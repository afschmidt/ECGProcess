"""
The flat, long-format tsv table writer.
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
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import Error_MSG, is_type
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

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
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
    kwargs_tab : `dict` [`str`, `any`] or `NoneType`, default `NoneType`
        Base keyword arguments forwarded to `pandas.DataFrame.to_csv`;
        the per-call header/mode/separator/compression options override
        matching keys.
    row_order : {'sample', 'lead'}, default `'sample'`
        The row order within one record's block in the `WaveForms`/
        `MedianBeats` output, passed to `signal_dicts_to_long_table`.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.tsv'
    # maps the pandas `compression` values to their filename suffixes
    _COMPRESSION_SUFFIX = {
        'gz':   '.gz',
        'gzip': '.gz',
        'bz2':  '.bz2',
        'zip':  '.zip',
        'xz':   '.xz',
        'zst':  '.zst',
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, tab_append: bool = True, tab_sep: str = '\t',
                 tab_compression: str | None = 'gzip',
                 kwargs_tab: dict[str, Any] | None = None,
                 row_order: str = TabNames.ROW_ORDER_SAMPLE,
                 ) -> None:
        """Initialise the tabular writer and its append state."""
        is_type(tab_append, bool)
        is_type(tab_sep, str)
        is_type(tab_compression, (type(None), str))
        is_type(kwargs_tab, (dict, type(None)))
        is_type(row_order, str)
        EXP_ROW_ORDER = [TabNames.ROW_ORDER_SAMPLE, TabNames.ROW_ORDER_LEAD]
        if row_order not in EXP_ROW_ORDER:
            raise ValueError(
                Error_MSG.CHOICE_PARM.format('row_order', EXP_ROW_ORDER))
        self.tab_append = tab_append
        self.tab_sep = tab_sep
        self.tab_compression = tab_compression
        self.kwargs_tab = kwargs_tab or {}
        self.row_order = row_order
        # NOTE tracks whether the next write is the first for append mode
        self._first = True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def reset(self) -> None:
        """
        Reset the append-mode header state for a new `write_ecg` run.
        
        Overrides the `BaseWriter` no-op default: `_first` tracks
        whether the header still needs writing, and without this
        override, a `TableWriter` instance reused across two
        independent `write_ecg` calls would silently drop the header
        on the second run.
        
        Returns
        -------
        `NoneType`
            This method mutates instance state in place and returns
            nothing.
        """
        self._first = True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def file_ext(self) -> str:
        """
        Return the `.tsv` extension with the compression suffix.
        
        Returns
        -------
        ext : `str`
            The file extension, including the leading dot.
        """
        suffix = self._COMPRESSION_SUFFIX.get(self.tab_compression, '')
        return self.FILE_EXT + suffix
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
        kwargs_tab_combi = {**self.kwargs_tab, **writer_kwargs}
        # #### set the filenames
        META_FILE, WAVE_FILE, MEDIAN_FILE, _, _ = self.file_names(
            chunk_num=chunk_num)
        # #### write individual files
        if ctx.e_meta:
            pd.DataFrame(meta_list, index=ctx.key_list).to_csv(
                os.path.join(ctx.target, META_FILE),
                **kwargs_tab_combi,
            )
        if ctx.e_wave:
            signal_dicts_to_long_table(
                wave_list, key_list=ctx.key_list,
                signal_type=CTypes.WaveForms,
                row_order=self.row_order,
            ).to_csv(
                os.path.join(ctx.target, WAVE_FILE),
                **kwargs_tab_combi,
            )
        if ctx.e_median:
            signal_dicts_to_long_table(
                median_list, key_list=ctx.key_list,
                signal_type=CTypes.MedianBeats,
                row_order=self.row_order,
            ).to_csv(
                os.path.join(ctx.target, MEDIAN_FILE),
                **kwargs_tab_combi,
            )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# helpers
def signal_dicts_to_long_table(lead_list: list[dict[str, "np.ndarray"]],
                               key_list: list[Any], signal_type: str,
                               prev_keys: list[str] | None = None,
                               row_order: str = TabNames.ROW_ORDER_SAMPLE,
                               **kwargs_pd: Any,
                               ) -> pd.DataFrame:
    """
    Map lists of dictionaries containing lead specific numpy arrays to a
    long-formatted pandas table.
    
    Parameters
    ----------
    lead_list : `list` [`dict` [`str`, `np.ndarray`]]
        A list of dictionaries with the lead names mapped to the keys and
        the voltage mapped to the values.
    key_list : `list`
        The per-record unique keys, aligned with `lead_list`.
    signal_type : `str`
        Adds a column `Signal type` containing this string as a constant.
    prev_keys : `list` [`str`] or `NoneType`, default `NoneType`
        The lead names from a previous call, seeding the key-consistency
        check so file headers can persist between calls; `NoneType`
        starts fresh.
    row_order : {'sample', 'lead'}, default `'sample'`
        The row order within one record's block: `'sample'` groups by
        sampling sequence then lead, `'lead'` groups by lead then
        sampling sequence. Records themselves are always grouped in
        `key_list` order.
    kwargs_pd
        keyword arguments passed to `pd.DataFrame`.
    
    Returns
    -------
    long_table : `pd.DataFrame`
        A long-formatted table with lead, voltage, sampling sequence
        columns grouped by file (including an unique file indicator
        column).
    
    Raises
    ------
    ValueError
        If the number of signals differs between the leads of a record,
        or if `row_order` is not `'sample'` or `'lead'`.
    KeyError
        If the lead names differ between records, or from `prev_keys`.
    """
    # #### check input and set constants
    is_type(lead_list, list, 'lead_list')
    is_type(key_list, list, 'key_list')
    is_type(signal_type, str, 'signal_type')
    is_type(prev_keys, (list, type(None)), 'prev_keys')
    is_type(row_order, str, 'row_order')
    EXP_ROW_ORDER = [TabNames.ROW_ORDER_SAMPLE, TabNames.ROW_ORDER_LEAD]
    if row_order not in EXP_ROW_ORDER:
        raise ValueError(
            Error_MSG.CHOICE_PARM.format('row_order', EXP_ROW_ORDER))
    SAMPLING_SEQ = 'Sampling sequence'
    # the last set of valid lead names; seeded by prev_keys so cross-call
    # key persistence is an explicit parameter, not instance state
    prev = prev_keys
    # #### initiate table and map lists
    table = pd.DataFrame()
    # NOTE w contains a dictionary with k: lead names and v: signals.
    for w, k in zip(lead_list, key_list, strict=True):
        # NOTE shallow-copy so NaN-replacement below never mutates the
        # caller's original record dict (a shallow copy is sufficient:
        # every write below is a whole-value rebind, never an in-place
        # array mutation).
        w = dict(w)
        # ##### are there leads with None instead of signals
        # FIRST get the length of the array and make sure this is unique.
        # SECOND replace these by arrays by NaN
        array_length = []
        for value in w.values():
            if isinstance(value, np.ndarray):
                array_length.append(len(value))
        arr_len = np.unique(array_length)
        if len(arr_len) == 0:
            # add a place holder length
            _log.warning(
                'All the signal data is set to None, replacing these '
                'by arrays of length one.',
            )
            arr_len = 1
        elif len(arr_len) > 1:
            raise ValueError('The number of signals differs per lead: '
                             f'`{arr_len}`.')
        for key, sig in w.items():
            if sig is None:
                w[key] = np.full(arr_len, np.nan)
                if arr_len != 1:
                    _log.warning(
                        "Lead '%s' had a None value and has been "
                        "replaced by an array of NaN.",
                        key,
                    )
        # ##### confirm the dictionary keys/lead names are identical
        current_keys = list(w.keys())
        if prev is not None:
            if current_keys != prev:
                raise KeyError('The dictionaries contain distinct keys. '
                               'The last set of valid keys was {}, '
                               'compared to {}.'.\
                               format(prev, current_keys))
        # ##### if the same map to dataframe
        temp_df = pd.DataFrame(w, **kwargs_pd)
        temp_df[TabNames.KEY] = k
        # FIXME this will be fairly slow/inefficient
        table = pd.concat([table, temp_df], ignore_index=True)
        # clean
        prev = current_keys
        del current_keys
        del temp_df
    # #### formatting to long
    if table.empty == False:
        table[SAMPLING_SEQ] = table.groupby(
            TabNames.KEY).cumcount()
        # NOTE pd.melt stacks rows by lead across records; restore
        # record order via a stable sort keyed on each key's
        # first-appearance position.
        PARTICIPANT_ORDER = 'Participant order'
        table[PARTICIPANT_ORDER] = pd.factorize(table[TabNames.KEY])[0]
        long_table = pd.melt(table, id_vars=\
                             [TabNames.KEY, SAMPLING_SEQ,
                              PARTICIPANT_ORDER],
                             value_vars=prev,
                             var_name='Lead',
                             value_name='Voltage',
                             )
        # 'sample' also sorts by sampling sequence, so a record's rows
        # go sample-then-lead; 'lead' leaves them lead-then-sample.
        sort_by = [PARTICIPANT_ORDER, SAMPLING_SEQ] \
            if row_order == TabNames.ROW_ORDER_SAMPLE \
            else [PARTICIPANT_ORDER]
        long_table = long_table.sort_values(
            by=sort_by, kind='stable',
        ).drop(columns=PARTICIPANT_ORDER).reset_index(drop=True)
        long_table['Signal type'] = signal_type
    else:
        long_table = table
    # #### return
    return long_table
