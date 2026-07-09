"""
Pluggable output writers for ECG data.

This module introduces ECG writing callables which can be used with the
`tabular` module to bulk wrote metadata and/or signal data.

Writers subclass register themselves in the module-level `WRITERS` registry via
the `register_writer` decorator, allowing for user supplied callables.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import abc
import logging
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, TypeVar
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    InputValidationError,
    Warn_MSG,
)
from ecgprocess.plot_ecgs import ECGDrawing
from ecgprocess.utils.ecg_tools import (
    signal_dicts_to_numpy_array,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
_log = logging.getLogger(__name__)
# the writer registry, populated by the register_writer decorator. All
# writer classes are defined at module top level so their decorators run
# before the registry is read.
WRITERS: dict[str, type["BaseWriter"]] = {}
# type variable preserving the concrete class type through the
# register_writer decorator (a bare type[BaseWriter] return would erase
# the decorated writer's constructor signature for static analysis)
_W = TypeVar('_W', bound='BaseWriter')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@dataclass
class WriteContext(object):
    """
    Carries the state a writer needs from :class:`ECGTable`.
    
    Parameters
    ----------
    e_meta : `bool`
        Whether metadata should be exported.
    e_wave : `bool`
        Whether waveform signals should be exported.
    e_median : `bool`
        Whether median beat signals should be exported.
    kwargs_tab : `dict` [`str`, `any`]
        Base keyword arguments forwarded to `pandas.DataFrame.to_csv`.
    key_list : `list`
        The per-record unique key list used as the metadata index.
    target : `str`
        The target directory the files are written to.
    chunk_num : `int` or `NoneType`
        The chunk number, appended to filenames when not `NoneType`.
    write_file_names : `Callable`
        Helper returning the (metadata, waveforms, medianbeats, ecg_data)
        filenames including extensions.
    get_long_table : `Callable`
        Helper mapping a list of lead dictionaries to a long-format
        `pandas.DataFrame`.
    """
    # NOTE add input tests?
    # NOTE 2 kwargs_tab, get_long_table might be better as options parameters?
    e_meta: bool
    e_wave: bool
    e_median: bool
    kwargs_tab: dict[str, Any]
    key_list: list[Any]
    target: str
    chunk_num: int | None
    write_file_names: Callable[..., tuple[str, str, str, str]]
    get_long_table: Callable[..., pd.DataFrame]

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class BaseWriter(abc.ABC):
    """
    Abstract base class for all ECG output writers.
    
    Concrete writers implement :meth:`write`, which receives the extracted
    per-chunk data lists and a :class:`WriteContext`.
    """
    # /////////////////////////////////////////////////////////////////////////
    @abc.abstractmethod
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a single chunk of extracted ECG data to disk.
        
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
        raise NotImplementedError
    # /////////////////////////////////////////////////////////////////////////
    def __repr__(self) -> str:
        """
        Return a constructor-like representation of the writer.
        
        Uses the runtime class name and the public instance attributes, so
        subclasses (including user-registered writers) inherit an accurate
        representation without overriding it. `str()` falls back to this
        method as no `__str__` is defined.
        """
        options = ', '.join(
            f'{name}={value!r}' for name, value in vars(self).items()
            if not name.startswith('_'))
        return f'{type(self).__name__}({options})'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def register_writer(name: str,
                    ) -> Callable[[type[_W]], type[_W]]:
    """
    Class decorator registering a writer under `name` in `WRITERS`.
    
    Parameters
    ----------
    name : `str`
        The registry key, matching a `file_type` value.
    
    Returns
    -------
    `Callable`
        The decorator adding the class to the registry.
    
    Raises
    ------
    TypeError
        If the decorated class is not a `BaseWriter` subclass.
    ValueError
        If `name` is already present in the registry.
    """
    is_type(name, str)
    # internal function
    def _decorator(cls: type[_W]) -> type[_W]:
        if not (isinstance(cls, type) and issubclass(cls, BaseWriter)):
            raise TypeError(
                f'`{getattr(cls, "__name__", cls)}` must be a `BaseWriter` '
                'subclass to be registered.')
        # check if already registered
        if name in WRITERS:
            raise ValueError(
                f'A writer is already registered under `{name}`.')
        WRITERS[name] = cls
        return cls
    return _decorator

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def resolve_writer(writer: Any) -> BaseWriter:
    """
    Normalise a user-supplied writer into a `BaseWriter` instance.
    
    Parameters
    ----------
    writer : `str`, `type`, `BaseWriter`, or `Callable`
        A registry-key string (looked up in :data:`WRITERS` and
        instantiated), a `BaseWriter` subclass (instantiated here), a
        `BaseWriter` instance (returned as-is), or a bare callable matching
        the `BaseWriter.write` signature. A bare callable bypasses the ABC
        guarantees and is wrapped without validation of its signature.
    
    Returns
    -------
    `BaseWriter`
        An object exposing a `write(meta_list, wave_list, median_list, ctx)`
        method.
    
    Raises
    ------
    ValueError
        If `writer` is a string not present in the registry.
    TypeError
        If `writer` is a class that is not a `BaseWriter` subclass, or is
        neither a `str`, `BaseWriter`, subclass, nor callable.
    """
    # if string look-up in WRITERS
    if isinstance(writer, str):
        try:
            cls = WRITERS[writer]
        except KeyError:
            raise ValueError(
                f'`{writer}` is not a registered writer; available: '
                f'{sorted(WRITERS)}.') from None
        return cls()
    # if type make sure it inherits from BaseWriter
    if isinstance(writer, type):
        if not issubclass(writer, BaseWriter):
            raise TypeError(
                f'`{writer.__name__}` must be a `BaseWriter` subclass.')
        return writer()
    # return
    if isinstance(writer, BaseWriter):
        return writer
    if callable(writer):
        return _CallableWriter(writer)
    # otherwise raise error
    raise TypeError(
        '`writer` must be a `BaseWriter` subclass, instance, or callable, '
        f'not `{type(writer).__name__}`.')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class _CallableWriter(BaseWriter):
    """
    Adapter wrapping a bare callable as a :class:`BaseWriter`.
    
    The callable must accept `(meta_list, wave_list, median_list, ctx)`.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, func: Callable[..., Any]) -> None:
        """
        Initialise the adapter.
        
        Parameters
        ----------
        func : `Callable`
            The callable to delegate `write` calls to.
        """
        self._func = func
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Delegate the write call to the wrapped callable.
        
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
        return self._func(meta_list, wave_list, median_list, ctx)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_TAB)
