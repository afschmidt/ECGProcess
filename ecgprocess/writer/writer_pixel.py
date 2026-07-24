"""
The stacked pixel-tensor writer.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import logging
from typing import Any
import numpy as np
import pandas as pd
from ecgprocess.constants import (
    FileNames,
    TabularNames as TabNames,
    WriteNames,
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    InputValidationError,
    Warn_MSG,
)
from ecgprocess.plot_ecgs import ECGDrawing
from ecgprocess.writer.writer_base import (
    WriteContext,
    register_writer,
)
from ecgprocess.writer.writer_figure import FigureWriter
from ecgprocess.writer.writer_numpy import NpyWriter

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
# NOTE hardcoded (not __name__), see writer_base._log
_log = logging.getLogger('ecgprocess.writer')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_PIXEL)
class PixelWriter(FigureWriter):
    """
    Writes rendered ECG figures as one stacked pixel tensor per chunk.
    
    Each record is rendered through an `ECGDrawing` exactly as in
    `FigureWriter`, rasterised via `ECGDrawing.to_numpy`, and collected
    into a `(n_records, height, width, channels)` NHWC tensor written as
    `figures.npy` (with the `_N` chunk suffix when writing chunks).
    Tensor persistence is delegated to an internal `NpyWriter`, so the
    dtype cast and the `allow_pickle` guard match the `'npy'` writer.
    When metadata is extracted it is written as a tab-separated
    `metadata.tsv` record-keeping table with the record UIDs as index,
    row `i` aligned with tensor slice `i`.
    
    Parameters
    ----------
    drawing : `ECGDrawing` or `NoneType`, default `NoneType`
        The drawing rendering each record. A default `ECGDrawing()` is
        used when `NoneType`, making the bare `'pixel'` registry key a
        working writer selector.
    mapper : `dict` [`str`, `tuple` [`int`, `slice`]] or `NoneType`, \
