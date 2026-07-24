"""
The per-record rendered-image writer.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import logging
from types import SimpleNamespace
from typing import Any
import matplotlib.pyplot as plt
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    PlotNames as PDNames,
    TabularNames as TabNames,
    WriteNames,
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    InputValidationError,
    Warn_MSG,
)
from ecgprocess.plot_ecgs import (
    ECGDrawing,
    _annotation_fields,
    _split_annotation_spec,
)
from ecgprocess.writer.writer_base import (
    BaseWriter,
    WriteContext,
    register_writer,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
CTypes = Core.DataTypes
# NOTE hardcoded (not __name__), see writer_base._log
_log = logging.getLogger('ecgprocess.writer')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_FIGURE)
class FigureWriter(BaseWriter):
    """
    Writes one rendered ECG image file per record, named by UID.
    
    Each record is rendered through an `ECGDrawing` and saved with
    `matplotlib.figure.Figure.savefig` as `<UID>.<image_format>`.
    
    Parameters
    ----------
    drawing : `ECGDrawing` or `NoneType`, default `NoneType`
        The drawing rendering each record. A default `ECGDrawing()` is
        used when `NoneType`, making the bare `'figure'` registry key a
        working writer selector.
    mapper : `dict` [`str`, `tuple` [`int`, `slice`]] or `NoneType`, \