class TableWriter(BaseWriter):
    """
    Writes ECG data to flat, long-format tsv tables.
    
    Parameters
    ----------
    tab_append : `bool`, default `True`
        Whether successive chunks are appended to a single file.
    tab_sep : `str`, default `'\\t'`
        The field separator passed to `pandas.DataFrame.to_csv`.
    tab_compression : `str` or `NoneType`, default `'gzip'`
        The compression passed to `pandas.DataFrame.to_csv`.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, tab_append: bool = True, tab_sep: str = '\t',
                 tab_compression: str | None = 'gzip',
                 ) -> None:
        """Initialise the tabular writer and its append state."""
        is_type(tab_append, bool)
        is_type(tab_sep, str)
        is_type(tab_compression, (type(None), str))
        self.tab_append = tab_append
        self.tab_sep = tab_sep
        self.tab_compression = tab_compression
        # NOTE tracks whether the next write is the first for append mode
        self._first = True
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a chunk of ECG data to long-format tsv tables.
        
        Each enabled source is written to its own file (`metadata`,
        `waveforms`, `medianbeats`), honouring the append, separator, and
        compression options set on the writer instance.
        
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
        # #### derive the per-call to_csv keyword arguments
        # the header/mode/chunk logic is a tabular-writer concern; `_first`
        # is only relevant when appending to a single file.
        if not self.tab_append:
            header = True
            mode = 'w'
            chunk_num = ctx.chunk_num
        elif self._first:
            header = True
            mode = 'w'
            chunk_num = None
        else:
            header = False
            mode = 'a'
            chunk_num = None
        self._first = False
        # NOTE only pass `mode` when appending so the header cases match the
        # pandas default ('w').
        writer_kwargs = {'header': header, 'sep': self.tab_sep,
                         'compression': self.tab_compression}
        if mode == 'a':
            writer_kwargs['mode'] = 'a'
        kwargs_tab_combi = {**ctx.kwargs_tab, **writer_kwargs}
        # #### set the filenames
        META_FILE, WAVE_FILE, MEDIAN_FILE, _ = ctx.write_file_names(
            chunk_num=chunk_num, **kwargs_tab_combi)
        # #### write individual files
        if ctx.e_meta:
            pd.DataFrame(meta_list, index=ctx.key_list).to_csv(
                os.path.join(ctx.target, META_FILE),
                **kwargs_tab_combi,
            )
        if ctx.e_wave:
            ctx.get_long_table(
                wave_list, signal_type=CTypes.WaveForms,
                purge_header=True,
            ).to_csv(
                os.path.join(ctx.target, WAVE_FILE),
                **kwargs_tab_combi,
            )
        if ctx.e_median:
            ctx.get_long_table(
                median_list, signal_type=CTypes.MedianBeats,
                purge_header=True,
            ).to_csv(
                os.path.join(ctx.target, MEDIAN_FILE),
                **kwargs_tab_combi,
            )

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
    
    All enabled sources are bundled into one `ecg_data.npz` file; the
    metadata column names are written to a `header_metadata.txt` sidecar.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
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
        _, _, _, ECG_FILE = ctx.write_file_names(chunk_num=ctx.chunk_num)
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
              ) -> None:
        """
        Write each assembled array to its own `.npy` file.
        
        Parameters
        ----------
        res_dict : `dict` [`str`, `np.ndarray`]
            The assembled arrays keyed by data type.
        ctx : `WriteContext`
            The context carrying the target path and filename helper.
        """
        # #### set the per-source filenames
        META_FILE, WAVE_FILE, MEDIAN_FILE, _ = ctx.write_file_names(
            chunk_num=ctx.chunk_num)
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

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_TFLOW)
class TFRecordWriter(BaseWriter):
    """
    Writes ECG data to a single `.tfrecord`.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True) -> None:
        """Initialise the tfrecord writer."""
        is_type(numeric_meta, bool)
        self.numeric_meta = numeric_meta
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _import_tensorflow() -> ModuleType:
        """
        Lazily import tensorflow.
        
        TensorFlow is an optional dependency: it is imported here, per
        `write` call, rather than at module import time, so that the rest
        of the package works without it.
        
        Returns
        -------
        tf : `ModuleType`
            The imported tensorflow module.
        
        Raises
        ------
        ImportError
            If tensorflow is not installed, naming the install route.
        """
        try:
            # filtering out TF warnings
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
            import tensorflow as tf
        except ImportError as exc:
            raise ImportError(Error_MSG.MISSING_TENSORFLOW) from exc
        return tf
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a chunk of ECG data to a single `.tfrecord`.
        
        The enabled sources are stored as flattened `tf.train.Feature`
        float lists in one `tf.train.Example`; the metadata column names
        are written to a `header_metadata.txt` sidecar.
        
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
        ImportError
            If tensorflow is not installed.
        """
        # #### import tensorflow lazily before any file is written
        tf = self._import_tensorflow()
        # #### set the filename
        _, _, _, ECG_FILE = ctx.write_file_names(chunk_num=ctx.chunk_num)
        # #### assemble the features for the enabled sources
        res_dict = {}
        header = None
        if ctx.e_meta:
            array, header = _meta_to_array(meta_list, self.numeric_meta)
            res_dict[CTypes.MetaData] = tf.train.Feature(
                float_list=tf.train.FloatList(value=array.flatten()))
        if ctx.e_wave:
            res_dict[CTypes.WaveForms] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        wave_list, padding=False).flatten()))
        if ctx.e_median:
            res_dict[CTypes.MedianBeats] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        median_list, padding=False).flatten()))
        # #### write the record and the metadata header sidecar
        with tf.io.TFRecordWriter(
                os.path.join(ctx.target, ECG_FILE)) as record_writer:
            record_writer.write(
                tf.train.Example(
                    features=tf.train.Features(feature=res_dict)
                ).SerializeToString())
        # NOTE header is not None exactly when metadata was exported
        if header is not None:
            _write_metadata_header(ctx.target, header)

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
        Whether `ECGDrawing.tile_x_axis` is applied after rendering, so
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
    
    Notes
    -----
    Rendering uses the active matplotlib backend; for large headless
    batch jobs select a non-interactive backend first, e.g.
    ``matplotlib.use('Agg')``.
    
    A mapper panel keyed ``'<lead> <suffix>'`` (e.g. ``'II strip'``)
    whose key is not itself a lead re-plots that lead, so custom
    layouts can include rhythm strips for any lead.
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
                 ) -> None:
        """Initialise the figure writer."""
        is_type(drawing, (ECGDrawing, type(None)))
        is_type(mapper, (dict, type(None)))
        is_type(source, str)
        is_type(image_format, str)
        is_type(tile_x, bool)
        is_type(kwargs_call, (dict, type(None)))
        is_type(kwargs_savefig, (dict, type(None)))
        self.drawing = drawing or ECGDrawing()
        self.mapper = mapper
        self.source = source
        # normalise so both 'png' and '.PNG' yield the 'png' format/extension
        self.image_format = image_format.lower().lstrip('.')
        self.tile_x = tile_x
        self.kwargs_call = kwargs_call or {}
        self.kwargs_savefig = kwargs_savefig or {}
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
            exactly one source), or if the selected source was not
            extracted.
        """
        # #### the figure writer renders exactly one signal source
        # both sources would silently drop one and collide on the
        # per-UID filenames
        if ctx.e_wave and ctx.e_median:
            raise InputValidationError(Error_MSG.FIGURE_DUAL_SOURCE)
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
                Error_MSG.FIGURE_SOURCE_NOT_EXTRACTED.format(self.source))
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
                if self.tile_x:
                    drawing.tile_x_axis()
                fig.savefig(
                    os.path.join(
                        ctx.target, f'{uid}.{self.image_format}'),
                    format=self.image_format, **self.kwargs_savefig,
                )
            finally:
                plt.close(fig)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# helpers