default `NoneType`
        An explicit lead layout forwarded to `ECGDrawing.__call__`.
        `DEFAULT_MAPPER` is used when `NoneType`.
    source : {'waveforms', 'median'}, default `'waveforms'`
        Which signal source to render, resolved through
        `ECGDrawing.SOURCE_MAP`.
    tile_x : `bool`, default `True`
        Whether `ECGDrawing.tile_x_axis` is applied after rendering; see
        `FigureWriter`.
    kwargs_call : `dict` or `NoneType`, default `NoneType`
        Extra keyword arguments forwarded to `ECGDrawing.__call__` for
        every record. `mapper` and `source` are writer-owned and must
        not be included.
    annotate : `list` [`dict`] or `NoneType`, default `NoneType`
        Annotation spec dicts forwarded to `ECGDrawing.annotate` for
        every record; see `FigureWriter`. Annotations are drawn before
        rasterising, so they are part of the pixel tensor. A record
        failing annotation while `ctx.skip_data` is set (the `ECGTable`
        `ignore_data` flag) is dropped from BOTH the pixel tensor and
        the metadata rows, keeping them row-aligned, and recorded on
        `ctx.failed_records`.
    channels : {'rgba', 'rgb', 'gray'}, default `'rgba'`
        The channel format of the tensor: RGBA (4 channels), RGB (3),
        or ITU-R BT.601 luminosity grayscale (1). Grayscale keeps its
        channel axis so the tensor rank is always 4.
    crop : `bool`, default `False`
        Whether whitespace is trimmed before rasterising, forwarded to
        `ECGDrawing.to_numpy`.
    dtype : `np.dtype`, `type`, or `str`, default `np.float32`
        The dtype the pixel tensor is cast to before writing; metadata
        keeps its own dtype. `np.uint8` preserves the native 0-255
        pixel range at a quarter of the float32 size.
    
    Raises
    ------
    InputValidationError
        If a chunk's rendered figures do not share one (height, width);
        render all records with one fixed figure size
        (`ECGStyle(figsize=..., dpi=...)`).
    
    Notes
    -----
    Each chunk holds all of its rasterised figures in memory before the
    stack is written; prefer modest chunk sizes, `dtype=np.uint8`, and
    `channels='gray'` for large batches.
    
    The `image_format` and `kwargs_savefig` parameters of `FigureWriter`
    do not apply: no per-record image files are written.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.npy'
    # the metadata table extension; FILE_EXT covers the pixel tensor
    META_EXT = '.tsv'
    # the supported channel formats mapped to their depths
    CHANNEL_FORMATS = {
        WriteNames.RGBA: 4,
        WriteNames.RGB:  3,
        WriteNames.GRAY: 1,
    }
    # the ITU-R BT.601 luminosity weights for grayscale conversion
    _LUMINOSITY = np.array([0.299, 0.587, 0.114], dtype=np.float32)
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, drawing: ECGDrawing | None = None,
                 mapper: dict | None = None,
                 source: str = 'waveforms',
                 tile_x: bool = True,
                 kwargs_call: dict | None = None,
                 annotate: list[dict[str, Any]] | None = None,
                 channels: str = WriteNames.RGBA,
                 crop: bool = False,
                 dtype: "np.dtype | type | str" = np.float32,
                 ) -> None:
        """Initialise the pixel writer."""
        super().__init__(drawing=drawing, mapper=mapper, source=source,
                         tile_x=tile_x, kwargs_call=kwargs_call,
                         annotate=annotate)
        # the image-file options are not part of the pixel writer's API;
        # remove the parent defaults so the repr does not advertise them
        del self.image_format, self.kwargs_savefig
        is_type(channels, str)
        is_type(crop, bool)
        if channels not in self.CHANNEL_FORMATS:
            raise InputValidationError(Error_MSG.CHOICE_PARM.format(
                'channels', sorted(self.CHANNEL_FORMATS)))
        self.channels = channels
        self.crop = crop
        # tensor persistence is delegated to the npy writer: dtype cast
        # and the allow_pickle guard live there
        self._npy = NpyWriter(dtype=dtype)
        self.dtype = self._npy.dtype
        # the per-write rasterisation buffers filled by `_persist_record`
        self._frames: list["np.ndarray"] = []
        self._kept_meta: list[dict[str, Any]] = []
        self._kept_keys: list[Any] = []
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Render all records and write one stacked pixel tensor.
        
        Runs the `FigureWriter` render loop (validation, layout,
        annotation, and the `ctx.skip_data` policy included), buffering
        each rasterised record instead of saving image files, then
        stacks the buffer, delegates tensor persistence to the internal
        `NpyWriter`, and writes the metadata `.tsv` when metadata is
        extracted.
        
        Parameters
        ----------
        meta_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing median beat signals.
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        
        Raises
        ------
        InputValidationError
            As raised by `FigureWriter.write`, or if the rendered
            figures do not share one (height, width).
        """
        # #### render into the buffers, then stack and persist
        self._frames = []
        self._kept_meta = []
        self._kept_keys = []
        try:
            super().write(meta_list, wave_list, median_list, ctx)
            self._save_stack(ctx)
        finally:
            # the buffers are per-write scratch state; do not let the
            # last chunk's frames linger on the instance
            self._frames = []
            self._kept_meta = []
            self._kept_keys = []
    # /////////////////////////////////////////////////////////////////////////
    def _persist_record(self, drawing: ECGDrawing, uid: Any,
                        meta: dict[str, Any], ctx: WriteContext,
                        ) -> None:
        """
        Buffer one rendered record as a pixel array.
        
        Overrides the `FigureWriter` persistence hook: the drawing is
        rasterised and buffered together with its metadata, so records
        skipped by the annotation policy stay absent from both.
        
        Parameters
        ----------
        drawing : `ECGDrawing`
            The called drawing holding the rendered figure.
        uid : `any`
            The record's unique key from `ctx.key_list`.
        meta : `dict` [`str`, `any`]
            The record's metadata (empty when metadata is not extracted).
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        """
        # invoked per record by the inherited FigureWriter.write loop;
        # a record skipped there never reaches this point, so frame,
        # metadata, and UID are appended (or omitted) together, keeping
        # row i of the metadata aligned with tensor slice i
        rgba = drawing.to_numpy(crop=self.crop, close=True)
        self._frames.append(self._convert_channels(rgba))
        self._kept_meta.append(meta)
        self._kept_keys.append(uid)
    # /////////////////////////////////////////////////////////////////////////
    def _convert_channels(self, rgba: "np.ndarray") -> "np.ndarray":
        """
        Convert an `(H, W, 4)` RGBA frame to the configured channels.
        
        Parameters
        ----------
        rgba : `np.ndarray`
            The rasterised frame in `(H, W, 4)` uint8 RGBA format.
        
        Returns
        -------
        frame : `np.ndarray`
            The frame with `CHANNEL_FORMATS[self.channels]` channels;
            grayscale keeps its channel axis for a uniform rank.
        """
        if self.channels == WriteNames.RGB:
            return rgba[..., :3]
        if self.channels == WriteNames.GRAY:
            gray = rgba[..., :3].astype(np.float32) @ self._LUMINOSITY
            return gray[..., np.newaxis]
        return rgba
    # /////////////////////////////////////////////////////////////////////////
    def _save_stack(self, ctx: WriteContext) -> None:
        """
        Stack the buffered frames and persist tensor and metadata.
        
        The tensor is written through the internal `NpyWriter`; the
        metadata is written as a tab-separated `metadata.tsv` with the
        kept record UIDs as index, row `i` aligned with tensor slice
        `i`.
        
        Parameters
        ----------
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        
        Raises
        ------
        InputValidationError
            If the buffered frames do not share one (height, width).
        """
        # an all-skipped chunk has nothing to stack; the failures are
        # already recorded on ctx.failed_records
        if not self._frames:
            _log.warning(Warn_MSG.PIXEL_EMPTY_CHUNK)
            return
        # #### stacking requires one shared frame size across the chunk
        shapes = {frame.shape for frame in self._frames}
        if len(shapes) > 1:
            raise InputValidationError(
                Error_MSG.PIXEL_SHAPE_MISMATCH.format(sorted(shapes)))
        # #### delegate tensor persistence (dtype cast, pickle guard)
        _, _, _, _, FIG_FILE = self.file_names(chunk_num=ctx.chunk_num)
        self._npy._save(
            {FileNames.FIGURES: np.stack(self._frames)}, ctx,
            file_names={FileNames.FIGURES: FIG_FILE},
        )
        # #### write the record-keeping metadata table, row i aligned
        # with tensor slice i and the kept UIDs as index
        if ctx.e_meta:
            sep = '' if ctx.chunk_num is None else '_'
            chunk = '' if ctx.chunk_num is None else str(ctx.chunk_num)
            META_FILE = FileNames.METADATA + sep + chunk + self.META_EXT
            pd.DataFrame(self._kept_meta, index=self._kept_keys).to_csv(
                os.path.join(ctx.target, META_FILE), sep='\t')