default `NoneType`
        An explicit lead layout forwarded to `ECGDrawing.__call__`.
        `DEFAULT_MAPPER` is used when `NoneType`.
    source : {'waveforms', 'median'}, default `'waveforms'`
        Which signal source to render, resolved through
        `ECGDrawing.SOURCE_MAP`.
    image_format : `str`, default `'png'`
        The image format written; also the file extension. Any format
        supported by the active matplotlib backend is valid (raster:
        png, jpg, tiff; vector: pdf, svg, eps); an unsupported format
        raises `ValueError` from `savefig` itself.
    tile_x : `bool`, default `True`
        WhetherE `ECGDrawing.tile_x_axis` is applied after rendering, so
        each grid column shows a sequential time slice (the clinical
        print convention) while multi-column panels keep their full
        span. The default suits continuous waveforms in the default
        layout; set `False` for median beats or custom layouts where
        every panel should show the whole trace.
    kwargs_call : `dict` or `NoneType`, default `NoneType`
        Extra keyword arguments forwarded to `ECGDrawing.__call__` for
        every record (e.g. `style`, `show_lead_labels`, `cal_pulse`).
        `mapper` and `source` are writer-owned and must not be included.
    kwargs_savefig : `dict` or `NoneType`, default `NoneType`
        Extra keyword arguments forwarded to `Figure.savefig` (e.g.
        `dpi`).
    annotate : `list` [`dict`] or `NoneType`, default `NoneType`
        Annotation spec dicts forwarded to `ECGDrawing.annotate` for
        every record (see there for the spec format). `'{key}'`
        placeholders are resolved per record from that record's
        MetaData, so templates require metadata extraction; literal
        strings do not. A record with a missing or `NoneType`
        referenced key raises `InputValidationError` naming the record,
        or, when `ctx.skip_data` is set (the `ECGTable` `ignore_data`
        flag), is skipped (no image file) and recorded on
        `ctx.failed_records`.
    
    Notes
    -----
    Rendering uses the default matplotlib backend, which for personal machines
    will likely be interactive (and slow therefore); for large headless
    batch jobs select a non-interactive backend, e.g. ``matplotlib.use('Agg')``.
    
    A mapper panel keyed ``'<lead> <suffix>'`` (e.g. ``'II strip'``)
    whose key is not itself a lead re-plots that lead, so custom
    layouts can include rhythm strips for any lead.
    
    Anticipating this writer will mostly be used to mimic paper ECGs the
    default of ECGDrawing is slightly altered by removing the GridSpec panel
    specific splines.
    """
    # /////////////////////////////////////////////////////////////////////////
    # the default layout: the standard clinical print (3x4 grid plus a
    # full-width lead II rhythm strip), matching the layout used in
    # `resources/examples/plot_ecgs.ipynb`
    DEFAULT_MAPPER: dict[str, tuple[int, slice]] = {
        Core.Leads.I:   (0, slice(0, 1)),
        Core.Leads.aVR: (0, slice(1, 2)),
        Core.Leads.V1:  (0, slice(2, 3)),
        Core.Leads.V4:  (0, slice(3, 4)),
        Core.Leads.II:  (1, slice(0, 1)),
        Core.Leads.aVL: (1, slice(1, 2)),
        Core.Leads.V2:  (1, slice(2, 3)),
        Core.Leads.V5:  (1, slice(3, 4)),
        Core.Leads.III: (2, slice(0, 1)),
        Core.Leads.aVF: (2, slice(1, 2)),
        Core.Leads.V3:  (2, slice(2, 3)),
        Core.Leads.V6:  (2, slice(3, 4)),
        Core.Leads.II + ' strip': (3, slice(0, 4)),
    }
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, drawing: ECGDrawing | None = None,
                 mapper: dict | None = None,
                 source: str = 'waveforms',
                 image_format: str = 'png',
                 tile_x: bool = True,
                 kwargs_call: dict | None = None,
                 kwargs_savefig: dict | None = None,
                 annotate: list[dict[str, Any]] | None = None,
                 ) -> None:
        """Initialise the figure writer."""
        is_type(drawing, (ECGDrawing, type(None)))
        is_type(mapper, (dict, type(None)))
        is_type(source, str)
        is_type(image_format, str)
        is_type(tile_x, bool)
        is_type(kwargs_call, (dict, type(None)))
        is_type(kwargs_savefig, (dict, type(None)))
        is_type(annotate, (list, type(None)))
        # a malformed annotation spec is systematic: validate at
        # construction so it cannot fail (or be skip-recorded) mid-batch
        for spec in (annotate or []):
            _split_annotation_spec(spec)
        self.drawing = drawing or ECGDrawing()
        self.mapper = mapper
        self.source = source
        # normalise so both 'png' and '.PNG' yield the 'png' format/extension
        self.image_format = image_format.lower().lstrip('.')
        self.tile_x = tile_x
        self.kwargs_call = kwargs_call or {}
        self.kwargs_savefig = kwargs_savefig or {}
        self.annotate = annotate or []
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Render and save one image file per record, named by UID.
        
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
            If `source` is not a `drawing.SOURCE_MAP` key, if both
            waveforms and median beats are extracted (the writer renders
            exactly one source), if the selected source was not
            extracted, if annotation templates are used without metadata
            extraction, or if a record misses a referenced metadata key
            while `ctx.skip_data` is unset.
        """
        # #### the figure writer renders exactly one signal source
        # both sources would silently drop one and collide on the
        # per-UID filenames
        if ctx.e_wave and ctx.e_median:
            raise InputValidationError(
                Error_MSG.DUAL_SOURCE.format(type(self).__name__))
        # #### annotation templates resolve from per-record metadata;
        # without metadata extraction every placeholder would fail, so
        # this is a configuration error and always raises upfront
        if not ctx.e_meta and any(
                _annotation_fields(spec[PDNames.ANNOT_TEXT])
                for spec in self.annotate):
            raise InputValidationError(Error_MSG.ANNOTATE_NEEDS_META)
        # #### resolve which extracted source to render
        source_map = self.drawing.SOURCE_MAP
        if self.source not in source_map:
            raise InputValidationError(
                Error_MSG.CHOICE_PARM.format('source', sorted(source_map)))
        attr_name = source_map[self.source]
        if attr_name == CTypes.WaveForms:
            record_list, extracted = wave_list, ctx.e_wave
        else:
            record_list, extracted = median_list, ctx.e_median
        if not extracted:
            raise InputValidationError(
                Error_MSG.SOURCE_NOT_EXTRACTED.format(
                    type(self).__name__, self.source))
        # #### align the optional metadata with the records
        meta_iter = meta_list if ctx.e_meta else [{}] * len(record_list)
        # #### resolve the layout: user-supplied or the clinical default
        mapper = self.mapper if self.mapper is not None \
            else self.DEFAULT_MAPPER
        # #### render and save one figure per record
        for uid, record, meta in zip(
                ctx.key_list, record_list, meta_iter, strict=True):
            # absent leads are None; drop them before rendering (also
            # yields a fresh dict, keeping the caller's data unmutated)
            signals = {lead: arr for lead, arr in record.items()
                       if arr is not None}
            # a panel keyed '<lead> <suffix>' (e.g. 'II strip') re-plots
            # that lead: inject the duplicated signal for such panels
            for key in mapper:
                if key not in signals:
                    base = key.split(' ', 1)[0]
                    if base in signals:
                        signals[key] = signals[base]
            # ECGDrawing consumes a reader-like object exposing the
            # signal and metadata attributes; adapt the per-record dicts
            adapter = SimpleNamespace(**{
                attr_name: signals,
                CTypes.MetaData: meta,
            })
            drawing = self.drawing(
                adapter, mapper=mapper, source=self.source,
                **self.kwargs_call,
            )
            fig = drawing.figure
            try:
                # remove spines to better mimic an ECG image
                for ax in drawing.axes.values():
                    for spine in ax.spines.values():
                        spine.set_visible(False)
                if self.tile_x:
                    drawing.tile_x_axis()
                # #### metadata-driven annotation; a missing key is a
                # data failure governed by the ECGTable ignore_data flag
                # (spec-shape errors were already raised at __init__)
                if self.annotate:
                    try:
                        drawing.annotate(self.annotate)
                    except InputValidationError as err:
                        if ctx.skip_data:
                            ctx.failed_records.append(
                                (uid, WriteNames.ANNOT_CAUSE.format(err)))
                            _log.warning(Warn_MSG.ANNOTATE_SKIPPED, uid, err)
                            continue
                        raise InputValidationError(
                            Error_MSG.ANNOTATE_RECORD.format(uid, err),
                        ) from err
                # #### persistence hook: `self` dispatches to the subclass
                # override (PixelWriter buffers a frame; this class saves
                # an image file), so subclasses reuse the loop above
                self._persist_record(drawing, uid, meta, ctx)
            finally:
                plt.close(fig)
    # /////////////////////////////////////////////////////////////////////////
    def _persist_record(self, drawing: ECGDrawing, uid: Any,
                        meta: dict[str, Any], ctx: WriteContext,
                        ) -> None:
        """
        Save one rendered record as `<UID>.<image_format>`.
        
        The persistence hook of the render loop in `write`; subclasses
        (e.g. `PixelWriter`) override it to consume the rendered drawing
        differently.
        
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
        # NOTE `meta` is unused here but part of the hook contract: the
        # PixelWriter override needs it to keep tensor and metadata aligned
        drawing.figure.savefig(
            os.path.join(ctx.target, f'{uid}.{self.image_format}'),
            format=self.image_format, **self.kwargs_savefig,
        )
