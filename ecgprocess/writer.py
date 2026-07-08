"""
Pluggable output writers for ECG data.

This module decouples the file-writing logic from :class:`ecgprocess.tabular.
ECGTable`. Writers subclass :class:`BaseWriter`, register themselves in the
module-level :data:`WRITERS` registry via the :func:`register_writer`
decorator, and receive all the state they need through a :class:`WriteContext`
dataclass. :func:`resolve_writer` normalises a user-supplied writer (subclass,
instance, or bare callable) into an object exposing a ``write`` method.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import abc
import logging
from dataclasses import dataclass
from typing import Any, Callable
import numpy as np
import pandas as pd
# filtering out TF warnings
# NOTE tensorflow is imported at module top level for now; task .3 makes it
# an optional, lazily imported dependency.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import (
    Warn_MSG,
)
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

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def register_writer(name: str,
                    ) -> Callable[[type[BaseWriter]], type[BaseWriter]]:
    """
    Class decorator registering a writer under `name` in :data:`WRITERS`.
    
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
    def _decorator(cls: type[BaseWriter]) -> type[BaseWriter]:
        if not (isinstance(cls, type) and issubclass(cls, BaseWriter)):
            raise TypeError(
                f'`{getattr(cls, "__name__", cls)}` must be a `BaseWriter` '
                'subclass to be registered.')
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
    if isinstance(writer, str):
        try:
            cls = WRITERS[writer]
        except KeyError:
            raise ValueError(
                f'`{writer}` is not a registered writer; available: '
                f'{sorted(WRITERS)}.') from None
        return cls()
    if isinstance(writer, type):
        if not issubclass(writer, BaseWriter):
            raise TypeError(
                f'`{writer.__name__}` must be a `BaseWriter` subclass.')
        return writer()
    if isinstance(writer, BaseWriter):
        return writer
    if callable(writer):
        return _CallableWriter(writer)
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
    def __init__(self, func: Callable[..., None]) -> None:
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
        """Delegate to the wrapped callable. See `BaseWriter.write`."""
        return self._func(meta_list, wave_list, median_list, ctx)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_TAB)
class TableWriter(BaseWriter):
    """
    Writes ECG data to flat, long-format tsv tables.

    Reproduces the behaviour of the former `ECGTable._write_tab`: up to
    three files (metadata, waveforms, medianbeats) gated by the export
    flags on the :class:`WriteContext`. The writer owns the tabular
    append semantics: when `tab_append` is `True` the first chunk is
    written with a header and subsequent chunks are appended without one;
    the cross-chunk state is held on the instance.

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
        Write a chunk of data to tsv tables. See `BaseWriter.write`.
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
        # pandas default ('w') byte-for-byte.
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
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_NUMPY)
class NumpyWriter(BaseWriter):
    """
    Writes ECG data to a single uncompressed `.npz` archive.

    Reproduces the behaviour of the former `ECGTable._write_numpy`: the
    enabled sources (metadata, waveforms, medianbeats) are bundled into one
    `ecg_data.npz` via `numpy.savez` (uncompressed), and the metadata column
    names are written to a `header_metadata.txt` sidecar. Signal arrays are
    built with `signal_dicts_to_numpy_array(..., padding=False)`, so all
    records in a chunk must share a length (set `signal_length_w`/`_m`).

    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True) -> None:
        """Initialise the numpy writer."""
        self.numeric_meta = numeric_meta
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """Write a chunk to an uncompressed `.npz`. See `BaseWriter.write`."""
        # #### set the filename
        _, _, _, ECG_FILE = ctx.write_file_names(chunk_num=ctx.chunk_num)
        # #### assemble the arrays for the enabled sources
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
        # #### write the bundle and the metadata header sidecar
        np.savez(os.path.join(ctx.target, ECG_FILE), **res_dict)
        if ctx.e_meta:
            _write_metadata_header(ctx.target, header)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_TFLOW)
class TFRecordWriter(BaseWriter):
    """
    Writes ECG data to a single `.tfrecord`.

    Reproduces the behaviour of the former `ECGTable._write_tfr`: the enabled
    sources are stored as flattened `tf.train.Feature` float lists in one
    `tf.train.Example`. Signal arrays are built with
    `signal_dicts_to_numpy_array(..., padding=False)`, so all records in a
    chunk must share a length. The metadata column names are written to a
    `header_metadata.txt` sidecar.

    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True) -> None:
        """Initialise the tfrecord writer."""
        self.numeric_meta = numeric_meta
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """Write a chunk to a `.tfrecord`. See `BaseWriter.write`."""
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
        if ctx.e_meta:
            _write_metadata_header(ctx.target, header)
