"""
The numpy-family writers: `NumpyWriter` (abstract), `NpzWriter`, `NpyWriter`.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import abc
from typing import Any
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import is_type
from ecgprocess.utils.ecg_tools import (
    signal_dicts_to_numpy_array,
)
from ecgprocess.writer.writer_base import (
    BaseWriter,
    WriteContext,
    register_writer,
    _meta_to_array,
    _write_metadata_header,
)
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
CTypes = Core.DataTypes

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class NumpyWriter(BaseWriter):
    """
    Abstract base class for the numpy-family writers.
    
    Assembles the enabled sources into numpy arrays (shared by all
    subclasses) and delegates persistence to the abstract `_save` method.
    The base class is not registered; only its concrete subclasses are reachable.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True) -> None:
        """Initialise the numpy-family writer."""
        is_type(numeric_meta, bool)
        self.numeric_meta = numeric_meta
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a chunk of ECG data as numpy arrays.
        
        Assembles the enabled sources via `_assemble`, delegates the file
        layout to the subclass `_save` implementation, and writes the
        metadata header sidecar when metadata is exported.
        
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
        """
        # #### assemble the arrays for the enabled sources
        res_dict, header = self._assemble(
            meta_list, wave_list, median_list, ctx)
        # #### persist the arrays (the subclass owns the file layout)
        self._save(res_dict, ctx)
        # #### write the metadata header sidecar
        # NOTE header is not None exactly when metadata was exported
        if header is not None:
            _write_metadata_header(ctx.target, header)
    # /////////////////////////////////////////////////////////////////////////
    def _assemble(self, meta_list: list[dict[str, Any]],
                  wave_list: list[dict[str, "np.ndarray"]],
                  median_list: list[dict[str, "np.ndarray"]],
                  ctx: WriteContext,
                  ) -> tuple[dict[str, "np.ndarray"], list[str] | None]:
        """
        Assemble numpy arrays for the sources enabled in the context.
        
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
        
        Returns
        -------
        res_dict : `dict` [`str`, `np.ndarray`]
            The assembled arrays keyed by data type, enabled sources only.
        header : `list` [`str`] or `NoneType`
            The metadata column names, or `NoneType` when metadata is not
            exported.
        """
        res_dict = {}
        header = None
        if ctx.e_meta:
            res_dict[CTypes.MetaData], header = _meta_to_array(
                meta_list, self.numeric_meta)
        if ctx.e_wave:
            res_dict[CTypes.WaveForms] = signal_dicts_to_numpy_array(
                wave_list, padding=False)
        if ctx.e_median:
            res_dict[CTypes.MedianBeats] = signal_dicts_to_numpy_array(
                median_list, padding=False)
        return res_dict, header
    # /////////////////////////////////////////////////////////////////////////
    @abc.abstractmethod
    def _save(self, res_dict: dict[str, "np.ndarray"],
              ctx: WriteContext,
              ) -> None:
        """
        Persist the assembled arrays to disk.
        
        Parameters
        ----------
        res_dict : `dict` [`str`, `np.ndarray`]
            The assembled arrays keyed by data type.
        ctx : `WriteContext`
            The context carrying the target path and filename helper.
        """
        raise NotImplementedError

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_NPZ)
class NpzWriter(NumpyWriter):
    """
    Writes ECG data to a single uncompressed `.npz` archive.
    
    All enabled sources are bundled into one `ecg_data.npz` file, which can
    accommodate information from multiple records; the metadata column names are
    written to a `header_metadata.txt` sidecar.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.npz'
    # /////////////////////////////////////////////////////////////////////////
    def _save(self, res_dict: dict[str, "np.ndarray"],
              ctx: WriteContext,
              ) -> None:
        """
        Bundle the assembled arrays into a single uncompressed `.npz`.
        
        Parameters
        ----------
        res_dict : `dict` [`str`, `np.ndarray`]
            The assembled arrays keyed by data type.
        ctx : `WriteContext`
            The context carrying the target path and filename helper.
        """
        # #### set the filename
        _, _, _, ECG_FILE, _ = self.file_names(chunk_num=ctx.chunk_num)
        # NOTE typed as `Any` so the ** unpacking does not collide with the
        # `allow_pickle` keyword in the numpy savez stubs
        arrays: dict[str, Any] = dict(res_dict)
        np.savez(os.path.join(ctx.target, ECG_FILE), **arrays)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_NPY)
class NpyWriter(NumpyWriter):
    """
    Writes ECG data to one `.npy` file per source.
    
    Each enabled source is written to its own uncompressed `.npy` file
    (`metadata.npy`, `waveforms.npy`, `medianbeats.npy`, with the `_N`
    chunk suffix when writing chunks). The metadata column names are
    written to a `header_metadata.txt` sidecar.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    dtype : `np.dtype`, `type`, or `str`, default `np.float32`
        The dtype signal arrays are cast to before writing; metadata keeps
        its own dtype. Note integer dtypes cannot represent the `np.nan`
        used for absent leads.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.npy'
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True,
                 dtype: "np.dtype | type | str" = np.float32,
                 ) -> None:
        """Initialise the npy writer."""
        super().__init__(numeric_meta=numeric_meta)
        # normalise the signal dtype (raises TypeError when invalid)
        self.dtype = np.dtype(dtype)
    # /////////////////////////////////////////////////////////////////////////
    def _save(self, res_dict: dict[str, "np.ndarray"],
              ctx: WriteContext,
              file_names: dict[str, str] | None = None,
              ) -> None:
        """
        Write each assembled array to its own `.npy` file.
        
        Parameters
        ----------
        res_dict : `dict` [`str`, `np.ndarray`]
            The assembled arrays keyed by data type.
        ctx : `WriteContext`
            The context carrying the target path and filename helper.
        file_names : `dict` [`str`, `str`] or `NoneType`, default \
`NoneType`
            Maps each `res_dict` key to its target filename. Callers
            delegating non-standard sources (e.g. `PixelWriter`) supply
            their own mapping; `NoneType` selects the standard
            per-source names.
        """
        # #### set the per-source filenames
        if file_names is None:
            META_FILE, WAVE_FILE, MEDIAN_FILE, _, _ = \
                self.file_names(chunk_num=ctx.chunk_num)
            file_names = {
                CTypes.MetaData: META_FILE,
                CTypes.WaveForms: WAVE_FILE,
                CTypes.MedianBeats: MEDIAN_FILE,
            }
        # #### write each enabled source to its own file
        for data_type, array in res_dict.items():
            # signals are cast to the configured dtype; metadata keeps its
            # own dtype
            if data_type != CTypes.MetaData:
                array = array.astype(self.dtype)
            # NOTE allow_pickle=False guards against object arrays, which
            # cannot be memory-mapped
            np.save(os.path.join(ctx.target, file_names[data_type]),
                    array, allow_pickle=False)
