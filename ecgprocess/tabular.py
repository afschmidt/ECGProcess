'''
A module to process ECG signal data and metadata to tabular form. This also
includes 2D figures - which are strictly speaking tables of pixels.

The module leverages the existing process class instances and based on their
class attributes extracts the requested data.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import os
# import re
import sys
import uuid
import pathlib
import logging
import numpy as np
import pandas as pd
# filtering out TF warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
# import matplotlib.pylab as plt
from typing import (
    Callable, Self, Optional, Any, Literal,
)
from ecgprocess.errors import (
    FileValidationError,
    XMLValidationError,
    NotCalledError,
    InputValidationError,
    is_type,
    Error_MSG,
    Warn_MSG,
    STDOUT_MSG,
    _check_readable,
    _check_presence,
)
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.utils.general import (
    replace_with_tar,
    _update_kwargs,
    chunk_list,
    update_dict_with_warning,
)
# from ecgprocess.plot_ecgs import (
#     ECGDrawing,
# )
from ecgprocess.utils.reader_tools import(
    BaseReader,
)
from ecgprocess.utils.ecg_tools import(
    signal_dicts_to_numpy_array,
)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CMeta = Core.MetaData
_log = logging.getLogger(__name__)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Example engineering functions

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# default
def metadata_identity(metadata:dict[str, Any], verbose:bool=False,
                      **kwargs) -> dict[str, Any]:
    """
    A place holder identity function, simply returning the same input data
    """
    is_type(verbose, bool)
    if verbose:
        print(**kwargs)
    return metadata

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# default
def signal_identity(signals:dict[str, np.ndarray], verbose:bool=False,
                      **kwargs) -> dict[str, Any]:
    """
    A place holder identity function, simply returning the same input data
    """
    is_type(verbose, bool)
    if verbose:
        print(**kwargs)
    if not TabNames.META_DICT in kwargs:
        raise KeyError(f"`{TabNames.META_DICT}` should be included as kwargs")
    return signals

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class ECGTable(object):
    '''
    Takes an `BaseReader` instance and loops over a supplied list of files
    containing ECG data and extract relevant information  using a `Processing`
    instance and a `Configuration` instance. The extracted information can be
    mapped to a Pandas.DataFrame or saved to disk.
    
    Parameters
    ----------
    ecgreader : `BaseReader`
        An instance of the BaseReader data class.
    path_list : `list` [`str`]
        A list of paths to one or more files containing ECG data.
    extract_meta : `bool`, default True
        Whether to extract the metadata data.
    extract_wave : `bool`, default True
        Whether to extract the raw waveforms.
    extract_median : `bool`, default True
        Whether to extract the median beats.
    engineer_meta : `Callable`, default `metadata_identity`
        A function applied to the internal meta_dict object. Please ensure
        the function includes parameter: `meta_dict`.
    engineer_wave : `Callable`, default `signal_identity`
        A function applied to the internal wave_dict object. Please ensure
        the function includes parameters: `wave_dict` and `**kwargs`.
    engineer_median : `Callable`, default `signal_identity`
        A function applied to the internal median_dict object. Please ensure
        the function includes parameters: `median_dict` and `**kwargs`.
    schema : `str` or `NoneType`, default `NoneType`
        The path to an optional XSD schema to validate XML files. Set to
        None to ignore.
    signal_length_w : `int` or `None`, default: `None`
        Target sample count for the per-record `WaveForms` signals. When
        set, each lead is right-padded with `pad_value` or right-truncated
        to this length inside `write_ecg`'s per-record loop, before
        `engineer_wave` runs. `None` disables waveform pad/truncate.
        The output column ``'sampling number padded (waveforms)'``
        records this target value (or ``None``); it does not confirm
        that padding actually changed the array length.
        signal length is equal to duration (second) by sampling rate (Hz).
        For a standard 10 second ECG with 500 Hz the sampling rate is 5,000.
    signal_length_m : `int` or `None`, default: `None`
        Target sample count for the per-record `MedianBeats` signals;
        same semantics as `signal_length_w` for medians. The output
        column ``'sampling number padded (medianbeats)'`` records this
        target value (or ``None``). For a 1.2 second median beat an 500 Hz
        sampling rate the expected sampling rate would be 600.
    pad_value : `int` or `float`, default: `0.0`
        Fill value used when right-padding shorter signals. The date type of
        the original array is preserved.
    
    Attributes
    ----------
    raw_path_list : `list` [`str`]
        A list of file paths.
    
    Methods
    -------
    get_table(unique, **kwargs)
        extract ECG data and maps these to class attributes.
    write_ecg(chunk, target_tar, target_path, tar_mode, file_type, tab_sep,
    tab_compression, tab_append, unique, write_failed, write_chunk_record,
    kwargs_reader, kwargs_tab)
        writes processed ECG data to a single or multiple files.
    
    Notes
    -----
    The engineering parameters can be used to supply functions that will be
    applied separately to dictionaries of each processed file before these
    dictionaries are combined and written to disk. The functions are applied in
    the following order to the internal objects: meta_dict (for metadata),
    wave_dict (for waveform signals), median_dict (for medianbeats signals).
    Please ensure the waveform and medianbeats functions includes a **kwargs
    parameter. The kwargs will be used internally to include the metadata. This
    ensures for example, that the engineer_wave function will have access to
    the metadata.
    '''
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, ecgreader:BaseReader, path_list:list[str],
                 extract_meta:bool=True, extract_wave:bool=True,
                 extract_median:bool=True,
                 engineer_meta:Callable=metadata_identity,
                 engineer_wave:Callable=signal_identity,
                 engineer_median:Callable=signal_identity,
                 schema:str | None = None,
                 signal_length_w:int | None = None,
                 signal_length_m:int | None = None,
                 pad_value:int | float = 0.0,
                 ) -> None:
        """
        Initialises a new instance of `ECGTable`.
        """
        # #### check input
        is_type(ecgreader, BaseReader)
        is_type(path_list, list)
        is_type(extract_meta, bool)
        is_type(extract_wave, bool)
        is_type(extract_median, bool)
        is_type(schema,
                (str, pathlib.PosixPath, pathlib.WindowsPath, type(None)))
        is_type(signal_length_w, (int, type(None)))
        is_type(signal_length_m, (int, type(None)))
        is_type(pad_value, (int, float))
        # length params, when supplied, must be strictly positive
        if signal_length_w is not None and signal_length_w <= 0:
            raise InputValidationError(
                f"`signal_length_w` must be > 0; got {signal_length_w}.")
        if signal_length_m is not None and signal_length_m <= 0:
            raise InputValidationError(
                f"`signal_length_m` must be > 0; got {signal_length_m}.")
        # #### assign to self
        self.ecgreader = ecgreader
        setattr(self, TabNames.E_META, extract_meta)
        setattr(self, TabNames.E_WAVE, extract_wave)
        setattr(self, TabNames.E_MEDIAN, extract_median)
        setattr(self, TabNames.ENG_META, engineer_meta)
        setattr(self, TabNames.ENG_WAVE, engineer_wave)
        setattr(self, TabNames.ENG_MEDIAN, engineer_median)
        setattr(self, TabNames.RPATH_L, path_list)
        setattr(self, TabNames.SCHEMA, schema)
        setattr(self, TabNames.SIG_LEN_W, signal_length_w)
        setattr(self, TabNames.SIG_LEN_M, signal_length_m)
        setattr(self, TabNames.PAD_VALUE, pad_value)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME} instance with "
                f"ecgreader={self.ecgreader}, "
                f"path_list={getattr(self, TabNames.RPATH_L)}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME}(ecgreader={self.ecgreader}, "
                f"path_list={getattr(self, TabNames.RPATH_L)})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _pad_or_truncate(self,
                         signals:dict[str, np.ndarray] | None,
                         target_length:int,
                         pad_value:int | float,
                         ) -> dict[str, np.ndarray] | None:
        """
        Right-pad or right-truncate each lead in `signals` to a fixed
        sample count. Applies in place mutations.
        
        Parameters
        ----------
        signals : `dict` [`str`, `np.ndarray`] or `None`
            Per-lead signal dict. `None` passes through. `None` lead
            values inside the dict pass through unchanged.
        target_length : `int`
            Target sample count per lead. Shorter arrays are right-padded
            with `pad_value`; longer arrays are right-truncated; equal
            length will not be affected.
        pad_value : `int` or `float`
            Fill value used for right-padding. The dtype of the original
            array is preserved by allocating with `dtype=arr.dtype`.
        
        Returns
        -------
        signals : `dict` [`str`, `np.ndarray`] or `None`
            The same dict object, with lead values replaced by their
            padded / truncated counterparts. Returned for symmetry with
            the engineer callables (`engineer_wave`, `engineer_median`),
            which take a signal dict and return a signal dict.
        
        Notes
        -----
        Mutates `signals` in place. The reader instance is recreated for
        every file by `_loop_table` (`self.ecgreader(p, ...)`), so the
        in-place mutation cannot leak across records. The engineer
        callables run after this method, so they observe the fixed-length
        arrays.
        """
        # Skip if none
        if signals is None:
            return None
        for lead, arr in signals.items():
            # `None` lead values are legitimate (an engineer callable
            # may null out a lead); preserve them as-is.
            if arr is None:
                continue
            # get signal length and compare to current
            current = arr.shape[0]
            if current == target_length:
                # skip if equal
                continue
            if current > target_length:
                # Right-truncate. `arr[:n]` is a view; `.copy()`
                # decouples the replacement from the original numpy buffer.
                signals[lead] = arr[:target_length].copy()
                continue
            # If all false right-pad
            # Single allocation of the target dtype; the
            # explicit `dtype=arr.dtype` prevents int->float upcast
            # that `np.pad(constant_values=...)` performs silently.
            padded = np.full(target_length, pad_value, dtype=arr.dtype)
            padded[:current] = arr
            signals[lead] = padded
        return signals
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, ignore_permission:bool = True, ignore_data:bool = False,
                 ignore_invalid:bool = False, confirm_meta:bool=False,
                 confirm_wave:bool=False, confirm_median=False,
                 verbose:bool=False,
                 ) -> Self:
        """
        Will take a BaseReader instance and loops over a list of file paths
        and and confirm the files exist and have appropriate read permission.
        
        Parameters
        ----------
        ignore_permission : `bool`, default True
            Skips file permission errors. The failed file names will be
            recorded for review.
        ignore_data : `bool`, default False
            Whether files with missing MetaData, WaveForm, or MedianBeat
            attributes should be skipped. The file names for these failures
            will be recorded.  Note, to limit I/O calls this step will not
            be conducted during __call__ and instead will be applied when
            processing data using any method with utilises `_loop_table`.
        ignore_invalid : `bool`, default False
            Whether XML files who failed to an XSD validation schema should
            be skipped. Note, to limit I/O calls schema validation will not be
            conducted during __call__ and instead will be applied when
            processing data using any method with utilises `_loop_table`.
        confirm_meta, confirm_wave, confirm_meta : `bool`, default False
            Whether to skip extraction the entire file when the indicated
            attribute is empty.
        verbose : `bool`, default `False`
            Whether to print warnings.
        
        Attributes
        ----------
        failed_path_list : `list` [`str`]
            File paths which are either absent or without read permission.
        curated_path_list : `list` [`str`]
            File paths which are readable.
        
        Returns
        -------
        ECGTable instance
            Returns the class instance with updated attributes.
        """
        # #### check input
        is_type(ignore_data, bool)
        is_type(ignore_permission, bool)
        is_type(ignore_invalid, bool)
        is_type(verbose, bool)
        # #### assign to self
        self.verbose = verbose
        setattr(self, TabNames.SKIP_PERM, ignore_permission)
        setattr(self, TabNames.SKIP_DATA, ignore_data)
        setattr(self, TabNames.SKIP_INVALID, ignore_invalid)
        setattr(self, TabNames.CONFIRM_META, confirm_meta)
        setattr(self, TabNames.CONFIRM_WAVE, confirm_wave)
        setattr(self, TabNames.CONFIRM_MEDIAN, confirm_median)
        # #### confirm internal logic
        MSG_LOGIC="`{}` is True but `{}` is False, please adjust."
        if getattr(self, TabNames.CONFIRM_META) == True and\
                getattr(self, TabNames.E_META) == False:
                    raise ValueError(MSG_LOGIC.format(
                        TabNames.CONFIRM_META, TabNames.E_META))
        if getattr(self, TabNames.CONFIRM_WAVE) == True and\
                getattr(self, TabNames.E_WAVE) == False:
                    raise ValueError(MSG_LOGIC.format(
                        TabNames.CONFIRM_WAVE, TabNames.E_WAVE))
        if getattr(self, TabNames.CONFIRM_MEDIAN) == True and\
                getattr(self, TabNames.E_MEDIAN) == False:
                    raise ValueError(MSG_LOGIC.format(
                        TabNames.CONFIRM_MEDIAN, TabNames.E_MEDIAN))
                                                      
        # #### loop over path
        empty_list = []
        curated_list = []
        # #### loop over individual files and assign to self
        for p in getattr(self, TabNames.RPATH_L):
            try:
                # add p and remove if skipp_missing == True
                curated_list.append(p)
                _check_readable(p)
            except PermissionError as PE:
                empty_list.append(p)
                # try next
                if getattr(self, TabNames.SKIP_PERM):
                    curated_list.pop()
                    pass
                else:
                    raise PE
        setattr(self, TabNames.FPATH_L, empty_list)
        setattr(self, TabNames.CPATH_L, curated_list)
        # #### do we want to print the list of invalid files.
        if len(getattr(self, TabNames.FPATH_L)) > 0:
            _log.warning(
                'The following files could not be accessed or found: %s.',
                getattr(self, TabNames.FPATH_L),
            )
        # #### Return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _loop_table(self, path_list:list[str],
                    parsed_config:ConfigParser,
                    unique:bool=True,
                    kwargs_reader_call:dict[Any, Any] | None = None,
                    kwargs_reader_extract:dict[Any, Any] | None = None,
                  ) -> tuple[list[dict[str, Any]], list[dict[str, np.ndarray]],
                             list[dict[str, np.ndarray]]]:
        """
        Will loop over the supplied files and extract ECG data.
        
        Parameters
        ----------
        path_list : `list` [`str`]
            A list of paths to one or more files containing ECG data.
        parsed_config : `ConfigParser`
            A parsed configuration file which was mapped using
            `ConfigParser.map`.
        unique : `bool`, default `True`
            ensures the `UID` metadata items are unique between files. Please
            ensure the UID key-value pair is appropriately set in
            the config file. If set to false a file-specific integer key will
            be assigned instead.
        kwargs_reader_call: `dict` [`any`, `any`]  or None, default `NoneType`
            passed to the kwargs of the `BaseReader` call method.
        kwargs_reader_extract: `dict` [`any`, `any`]  or None, default `NoneType`
            passed to the `BaseReader` extract method.
         
        Attributes
        ----------
        key_list: `list` [`str`]
            A list of unique identifiers.
        no_data_list : `list` [`str`]
            A list of files without the requested attributes: MetaData,
            WaveForms, and/or MedianBeats.
        invalid_list : `list` [`str`]
            A list of files which failed to validate.
        _id_start_number : `int`
            Records the integer start number used as place holder UID when
            unique = `False`. This attributes ensures UIDs are unique across
            multiple calls to the method.
        
        Returns
        -------
        tuple of list
            the metadata, waveform signals, and medianbeats signals.
        
        Notes
        -----
        To keep track of multiple ECG files the function will try to use the
        the privileged variable UID. If this is not found in the supplied
        `MetaData` it will instead assign an integer value starting from 1 for
        each file processed.
        """
        # #### check input
        # NOTE path_list has already been test - not doing this again because
        # it is a private method.
        is_type(unique, bool)
        # if kwargs is None assigned an empty dict
        kwargs_reader_call = kwargs_reader_call or {}
        kwargs_reader_extract = kwargs_reader_extract or {}
        kwargs_reader_extract = _update_kwargs(
            update_dict=kwargs_reader_extract, config=parsed_config,
        )
        # #### check if __call__ has been run
        # note that we are not directly using this attribute otherwise and
        # instead using the supplied path_list.
        if not hasattr(self, TabNames.CPATH_L):
            raise NotCalledError()
        # #### extract data
        meta_list, wave_list, median_list = [[] for _ in range(3)]
        # the lists will be appended after each iteration
        if hasattr(self, TabNames.KEY_L) == False:
            setattr(self, TabNames.KEY_L, [])
        if hasattr(self, TabNames.NO_DATA_L) == False:
            setattr(self, TabNames.NO_DATA_L, [])
        if hasattr(self, TabNames.INVALID_L) == False:
            setattr(self, TabNames.INVALID_L, [])
        if hasattr(self, TabNames.ID_START) == False:
            setattr(self, TabNames.ID_START, 1)
        # loop over individual files
        for i, p in enumerate(path_list,
                              start=getattr(self, TabNames.ID_START)):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance and check how errors should be handled
            if not getattr(self, TabNames.SCHEMA) is None:
                try:
                    ecg_inst = self.ecgreader(
                        p, schema=getattr(self, TabNames.SCHEMA),
                        verbose=self.verbose,
                        **kwargs_reader_call)
                    ecg_inst = ecg_inst.extract(**kwargs_reader_extract)
                except XMLValidationError as XML_VAL:
                    getattr(self, TabNames.INVALID_L).append(p)
                    if getattr(self, TabNames.SKIP_INVALID):
                        continue
                    else:
                        raise XML_VAL
            else:
                try:
                    ecg_inst = self.ecgreader(p, verbose=self.verbose,
                                              **kwargs_reader_call)
                    ecg_inst = ecg_inst.extract(**kwargs_reader_extract)
                except AttributeError as AE:
                    getattr(self,TabNames.NO_DATA_L).append(p)
                    if getattr(self, TabNames.SKIP_DATA):
                        continue
                    else:
                        raise AE
            # extract unique identifier.
            if unique == True:
                if hasattr(ecg_inst, CTypes.MetaData) == False:
                    raise AttributeError('`unique` is `True`, but there is '
                                         'no MetaData to extract the UID from.'
                                         )
                else:
                    if not getattr(ecg_inst, CTypes.MetaData)[CMeta.UID] is None:
                        key = str(
                            getattr(ecg_inst, CTypes.MetaData)[CMeta.UID]
                        )
                    else:
                        raise KeyError(f"`{CMeta.UID}` is None.")
            else:
                key = str(i)
            # confirm the key is unique
            if key in getattr(self, TabNames.KEY_L):
                raise IndexError(
                    'The current file seems to have been extracted already. '
                    'Please ensure the supplied files are unique. '
                    f'This is the current file ID {key} and these '
                    'are the IDs of the processed files '
                    f'{getattr(self, TabNames.KEY_L)}.'
                )
            else:
                getattr(self, TabNames.KEY_L).append(key)
            # empty objects
            meta_temp = []
            wave_temp, median_temp = ({} for _ in range(2))
            # pad/truncate config (None when the user did not opt in).
            sig_len_w = getattr(self, TabNames.SIG_LEN_W)
            sig_len_m = getattr(self, TabNames.SIG_LEN_M)
            pad_value = getattr(self, TabNames.PAD_VALUE)
            # append metadata.
            meta_available = False
            if getattr(self, TabNames.E_META):
                try:
                    meta_temp = getattr(ecg_inst, CTypes.MetaData)
                    # add key to meta data
                    meta_temp[TabNames.KEY] = key
                    # add filename
                    meta_temp[TabNames.FILENAM] = p
                    # Added padded columns - will stay None if not used.
                    meta_temp[TabNames.SN_W_PADDED] = sig_len_w
                    meta_temp[TabNames.SN_M_PADDED] = sig_len_m
                    # DURATION_PADDED is waveforms-only and needs the
                    # original sampling frequency; emit a warning when the
                    # user opted in but SF disagrees with the assumed
                    # 500 Hz that the rest of the pipeline targets.
                    # duration pad is len/sampling freq
                    sf_val = meta_temp.get(CMeta.SF)
                    if sig_len_w is not None and sf_val:
                        meta_temp[TabNames.DURATION_PADDED] = (
                            sig_len_w / sf_val)
                        if sf_val != 500:
                            _log.warning(
                                "Pad/truncate target assumes 500 Hz but "
                                "%s=%s for file %s.",
                                CMeta.SF, sf_val, p,
                            )
                    else:
                        meta_temp[TabNames.DURATION_PADDED] = None
                    # available.
                    meta_available = True
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        # skip the entire run there if there is metadata
                        getattr(self,TabNames.NO_DATA_L).append(p)
                        if getattr(self, TabNames.CONFIRM_META):
                            getattr(self,TabNames.NO_DATA_L).append(p)
                            continue
                    else:
                        raise AE
                if meta_available == True:
                    try:
                        # piping the metadata through the engineer function
                        meta_org = meta_temp.copy()
                        meta_new =\
                            getattr(self, TabNames.ENG_META)(
                                meta_temp,
                            )
                        if getattr(self, TabNames.CONFIRM_META):
                            # skip if everything is None
                            if all(v is None for v in meta_new.values()):
                                getattr(self,TabNames.NO_DATA_L).append(p)
                                continue
                        # `meta_temp` is supplied to the wave/median functions
                        meta_temp = update_dict_with_warning(
                            meta_org, meta_new, verbose=self.verbose)
                    except FileValidationError as FILE_VAL:
                        getattr(self, TabNames.INVALID_L).append(p)
                        if getattr(self, TabNames.SKIP_INVALID):
                            continue
                        else:
                            raise FILE_VAL
            # Append waveform signals.
            if getattr(self, TabNames.E_WAVE):
                try:
                    # piping the waveform signals through the engineer function
                    # metadata is supplied through the function kwargs
                    wave_temp = getattr(ecg_inst, CTypes.WaveForms)
                    # opt-in pad/truncate before the engineer runs so the
                    # engineer (and every downstream writer) sees fixed
                    # length arrays.
                    if sig_len_w is not None:
                        wave_temp = self._pad_or_truncate(
                            wave_temp, sig_len_w, pad_value)
                    wave_temp =\
                        getattr(self, TabNames.ENG_WAVE)(
                            wave_temp, meta_dict=meta_temp
                        )
                    if getattr(self, TabNames.CONFIRM_WAVE):
                        # skip if everything is None
                        if all(v is None for v in wave_temp.values()):
                            getattr(self,TabNames.NO_DATA_L).append(p)
                            continue
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        getattr(self,TabNames.NO_DATA_L).append(p)
                        # do we want to skip the entire file?
                        if getattr(self, TabNames.CONFIRM_WAVE):
                            getattr(self,TabNames.NO_DATA_L).append(p)
                            continue
                    else:
                        raise AE
            # Append median beat signals.
            if getattr(self, TabNames.E_MEDIAN):
                try:
                    # piping the medianbeats signals through the engineer
                    # function metadata is supplied through the function kwargs
                    median_temp = getattr(ecg_inst, CTypes.MedianBeats)
                    # opt-in pad/truncate (see waveform block above).
                    if sig_len_m is not None:
                        median_temp = self._pad_or_truncate(
                            median_temp, sig_len_m, pad_value)
                    median_temp =\
                        getattr(self, TabNames.ENG_MEDIAN)(
                        median_temp, meta_dict=meta_temp,
                        )
                    if getattr(self, TabNames.CONFIRM_MEDIAN):
                        # skip if everything is None
                        if all(v is None for v in median_temp.values()):
                            getattr(self,TabNames.NO_DATA_L).append(p)
                            continue
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        getattr(self,TabNames.NO_DATA_L).append(p)
                        # do we want to skip the entire file?
                        if getattr(self, TabNames.CONFIRM_MEDIAN):
                            getattr(self,TabNames.NO_DATA_L).append(p)
                            continue
                    else:
                        raise AE
            # append to lists
            if getattr(self, TabNames.E_META):
                meta_list.append(meta_new)
            if getattr(self, TabNames.E_WAVE):
                wave_list.append(wave_temp)
            if getattr(self, TabNames.E_MEDIAN):
                median_list.append(median_temp)
            # make sure this object is unique
            setattr(self,TabNames.NO_DATA_L, list(np.unique(
                getattr(self,TabNames.NO_DATA_L))))
        # record and update the last ID_START
        setattr(self, TabNames.ID_START, i+1)
        # to we want to print warnings?
        if len(getattr(self, TabNames.NO_DATA_L)) > 0:
            _log.warning(
                'The following files do not have the requested data: %s.',
                getattr(self, TabNames.NO_DATA_L),
            )
        if len(getattr(self, TabNames.INVALID_L)) > 0:
            _log.warning(
                'The following XML files could not be validated: %s.',
                getattr(self, TabNames.INVALID_L),
            )
        # check data and return
        return meta_list, wave_list, median_list
    # /////////////////////////////////////////////////////////////////////////
    def get_table(self,
                  parsed_config:ConfigParser,
                  unique:bool=True,
                  kwargs_reader_call:dict[Any, Any] | None = None,
                  kwargs_reader_extract:dict[Any, Any] | None = None,
                  ) -> Self:
        """
        Returns ECG data as pandas.DataFrames.
        
        Parameters
        ----------
        parsed_config : `ConfigParser`
            A parsed configuration file which was mapped using
            `ConfigParser.map`.
        unique : `bool`, default `True`
            ensures the `UID` metadata items are unique between files. Please
            ensure the UID key-value pair is appropriately set in
            the config file. If set to false a file-specific integer key will
            be assigned instead.
        kwargs_reader_call: `dict` [`any`, `any`]  or None, default `NoneType`
            passed to the kwargs of the `BaseReader` call method.
        kwargs_reader_extract: `dict` [`any`, `any`]  or None, default `NoneType`
            passed to the `BaseReader` extract method.
        
        Attributes
        ----------
        MetaDataTable: pandas.DataFrame
            A table of the metadata.
        WaveFormsTable: pandas.DataFrame
            A long-formatted table with waveforms signals.
        MedianBeatsTable: pandas.DataFrame
            A long-formatted table with the median beat signals.
        
        Returns
        -------
        `ECGTable` instance
            Returns the class instance with updated attributes.
        
        Notes
        -----
        To keep track of multiple ECG files the function will try to use the
        privileged variable UID. If this is not found in the supplied
        `MetaData` the function will instead assign an integer starting from
        1 as a unique key.
        """
        # #### run loop
        try:
            meta_list, wave_list, median_list = self._loop_table(
                getattr(self, TabNames.CPATH_L),
                parsed_config=parsed_config, unique=unique,
                kwargs_reader_call=kwargs_reader_call,
                kwargs_reader_extract=kwargs_reader_extract,
            )
            # #### make tables and assign these to self
            if getattr(self, TabNames.E_META):
                setattr(self, CTypes.MetaData, pd.DataFrame(
                    meta_list, index=getattr(self, TabNames.KEY_L)
                ))
            if getattr(self, TabNames.E_WAVE):
                setattr(self, CTypes.WaveForms, self._get_long_table(
                    wave_list, signal_type=CTypes.WaveForms,
                    purge_header=True,
                ))
            if getattr(self, TabNames.E_MEDIAN):
                setattr(self, CTypes.MedianBeats, self._get_long_table(
                    median_list, signal_type=CTypes.MedianBeats,
                    purge_header=True,
                ))
        finally:
            # cleaning-up.
            if hasattr(self, TabNames.KEY_L) == True:
                delattr(self, TabNames.KEY_L)
            if hasattr(self, TabNames.NO_DATA_L) == True:
                delattr(self, TabNames.NO_DATA_L)
            if hasattr(self, TabNames.INVALID_L) == True:
                delattr(self, TabNames.INVALID_L)
            if hasattr(self, TabNames.ID_START) == True:
                delattr(self, TabNames.ID_START)
        # #### Return
        setattr(self, TabNames.TABLE_CALLED, 'True')
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _get_long_table(self, lead_list:list[dict[str, np.ndarray]],
                        signal_type:str, purge_header:bool=True,
                        **kwargs,
                        ) -> pd.DataFrame:
        '''
        Mapping lists of dictionaries containing lead specific numpy arrays
        to a long-formatted pandas table.
        
        Parameters
        ----------
        lead_list : `list` [`dict` [`str`, `np.ndarray`]
            A list of dictionaries with the lead names mapped to the keys and
            the voltage mapped to the values.
        signal_type : `str`,
            Adds a column `Waveform type` containing this string as a constant.
        purge_header : `bool`, default True
            Set to `False` to make sure the file header persists between calls.
            This is used to ensure the headers are the same between files.
        kwargs
            keyword arguments passed to pd.DataFrame.
        
        Returns
        -------
        pd.DataFrame
            A long-formatted table with lead, voltage, sampling sequence
            columns grouped by file (including an unique file indicator column)
        '''
        # #### check input and set constants
        is_type(lead_list, list, 'lead_list')
        is_type(signal_type, str, 'signal_type')
        kwargs_pdd = kwargs
        PREV = 'previous'
        SAMPLING_SEQ = 'Sampling sequence'
        # do we need to purge the header information
        # otherwise this persists across repeated calls
        if purge_header == True:
            setattr(self, PREV, None)
        else:
            if not hasattr(self, PREV):
                setattr(self, PREV, None)
        # #### initiate table and map lists
        table = pd.DataFrame()
        # NOTE w contains a dictionary with k: lead names and v: signals.
        for w, k in zip(lead_list, getattr(self, TabNames.KEY_L), strict=True):
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
            if getattr(self, PREV) is not None:
                if current_keys != getattr(self, PREV):
                    raise KeyError('The dictionaries contain distinct keys. '
                                   'The last set of valid keys was {}, '
                                   'compared to {}.'.\
                                   format(getattr(self, PREV), current_keys))
            # ##### if the same map to dataframe
            temp_df = pd.DataFrame(w, **kwargs_pdd)
            temp_df[TabNames.KEY] = k
            # FIXME this will be fairly slow/inefficient
            table = pd.concat([table, temp_df], ignore_index=True)
            # clean
            setattr(self, PREV, current_keys)
            del current_keys
            del temp_df
        # #### formatting to long
        if table.empty == False:
            table[SAMPLING_SEQ] = table.groupby(
                TabNames.KEY).cumcount()
            long_table = pd.melt(table, id_vars=\
                                 [TabNames.KEY, SAMPLING_SEQ],
                                 value_vars=getattr(self, PREV),
                                 var_name='Lead',
                                 value_name='Voltage',
                                 )
            long_table['Signal type'] = signal_type
        else:
            long_table = table
        # #### return
        return long_table
    # /////////////////////////////////////////////////////////////////////////
    def write_ecg(self, parsed_config=ConfigParser,
                  chunk:int | None = None, target_tar: None | str = None,
                  target_path:str='.', tar_mode:str='w:gz',
                  file_type:Literal['table', 'numpy', 'tensorflow'] = 'table',
                  tab_sep:str='\t', tab_compression:str | None ='gzip',
                  tab_append:bool=True, unique:bool=True,
                  write_failed:bool=True, write_chunk_record:bool = False,
                  kwargs_reader_call:dict[Any, Any] | None = None,
                  kwargs_reader_extract:dict[Any, Any] | None = None,
                  kwargs_tab: None | dict[str, Any] = None,
                  ) -> Self:
        '''
        Extracts chunks of ECG data, and writes these to a single or multiple
        target files which can be optionally tar compressed.
        
        Parameters
        ----------
        parsed_config : `ConfigParser`
            A parsed configuration file which was mapped using
            `ConfigParser.map`.
        chunk : `int`, default `NoneType`
            The number of sources files written to a single processed file. For
            `file_type=table` set this to 1 with `tab_append=True` minimise the
            memory fingerprint.  Set to `NoneType` to combine all the ECG data
            into a single target file.
        target_tar : `str`, default `NoneType`
            The `name` of an optional tarfile where the individual files will
            be written to. The target_tar will be concatenated to
            `target_path`. Depending on the `mode` this directory will be
            tar.gz compressed for example.  Set `target_tar` to `NoneType` to
            simply add the files directly to `target_path`.
            Note this will overwrite any potential directory or file with the
            provide name.
        target_path : `str`, default '.'
            The full path where the files should be written to. If provided
            `target_tar` will be created underneath this path, otherwise the
            files will be directly written to the `target_path` terminal
            directory (assuming this is writable).
        file_type : {'table', 'numpy', 'tensorflow'}, default `table`
            Whether to write the files to `tsv` using pandas.DataFrame, to `npz`
            using numpy.savez, or to `tfrecord` using
            tensorflow.io.TFRecordWriter.
        tar_mode : `str`, default `w:gz`
            The tarfile.open mode.
        tab_sep : `str`, default `\\t`
            The file separator, which will be passed to
            pandas.DataFrame.to_csv.
        tab_compression : `str`, default `gzip`
            The file compression passed to pandas.DataFrame.to_csv.
        tab_append : `bool`, default True
            Whether individual chunks should be appended to the `tsv` file.
        unique : `bool`, default `True`
            ensures the `UID` metadata items are unique between files. Please
            ensure the UID metadata key value pair is appropriately set in
            the config file. If set to False an file-specific integer key will
            be assigned instead.
        write_failed : `bool`, default `True`
            Whether to write a text file to disk containing the failed file
            names with some information on why these failed.
        write_chunk_record : `bool`, default `True`
            Whether to include a record matching the chunk indicator to the
            files included in each chunk.
        kwargs_reader_call: `dict` [`any`, `any`]  or `None`, default `NoneType`
            passed to the kwargs of the `BaseReader` call method.
        kwargs_reader_extract: `dict` [`any`, `any`]  or `None`, default `NoneType`
            passed to the `BaseReader` extract method.
        kwargs_tab : `dict` [`str`, `any`] or `None`, default `None`
            Keyword argument for `pd.DataFrame.to_csv`.
        
        Attributes
        ----------
        target_path : `str`
            The directory or tar file path were the files are written to.
        
        Returns
        -------
        `ECGTable` instance
            The class instance with updated attributes.
        
        Raises
        ------
        NotADirectoryError or PermissionError
            If the target directory does not exist or is not writable.
        
        Notes
        -----
        While file_type='table' can store any kind of information, numpy and
        tfrecord are best used to store numerical/float data. Currently
        non-numerical data are therefore drooped from metadata for these
        filetypes.
        
        For numpy and tfrecord the signal data will be automatically
        zero-padded to the longest signal. Missing signals will be presented
        as np.nan. The array columns match the canonical ECG lead order, please
        refer to `ecg_tools.signal_dicts_to_numpy_array` for the exact order.
        '''
        # #### set defaults
        self.kwargs_tab = kwargs_tab or {}
        # expected file_types
        EXP_WRITE=[TabNames.WRITE_TAB, TabNames.WRITE_NUMPY,
                   TabNames.WRITE_TFLOW]
        # #### check input
        is_type(parsed_config, ConfigParser)
        is_type(chunk, (type(None), int))
        is_type(target_tar, (type(None), str))
        is_type(target_path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(tar_mode, str)
        is_type(tab_append, bool)
        is_type(tab_sep, str)
        is_type(tab_compression, (type(None), str))
        is_type(write_failed, bool)
        is_type(write_chunk_record, bool)
        is_type(file_type, str)
        # set to self
        setattr(self, TabNames.WRITE_TYPE, file_type)
        # confirm file_type is correct
        if not file_type in EXP_WRITE:
            raise ValueError(
                Error_MSG.CHOICE_PARM.format('file_type', EXP_WRITE))
        # check readability
        _check_presence(target_path)
        _check_readable(target_path)
        # #### create target path
        # get the current wd if requested
        if target_path == '.':
            target_path = os.getcwd()
        # create a temp directory under target_path or otherwise simply use
        # target_path
        if target_tar is not None:
            # adding a temp dir
            target = os.path.join(target_path, str(uuid.uuid4()))
            # make the new child dir
            # NOTE if target_tar has extensions such as `tar.gz` this will be
            # included but the directly is not really compressed (will be done
            # below).
            os.makedirs(target, exist_ok=True)
        else:
            target = target_path
            setattr(self, TabNames.WRITE_ECG_PATH, target)
        # #### extract data
        chunk_record = {}
        # chunk data
        if not chunk is None:
            path_list = chunk_list(getattr(self, TabNames.CPATH_L), chunk)
            
        else:
            # making this into  single chunk [[ ]]
            path_list = [getattr(self, TabNames.CPATH_L)]
        # NOTE First is only relevant when writing to a file using append.
        first=True
        # #### loop over the path_list
        try:
            for n, p in enumerate(path_list, start=1):
                # record the chunk_number and the files included
                # NOTE `p` is a list and `n` an integer
                chunk_record[n] = p
                # extract data
                meta_list, wave_list, median_list = self._loop_table(
                    p, parsed_config=parsed_config,
                    unique=unique,
                    kwargs_reader_call=kwargs_reader_call,
                    kwargs_reader_extract=kwargs_reader_extract,
                )
                # write based on the supplied file type
                if getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TAB:
                    if tab_append == False:
                        self._write_tab(
                            meta_list, wave_list, median_list, target,
                            chunk_num=n if chunk is not None else None,
                            header=True, sep=tab_sep,
                            compression=tab_compression,
                                        )
                    # Write to a single file
                    elif first==True:
                        first = False
                        # write first file
                        self._write_tab(meta_list, wave_list, median_list,
                                        target, chunk_num=None,
                                        header=True, sep=tab_sep,
                                        compression=tab_compression,
                                        )
                    else:
                        # append
                        self._write_tab(meta_list, wave_list, median_list,
                                        target, chunk_num=None,
                                        header=False, mode='a', sep=tab_sep,
                                        compression=tab_compression,
                                        )
                if getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_NUMPY:
                    self._write_numpy(
                        meta_list, wave_list, median_list, target,
                        chunk_num=n if chunk is not None else None,
                    )
                if getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TFLOW:
                    self._write_tfr(
                        meta_list, wave_list, median_list, target,
                        chunk_num=n if chunk is not None else None,
                    )
                # deleting the current key list
                if hasattr(self, TabNames.KEY_L) == True:
                    delattr(self, TabNames.KEY_L)
            # #### write chunk record
            if write_chunk_record:
                chnk_lst = []
                for cnum, fpaths in chunk_record.items():
                    if isinstance(fpaths, str):
                        raise ValueError('`fpaths` should be a list, not '
                                         f'type(fpaths).')
                    # if a string check if it is `, ` separated and map to
                    # list
                    # CHUNK_SPLIT = ', '
                    # if CHUNK_SPLIT in chunk_record:
                    #     # NOTE using strip to remove redundant white space
                    #     fpaths = [s.strip() for s in fpaths.split(CHUNK_SPLIT)]
                    print('fpaths: ')
                    print(fpaths)
                    print(type(fpaths))
                    # Ensure file_paths is a list or iterable of file paths:
                    for fp in fpaths:
                        chnk_lst.append({'Chunk number': cnum, 'Files': fp})
                chunk_tab = pd.DataFrame(chnk_lst)
                chunk_tab.to_csv(os.path.join(target, 'chunkrecord.txt'),
                                 sep='\t', header=True, index=False)
            # #### write failed files
            if write_failed == True:
                # adding the reason for failing
                total_failures =\
                    [(p, 'File permission') for p in\
                     getattr(self, TabNames.FPATH_L) ] +\
                    [ (p, 'No data') for p in\
                     getattr(self, TabNames.NO_DATA_L)] +\
                    [(p, 'Invalid data') for p in\
                     getattr(self, TabNames.INVALID_L)]
                # writing to text file
                with open(os.path.join(target, 'FailedFiles.txt'), 'w') as file:
                    for p, cause in total_failures:
                        file.write(p + "\t" + cause + "\n")
            # #### if needed replace directory by a tarball
            if target_tar is not None:
                # create the final target path
                target_final = os.path.join(target_path, target_tar)
                replace_with_tar(target, target_final, mode=tar_mode)
                setattr(self, TabNames.WRITE_ECG_PATH, target_final)
        finally:
            # cleaning-up.
            if hasattr(self, TabNames.NO_DATA_L) == True:
                delattr(self, TabNames.NO_DATA_L)
            if hasattr(self, TabNames.INVALID_L) == True:
                delattr(self, TabNames.INVALID_L)
            if hasattr(self, TabNames.ID_START) == True:
                delattr(self, TabNames.ID_START)
        # #### return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _write_file_names(self, chunk_num:int|None = None,
                          **kwargs:Optional[Any],
                          ) -> tuple[str, str, str, str]:
        """
        Creates filenames with relevant extensions, optionally accounting
        for chunks by adding the chunk number as suffix.
        
        Parameters
        ----------
        chunk_num : `int` or `NoneType`, default `NoneType`
            Appends the chunk number with a '_' separator before the file
            extension.
        
        Returns
        -------
        tuple of strings
            The filenames for metadata, waveforms, medianbeats, and ecg_data.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        # Set the initial filenames
        META_FILE = 'metadata'
        WAVE_FILE = 'waveforms'
        MEDIAN_FILE = 'medianbeats'
        ECG_FILE = 'ecg_data'
        SEP = ''
        CHUNK = ''
        # determine file type
        if getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TAB:
            EXT = '.tsv'
            # is the file compressed?
            try:
                if kwargs['compression'] == 'gz':
                    EXT = EXT + '.gz'
                if kwargs['compression'] == 'gzip':
                    EXT = EXT + '.gz'
                if kwargs['compression'] == 'bz2':
                    EXT = EXT + '.bz2'
                if kwargs['compression'] == 'zip':
                    EXT = EXT + '.zip'
                if kwargs['compression'] == 'xz':
                    EXT = EXT + '.xz'
                if kwargs['compression'] == 'zst':
                    EXT = EXT + '.zst'
            except KeyError:
                pass
        elif getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_NUMPY:
            EXT = '.npz'
        elif getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TFLOW:
            EXT = '.tfrecord'
        # Are we writing in chunks?
        if not chunk_num is None:
            SEP = '_'
            CHUNK = str(chunk_num)
        # the final file names
        META_FILE = META_FILE + SEP + CHUNK + EXT
        WAVE_FILE = WAVE_FILE + SEP + CHUNK + EXT
        MEDIAN_FILE = MEDIAN_FILE + SEP + CHUNK + EXT
        ECG_FILE = ECG_FILE + SEP + CHUNK + EXT
        # return
        return META_FILE, WAVE_FILE, MEDIAN_FILE, ECG_FILE
    # /////////////////////////////////////////////////////////////////////////
    def _write_tab(self, meta_list:list[dict[str, Any]],
                   wave_list:list[dict[str, np.ndarray]],
                   median_list:list[dict[str, np.ndarray]],
                   target:str,
                   chunk_num:int | None,
                   **kwargs,
                   ) -> None:
        """
        Writes data to a flat tsv table.
        
        Parameters
        ----------
        wave_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing medianbeats signals.
        target: `str`
            The target directory.
        chunk_num : `int` or `NoneType`
            Appends the chunk number with a '_' separator before the file
            extension.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        kwargs_tab_combi = {**self.kwargs_tab, **kwargs}
        # #### Set the filenames
        META_FILE, WAVE_FILE, MEDIAN_FILE, _=\
            self._write_file_names(chunk_num=chunk_num, **kwargs_tab_combi)
        # #### write individual files
        if getattr(self, TabNames.E_META):
            pd.DataFrame(meta_list, index=getattr(self, TabNames.KEY_L)
                         ).to_csv(
                os.path.join(target, META_FILE),
                **kwargs_tab_combi,
            )
        if getattr(self, TabNames.E_WAVE):
            self._get_long_table(
                wave_list, signal_type=CTypes.WaveForms,
                purge_header=True,
            ).to_csv(
                os.path.join(target, WAVE_FILE),
                **kwargs_tab_combi,
            )
        if getattr(self, TabNames.E_MEDIAN):
            self._get_long_table(
                median_list, signal_type=CTypes.MedianBeats,
                purge_header=True,
            ).to_csv(
                os.path.join(target, MEDIAN_FILE),
                **kwargs_tab_combi,
            )
    # /////////////////////////////////////////////////////////////////////////
    def _write_numpy(self, meta_list:list[dict[str, Any]],
                     wave_list:list[dict[str, np.ndarray]],
                     median_list:list[dict[str, np.ndarray]],
                     target:str,
                     chunk_num:int | None,
                     numeric_meta:bool = True,
                     ) -> None:
        """
        Writes data to a compressed numpy file `.npz`.
        
        Parameters
        ----------
        wave_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing medianbeats signals.
        target: `str`
            The target directory.
        chunk_num : `int` or `NoneType`
            Appends the chunk number with a '_' separator before the file
            extension.
        numeric_meta : `bool`, default `True`
            Whether non-numeric data should be dropped from the metadata.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        is_type(numeric_meta, bool)
        # Set the filenames
        _, _, _, ECG_FILE=\
            self._write_file_names(chunk_num=chunk_num)
        # #### write individual files
        res_dict = {}
        if getattr(self, TabNames.E_META):
            tab1  = pd.DataFrame(meta_list)
            if numeric_meta:
                old_cols = set(tab1.columns)
                tab1 = tab1.select_dtypes(include=[np.number])
                new_cols = set(tab1.columns)
                drop_cols = old_cols - new_cols
                if len(drop_cols) > 0:
                    _log.warning(Warn_MSG.DROP_NONE_NUMERIC, drop_cols)
            # get the header
            tab1_header = list(tab1.columns)
            res_dict[CTypes.MetaData] = tab1.to_numpy()
        if getattr(self, TabNames.E_WAVE):
            # `padding=False` will rely on `ECGTable._pad_or_truncate`
            res_dict[CTypes.WaveForms] = signal_dicts_to_numpy_array(
                wave_list, padding=False)
        if getattr(self, TabNames.E_MEDIAN):
            res_dict[CTypes.MedianBeats] = signal_dicts_to_numpy_array(
                median_list, padding=False)
        # finally write to a single file
        np.savez(os.path.join(target, ECG_FILE), **res_dict)
        # include the header
        if getattr(self, TabNames.E_META):
            type(self)._write_header(target, tab1_header)
    # /////////////////////////////////////////////////////////////////////////
    def _write_tfr(self, meta_list:list[dict[str, Any]],
                   wave_list:list[dict[str, np.ndarray]],
                   median_list:list[dict[str, np.ndarray]],
                   target:str,
                   chunk_num:int | None,
                   numeric_meta:bool = True,
                   ) -> None:
        """
        Writes data to a compressed tfrecord.
        
        Parameters
        ----------
        wave_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing medianbeats signals.
        target: `str`
            The target directory.
        chunk_num : `int` or `NoneType`
            Appends the chunk number with a '_' separator before the file
            extension.
        numeric_meta : `bool`, default `True`
            Whether non-numeric data should be dropped from the metadata.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        is_type(numeric_meta, bool)
        # Set the filenames
        _, _, _, ECG_FILE=\
            self._write_file_names(chunk_num=chunk_num)
        # #### write individual files
        res_dict = {}
        if getattr(self, TabNames.E_META):
            tab1  = pd.DataFrame(meta_list)
            if numeric_meta:
                old_cols = set(tab1.columns)
                tab1 = tab1.select_dtypes(include=[np.number])
                new_cols = set(tab1.columns)
                drop_cols = old_cols - new_cols
                if len(drop_cols) > 0:
                    _log.warning(Warn_MSG.DROP_NONE_NUMERIC, drop_cols)
            # get the header
            tab1_header = list(tab1.columns)
            # write the dict
            res_dict[CTypes.MetaData] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=tab1.to_numpy().flatten()
                ))
        if getattr(self, TabNames.E_WAVE):
            # `padding=False`: see _write_numpy for the rationale.
            res_dict[CTypes.WaveForms] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        wave_list, padding=False).flatten()
                ))
        if getattr(self, TabNames.E_MEDIAN):
            res_dict[CTypes.MedianBeats] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        median_list, padding=False).flatten()
                ))
        # finally write to a single file
        with tf.io.TFRecordWriter(os.path.join(target, ECG_FILE)) as writer:
            writer.write(
                tf.train.Example(features=tf.train.Features(feature=res_dict)).\
                SerializeToString()
            )
        # include the header
        if getattr(self, TabNames.E_META):
            type(self)._write_header(target, tab1_header)
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _write_header(target:str, header:list[str]):
        """Write list entries a file with each entry on a new line"""
        with open(os.path.join(target, 'header_metadata.txt'), 'w') as file:
            # Iterate over the list with enumeration starting at 1
            for line_number, head in enumerate(header, start=1):
                # Write each element with its line number to the file
                file.write(f"{line_number}\t{head}\n")
