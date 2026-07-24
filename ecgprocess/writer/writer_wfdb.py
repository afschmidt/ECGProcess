"""
The lazily-imported WFDB (PhysioNet) writer.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import re
from types import ModuleType
from typing import Any
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import Error_MSG, is_type, InputValidationError
from ecgprocess.writer.writer_base import (
    BaseWriter,
    WriteContext,
    register_writer,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
CTypes = Core.DataTypes

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_WFDB)
class WFDBWriter(BaseWriter):
    """
    Writes one WFDB (PhysioNet) record per ECG UID.
    
    Each record is written as `<sanitised-UID>.hea` + `<sanitised-UID>.dat`
    via `wfdb.wrsamp`: a single multiplexed, format-16 (int16) `.dat`
    holding every lead of the selected source as a channel, with the
    per-channel gain/baseline computed automatically by `wfdb` from the
    physical signal (`p_signal`); no manual `adc_gain`/`baseline` is
    supplied.
    
    Parameters
    ----------
    source : {'waveforms', 'median'}, default `'waveforms'`
        Which signal source to write. A WFDB record is single-rate and
        single-length, so exactly one source may be extracted; mirrors
        `FigureWriter.source`.
    units : `str`, default `'mV'`
        The physical unit label written to the header for every channel
        (WFDB-canonical casing; lowercase `'mv'` is non-standard).
    units_field : `str` or `NoneType`, default `NoneType`
        A `MetaData` key optionally overriding `units` per record: when
        set and `meta.get(units_field)` is a non-empty string, it is used
        as that record's unit label instead of `units`.
    meta_fields : `list` [`str`], `str` ('all'), or `NoneType`, default `NoneType`
        `MetaData` keys written as `.hea` comment lines in addition to the
        original UID (always included as the first comment). Pass `'all'` to
        write every key in the record's `meta` dict; alternatively, specify
        field names explicitly as a list. The `'all'` sentinel is resolved at
        write time against the actual metadata keys, so different records may
        produce different comment sets.
    
    Raises
    ------
    ImportError
        If `wfdb` is not installed (see `_import_wfdb`).
    InputValidationError
        If both `WaveForms` and `MedianBeats` are extracted, if the
        selected `source` was not extracted, or if the processed sampling
        frequency metadata is absent.
    
    Notes
    -----
    `units` (and `units_field`) is a declarative label only: no value
    rescaling is performed. `ECGProcess` does not itself track or convert
    signal units elsewhere - `MetaData.RES_U_W`/`RES_U_M` are likewise
    descriptive fields, populated from a user config and never applied to
    the signal - so a caller whose signal is not already expressed in
    `units` must rescale it before calling `write_ecg`.
    
    Rectangular data (every configured lead present and equal length within
    a record) is guaranteed by `ECGTable` via `ignore_missing_leads`
    filtering upstream.
    
    The sampling frequency is read from the processed-rate metadata
    (`CoreData.ProcessingData.SF_NEW_W`/`SF_NEW_M`), populated only when
    the reader ran with resampling enabled - NOT the original
    `MetaData.SF`. A record without it raises; there is no fallback.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = ''
    # maps the 'source' parameter to the CoreData.DataTypes value it reads
    SOURCE_MAP: dict[str, str] = {
        'waveforms': CTypes.WaveForms,
        'median':    CTypes.MedianBeats,
    }
    # maps 'source' to the processed-rate MetaData key `fs` is read from
    _SF_KEY_MAP: dict[str, str] = {
        'waveforms': Core.ProcessingData.SF_NEW_W,
        'median':    Core.ProcessingData.SF_NEW_M,
    }
    # the WFDB-legal record-name character set; other characters map to '_'
    _INVALID_CHARS = re.compile(r'[^A-Za-z0-9_-]')
    # the fixed WFDB sample format: int16, one entry required per channel
    _FMT = '16'
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, source: str = 'waveforms', units: str = 'mV',
                 units_field: str | None = None,
                 meta_fields: list[str] | str | None = None,
                 ) -> None:
        """Initialise the WFDB writer."""
        is_type(source, str)
        is_type(units, str)
        is_type(units_field, (str, type(None)))
        is_type(meta_fields, (list, str, type(None)))
        if isinstance(meta_fields, str) and meta_fields != 'all':
            raise InputValidationError(
                f"meta_fields string must be 'all', got {meta_fields!r}.")
        self.source = source
        self.units = units
        self.units_field = units_field
        self.meta_fields = meta_fields if meta_fields is not None else []
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _import_wfdb() -> ModuleType:
        """
        Lazily import wfdb.
        
        wfdb is an optional dependency: it is imported here, per `write`
        call, rather than at module import time, so that the rest of the
        package works without it.
        
        Returns
        -------
        wfdb : `ModuleType`
            The imported wfdb module.
        
        Raises
        ------
        ImportError
            If wfdb is not installed, naming the install route.
        """
        try:
            import wfdb
        except ImportError as exc:
            raise ImportError(Error_MSG.MISSING_WFDB) from exc
        return wfdb
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write one WFDB record per ECG UID for the selected source.
        
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
            If wfdb is not installed.
        InputValidationError
            See the class docstring.
        """
        # #### import wfdb lazily before any file is written
        wfdb = self._import_wfdb()
        # #### the writer writes exactly one signal source per record
        if ctx.e_wave and ctx.e_median:
            raise InputValidationError(
                Error_MSG.DUAL_SOURCE.format(type(self).__name__))
        if self.source not in self.SOURCE_MAP:
            raise InputValidationError(Error_MSG.CHOICE_PARM.format(
                'source', sorted(self.SOURCE_MAP)))
        attr_name = self.SOURCE_MAP[self.source]
        if attr_name == CTypes.WaveForms:
            record_list, extracted = wave_list, ctx.e_wave
        else:
            record_list, extracted = median_list, ctx.e_median
        if not extracted:
            raise InputValidationError(
                Error_MSG.SOURCE_NOT_EXTRACTED.format(
                    type(self).__name__, self.source))
        sf_key = self._SF_KEY_MAP[self.source]
        # #### align the optional metadata with the records
        meta_iter = meta_list if ctx.e_meta else [{}] * len(record_list)
        # #### write one record per UID
        for uid, record, meta in zip(
                ctx.key_list, record_list, meta_iter, strict=True):
            self._write_record(wfdb, uid, record, meta, sf_key, ctx)
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _sanitise_comment_value(value: Any, field: str) -> str:
        """
        Sanitise a metadata value for use in a .hea comment line.
        
        WFDB comment lines are newline-delimited; embedded newlines
        would break the format. This method replaces all newline
        sequences (\r\n, \r, \n) with single spaces.
        
        Parameters
        ----------
        value : `any`
            The metadata value.
        field : `str`
            The metadata field name (for the comment line).
        
        Returns
        -------
        comment : `str`
            A single-line comment string safe for .hea files.
        """
        str_value = str(value)
        sanitised = re.sub(r'[\r\n]+', ' ', str_value)
        return f'{field}: {sanitised}'
    # /////////////////////////////////////////////////////////////////////////
    def _write_record(self, wfdb: ModuleType, uid: Any,
                      record: dict[str, "np.ndarray"],
                      meta: dict[str, Any], sf_key: str,
                      ctx: WriteContext,
                      ) -> None:
        """
        Write a single record as `<sanitised-UID>.hea` + `.dat`.
        
        Parameters
        ----------
        wfdb : `ModuleType`
            The imported wfdb module.
        uid : `any`
            The record's unique key from `ctx.key_list`.
        record : `dict` [`str`, `np.ndarray`]
            The lead name to signal mapping for this record.
        meta : `dict` [`str`, `any`]
            The record's metadata (empty when metadata is not extracted).
        sf_key : `str`
            The processed-rate `MetaData` key `fs` is read from (selected
            by `source`).
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        
        Raises
        ------
        InputValidationError
            If the processed sampling frequency metadata is absent.
        """
        # #### rectangular data guaranteed by ECGTable.ignore_missing_leads
        sig_name = list(record.keys())
        # #### the processed-rate metadata; no fallback to the original SF
        fs = meta.get(sf_key)
        if fs is None:
            raise InputValidationError(
                Error_MSG.WFDB_MISSING_SF.format(sf_key))
        # #### the declared unit label: per-record metadata override, or
        # the writer default (a purely declarative label, see class Notes)
        units = self.units
        if self.units_field is not None:
            meta_units = meta.get(self.units_field)
            if isinstance(meta_units, str) and meta_units:
                units = meta_units
        # #### assemble the multiplexed physical signal (n_samples, n_sig)
        p_signal = np.column_stack(
            [np.asarray(record[lead], dtype=float) for lead in sig_name])
        # #### resolve meta_fields 'all' sentinel at write time
        if isinstance(self.meta_fields, str) and self.meta_fields == 'all':
            fields_to_write = list(meta.keys())
        else:
            fields_to_write = self.meta_fields
        # #### header comments: the original UID, then the requested fields
        # (sanitise comment values to prevent newlines from breaking .hea format)
        comments = [f'UID: {uid}'] + [
            self._sanitise_comment_value(meta.get(field), field)
            for field in fields_to_write]
        # #### write the record; write_dir must already exist (ECGTable
        # creates ctx.target before any writer is invoked)
        wfdb.wrsamp(
            self._INVALID_CHARS.sub('_', str(uid)),
            fs=fs,
            units=[units] * len(sig_name),
            sig_name=sig_name,
            p_signal=p_signal,
            fmt=[self._FMT] * len(sig_name),
            comments=comments,
            write_dir=ctx.target,
        )