def _meta_to_array(meta_list: list[dict[str, Any]], numeric_meta: bool,
                   ) -> tuple["np.ndarray", list[str]]:
    """
    Build a metadata array and its column header from a list of dicts.
    
    Parameters
    ----------
    meta_list : `list` [`dict` [`str`, `any`]]
        A list of per-record metadata dictionaries.
    numeric_meta : `bool`
        When True, non-numeric columns are dropped (with a warning) so the
        result is a purely numeric array.
    
    Returns
    -------
    array : `np.ndarray`
        The metadata as a 2D array.
    header : `list` [`str`]
        The retained column names, in array-column order.
    """
    tab = pd.DataFrame(meta_list)
    if numeric_meta:
        old_cols = set(tab.columns)
        tab = tab.select_dtypes(include=[np.number])
        drop_cols = old_cols - set(tab.columns)
        if len(drop_cols) > 0:
            _log.warning(Warn_MSG.DROP_NONE_NUMERIC, drop_cols)
    return tab.to_numpy(), list(tab.columns)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _write_metadata_header(target: str, header: list[str]) -> None:
    """
    Write the metadata column names to a `header_metadata.txt` sidecar.
    
    The array formats (`.npz`, `.tfrecord`) store metadata as a bare numeric
    array with no column labels, so the header is written alongside as a
    line-numbered lookup.
    
    Parameters
    ----------
    target : `str`
        The directory the header file is written to.
    header : `list` [`str`]
        The metadata column names, in array-column order.
    """
    with open(os.path.join(target, 'header_metadata.txt'), 'w') as file:
        # NOTE line numbering starts at 1 to match the sidecar convention.
        for line_number, head in enumerate(header, start=1):
            file.write(f"{line_number}\t{head}\n")

