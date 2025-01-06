'''
A module to process ECG signal data and metadata to tabular form. This also
includes 2D figures - which are strictly speaking tables of pixels.

The module leverages the existing process class instances and based on their
class attributes extracts the requested data.
'''

# NOTE allow for a custom function to be applied to the waveforms and/or
# medianbeats, which can optionally select data from the metadata.
# consider allowing for functions to be passed to metadata as well.

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import os
# import re
import sys
import uuid
import pathlib
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf
# import matplotlib.pylab as plt
from typing import (
    Self, Optional, Any, Literal,
)
from ecgprocess.errors import (
    XMLValidationError,
    NotCalledError,
    is_type,
    Error_MSG,
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
    # assign_empty_default,
)
# from ecgprocess.plot_ecgs import (
#     ECGDrawing,
# )
from ecgprocess.utils.reader_tools import(
    BaseReader,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CMeta = Core.MetaData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class ECGTable(object):
    '''
    Takes an `BaseReader` instance and loops over a list of file paths
    containing ECG data and extract relevant information  using a `Processing`
    instance and a `Mapping` instance. The extract information can be mapped to
    a Pandas.DataFrame or saved to disk.
    
    Parameters
    ----------
    ecgreader : `BaseReader`
        An instance of the BaseReader data class.
    path_list : `list` [`str`]
        A list of paths to one or more files containing ECG data.
    extract_meta : `bool`, `default` True
        Whether to extract the metadata data.
    extract_wave : `bool`, `default` True
        Whether to extract the raw waveforms.
    extract_median : `bool`, `default` True
        Whether to extract the median beats.
    schema : `str` or `NoneType`, default `NoneType`
        The path to an optional XSD schema to validate an XML file. Set to
        None to ignore.
    
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
    '''
    
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, ecgreader:BaseReader, path_list:list[str],
                 extract_meta:bool=True, extract_wave:bool=True,
                 extract_median:bool=True, schema:str | None = None,
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
        # #### assign to self
        self.ecgreader = ecgreader
        setattr(self, TabNames.E_META, extract_meta)
        setattr(self, TabNames.E_WAVE, extract_wave)
        setattr(self, TabNames.E_MEDIAN, extract_median)
        setattr(self, TabNames.RPATH_L, path_list)
        setattr(self, TabNames.SCHEMA, schema)
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
                f"augment_leads={getattr(self, TabNames.RPATH_L)})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, ignore_permission:bool = True,
                 ignore_data:bool = False, ignore_invalid:bool = False,
                 verbose:bool=False,
                 ) -> Self:
        """
        Will take a BaseReader instance and loops over a list of file paths
        and and confirm the files exist and have appropriate read permission.
        
        Parameters
        ----------
        ignore_permission : `bool`, default True
            Skips file permission errors. The failed file names will be recorded
            for review.
        ignore_data : `bool`, default False
            Whether missing MetaData, WaveForm, or MedianBeat data objects
            should be skipped. The file names for these failures will be
            recorded.
        ignore_invalid : `bool`, default False
            Whether XML files who failed to an XSD validation schema should
            be skipped.
        verbose : `bool`, default `False`
            Whether to print warnings.
        
        Attributes
        ----------
        failed_path_list : `list` [`str`]
            File paths which were either absent or without read permission.
        curated_path_list : `list` [`str`]
            File paths which are readable.
        
        Returns
        -------
        self : `ECGTable` instance
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
        # #### do we want to print empty_list
        if self.verbose == True:
            if len(getattr(self, TabNames.FPATH_L))>0:
                warnings.warn(
                    'The following files could not be accessed or found: {}.'.\
                    format(getattr(self, TabNames.FPATH_L))
                )
        # #### Return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _loop_table(self, path_list:list[str], unique:bool=True,
                    **kwargs:Optional[Any],
                  ) -> tuple[list[dict[str, Any]], list[dict[str, np.ndarray]],
                             list[dict[str, np.ndarray]]]:
        """
        Will loop of the supplied files and extract ECG data.
        
        Parameters
        ----------
        path_list : `list` [`str`]
            A list of paths to one or more files containing ECG data.
        unique : `bool`, default `True`
            ensures the `UID` metadata items are unique between files. Please
            ensure the UID metadata key value pair is appropriately set in
            the config file. If set to false an file-specific integer key will
            be assigned instead.
        **kwargs: optional
            Keyword arguments used in the call method of a `BaseReader`
            instance
        
        Attributes
        ----------
        key_list: list [`str`]
            A list of unique identifiers.
        no_data_list : `list` [`str`]
            A list of files without data.
        invalid_list : `list` [`str`]
            A list of files which failed to validate.
        _id_start_number : `int`
            Records the integer start number used as place holder UID when
            unique = `False`. This attributes esnures UIDs are unique across
            multiple calls to the method.
        
        Returns
        -------
        tuple of list
            the metadata, waveform signals, and medianbeats signals.
        
        Notes
        -----
        To keep track of multiple ECG files the function will try to use the
        the privileged variable UID. If this is not found in the supplied
        `MetaData` it will instead assign an interger value starting from 1 for
        each file processed.
        """
        # #### check input
        # NOTE path_list has already been test - not doing this again because
        # it is a private method.
        is_type(unique, bool)
        kwargs_reader = kwargs
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
        # loop over individual files
        if hasattr(self, TabNames.ID_START) == False:
            setattr(self, TabNames.ID_START, 1)
        for i, p in enumerate(path_list,
                              start=getattr(self, TabNames.ID_START)):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance and check how errors should be handled
            if not getattr(self, TabNames.SCHEMA) is None:
                try:
                    ecg_inst = self.ecgreader(
                        p, schema=getattr(self, TabNames.SCHEMA),
                        **kwargs_reader)
                except XMLValidationError as XML_VAL:
                    getattr(self, TabNames.INVALID_L).append(p)
                    if getattr(self, TabNames.SKIP_INVALID):
                        continue
                    else:
                        raise XML_VAL
            else:
                try:
                    ecg_inst = self.ecgreader(p, **kwargs_reader)
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
                    if hasattr(ecg_inst[CTypes.MetaData], CMeta.UID) == False:
                        raise AttributeError(Error_MSG.MISSING_ATTR.format(
                            'CMeta.UID', 'ecg_inst'))
                    else:
                        key = str(getattr(ecg_inst[CTypes.MetaData], CMeta.UID))
            else:
                try:
                    key = str(getattr(ecg_inst[CTypes.MetaData], CMeta.UID))
                except AttributeError or KeyError:
                    key = i
            # confirm the key is unique
            if key in getattr(self, TabNames.KEY_L):
                raise IndexError('The file seems to have been extracted already'
                                 '.Please ensure the supplied files are unique.'
                                 f'This is the current file ID {key} and these'
                                 'are the IDs of the processed files '
                                 f'{getattr(self, TabNames.KEY_L)}.'
                                 )
            else:
                getattr(self, TabNames.KEY_L).append(key)
            # Append metadata.
            no_meta = False
            if getattr(self, TabNames.E_META):
                try:
                    meta_list.append(getattr(ecg_inst, CTypes.MetaData))
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        no_meta=True
                    else:
                        raise AE
            # Append waveform signals.
            no_wave = False
            if getattr(self, TabNames.E_WAVE):
                try:
                    wave_list.append(getattr(ecg_inst, CTypes.WaveForms))
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        no_wave=True
                    else:
                        raise AE
            # Append median beat signals.
            no_median = False
            if getattr(self, TabNames.E_MEDIAN):
                try:
                    median_list.append(getattr(ecg_inst, CTypes.MedianBeats))
                except AttributeError as AE:
                    if getattr(self, TabNames.SKIP_DATA):
                        no_median=True
                    else:
                        raise AE
            # if there is no data at all record this
            if no_meta and no_wave and no_median:
                getattr(self,TabNames.NO_DATA_L).append(p)
        # record update the last ID_START
        setattr(self, TabNames.ID_START, i+1)
        # return the list
        return meta_list, wave_list, median_list
    # /////////////////////////////////////////////////////////////////////////
    def get_table(self, unique:bool=True, **kwargs:Optional[Any],
                  ) -> Self:
        """
        Presents ECG data as pandas.DataFrames.
        
        Parameters
        ----------
        unique : `bool`, default `True`
            ensures the `UID` metadata items are unique between files. Please
            ensure the UID metadata key value pair is appropriately set in
            the config file. If set to false an file-specific integer key will
            be assigned instead.
        **kwargs: optional
            Keyword arguments used in the call method of a `BaseReader`
            instance
        
        Attributes
        ----------
        MetaDataTable: pandas.DataFrame
            A table of the metadata.
        WaveFormsTable: pandas.DataFrame
            A long-format table with waveforms signals.
        MedianBeatsTable: pandas.DataFrame
            A long-format table with the median beat signals.
        
        Returns
        -------
        self : `ECGTable` instance
            Returns the class instance with updated attributes.
        
        Notes
        -----
        To keep track of multiple ECG files the function will try to use the
        the privileged variable UID. If this is not found in the supplied
        `MetaData` it will instead simply assign a interger starting from 1 for
        each file processed.
        """
        # #### run loop
        try:
            meta_list, wave_list, median_list = self._loop_table(
                getattr(self, TabNames.CPATH_L), unique, **kwargs)
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
        lead_list : list [`dict`]
            A list of dictionaries with the lead mapped to the keys and the
            voltage mapped to the values.
        signal_type : str,
            Adds a column `Waveform type` containing this string as a constant.
        purge_header : bool, default True
            Set to `False` to make sure the file header persists between calls.
            This is used to ensure the headers are the same between files.
        **kwargs : optional
            keyword arguments passed to pd.DataFrame.
        
        Returns
        -------
        self : pd.DataFrame
            A long-formatted table with lead, voltage, sampling indicator
            columns grouped by file (including an unique file indicator column)
        '''
        # #### check input and set constants
        is_type(lead_list, list, 'lead_list')
        is_type(signal_type, str, 'signal_type')
        kwargs_pdd = kwargs
        PREV = 'previous'
        SAMPLING_SEQ = 'Sampling sequence'
        # do we need to purge the header information
        # otherwise this persists throughout calls
        if purge_header == True:
            setattr(self, PREV, None)
        else:
            if not hasattr(self, PREV):
                setattr(self, PREV, None)
        # #### initiate table and map lists
        table = pd.DataFrame()
        # NOTE w contains a dictionary with k: lead names and v: signals.
        for w, k in zip(lead_list, getattr(self, TabNames.KEY_L), strict=True):
            # confirm the dictionary keys/lead names are identical
            current_keys = list(w.keys())
            if getattr(self, PREV) is not None:
                if current_keys != getattr(self, PREV):
                    raise KeyError('The dictionaries contain distinct keys. '
                                   'The last set of valid keys was {}, '
                                   'compared to {}.'.\
                                   format(getattr(self, PREV), current_keys))
            # if the same map to dataframe
            temp_df = pd.DataFrame(w, **kwargs_pdd)
            temp_df[CMeta.UID] = k
            table = pd.concat([table, temp_df], ignore_index=True)
            # clean
            setattr(self, PREV, current_keys)
            del current_keys
            del temp_df
        # #### formatting to long
        if table.empty == False:
            table[SAMPLING_SEQ] = table.groupby(
                CMeta.UID).cumcount()
            long_table = pd.melt(table, id_vars=\
                                 [CMeta.UID, SAMPLING_SEQ],
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
    def write_ecg(self, chunk:int=256, target_tar: None | str = None,
                  target_path:str='.', tar_mode:str='w:gz',
                  file_type:Literal['table', 'numpy', 'tensorflow'] = 'table',
                  tab_sep:str='\t', tab_compression:str | None ='gzip',
                  tab_append:bool=True, unique:bool=True,
                  write_failed:bool=True, write_chunk_record:bool = False,
                  kwargs_reader: None | dict[str, Any] = None,
                  kwargs_tab: None | dict[str, Any] = None,
                  ) -> Self:
        '''
        Extracts chunks of ECG data, and writes these to a single or multiple
        target files, which can be optionally tar compressed.
        
        Parameters
        ----------
        chunk : `int`, default 256
            The number of files written to a single file. For `file_type` set
            this to 1 with `tab_append=True` minimise the memory fingerprint.
            Set to `NoneType` to combine all the ECG data into a single target
            file.
        target_tar : `str`, default `NoneType`
            The `name` of an optional tarfile where the individual files will
            be written to. The target_tar will be concatenated to
            `target_path`. Depending on the `mode` this directory will be
            tar.gz compressed for example.  Set `target_tar` to `NoneType` to
            simply add the files directly to `target_path`.
            Note this will overwrite any potential directory or file with the
            provide name.
        target_path : `str`, default '.'
            The full path where the files should be written to. if provided
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
            the config file. If set to false an file-specific integer key will
            be assigned instead.
        write_failed : `bool`, default `True`
            Whether to write a text file to disk containing the failed file
            names.
        write_chunk_record : `bool`, default `True`
            Whether to include a record matching the chunk indicator to the
            files included.
        kwargs_reader : `dict` [`str`, `any`], default `None`
            Keyword arguments used in the call method of a `BaseReader`
            instance.
        kwargs_tab : `dict` [`str`, `any`], default `None`
            Keyword argument for `pd.DataFrame.to_csv`.
        
        Attributes
        ----------
        target_path : str
            The directory or tar file path were the files are written to.
        NoDataList : `list` [`str`]
            A list of files without any data.
        
        Returns
        -------
        self : `ECGTable` instance
            Returns the class instance with updated attributes.
        
        Raises
        ------
        NotADirectoryError or PermissionError
            If the target directory does not exist or is not writable.
        
        Notes
        -----
        While file_type='table' can store any kind of information, numpy and
        tfrecord are best used to store numerical/float data. The current
        behaviour does not check feature types and expects the user to
        supply a reader instance which extract the appropriate type of data,
        i.e., excluding string data when not writing to tables.
        '''
        # #### set defaults
        # if kwargs is None assigned an empty dict
        kwargs_reader = kwargs_reader or {}
        kwargs_tab = kwargs_tab or {}
        # expected file_types
        EXP_WRITE=[TabNames.WRITE_TAB, TabNames.WRITE_NUMPY,
                   TabNames.WRITE_TFLOW]
        # #### check input
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
        # update kwargs with supplied parameters
        self.kwargs_tab = _update_kwargs(update_dict=kwargs_tab,
                                    compression=tab_compression,
                                    sep=tab_sep,
                                    )
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
            path_list = getattr(self, TabNames.CPATH_L)
        # NOTE First is only relevant when writing to a file using append.
        first=True
        # #### loop over the path_list
        try:
            for n, p in enumerate(path_list, start=1):
                # record the chunk_number and the files included
                chunk_record[n] = ', '.join(p)
                # extract data
                meta_list, wave_list, median_list = self._loop_table(
                    p, unique, **kwargs_reader)
                # write based on the supplied file type
                if getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TAB:
                    if tab_append == False:
                        self._write_tab(
                            meta_list, wave_list, median_list, target,
                            chunk_num=n if chunk is not None else None,
                            header=True,
                                        )
                    # Write to a single file
                    elif first==True:
                        first = False
                        # write first file
                        self._write_tab(meta_list, wave_list, median_list,
                                        target, chunk_num=None,
                                        header=True,
                                        )
                    else:
                        # append
                        self._write_tab(meta_list, wave_list, median_list,
                                        target, chunk_num=None,
                                        header=False, mode='a',
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
        # #### write chunk record
        if write_chunk_record:
            chunk_tab = pd.DataFrame.from_dict(chunk_record, orient='index',
                                   columns=['Files'])
            chunk_tab.index.name='Chunk number'
            chunk_tab.to_csv(
                os.path.join(target, 'ChunkRecord.tsv'), sep='\t', header=True,
                index=True)
        # #### write failed files, note not compressing these
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
        # #### return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _write_file_names(self, chunk_num:int|None = None,
                          ) -> tuple[str, str, str, str]:
        """
        Creates the filenames with relevant extensions, optionally accounting
        for chunks.
        
        Parameters
        ----------
        chunk_num : `int` or `NoneType`, default `NoneType`
            Appends the chunk number with a '_' seperator before the file
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
            if self.kwargs_tab['compression'] == 'gz':
                EXT = EXT + '.gz'
            if self.kwargs_tab['compression'] == 'bz2':
                EXT = EXT + '.bz2'
            if self.kwargs_tab['compression'] == 'zip':
                EXT = EXT + '.zip'
            if self.kwargs_tab['compression'] == 'xz':
                EXT = EXT + '.xz'
            if self.kwargs_tab['compression'] == 'zst':
                EXT = EXT + '.zst'
        elif getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_NUMPY:
            EXT = '.npz'
        elif getattr(self, TabNames.WRITE_TYPE) == TabNames.WRITE_TFLOW:
            EXT = '.tfrecord'
        # Are we writing in chunks?
        if not chunk_num is None:
            SEP = '_'
            CHUNK = str(chunk_num)
        # the finel file names
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
        Writes data to a flat table.
        
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
            Appends the chunk number with a '_' seperator before the file
            extension.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        # Set the filenames
        META_FILE, WAVE_FILE, MEDIAN_FILE, _=\
            self._write_file_names(chunk_num=chunk_num)
        # #### write individual files
        kwargs_tab_combi = {**self.kwargs_tab, **kwargs}
        if getattr(self, TabNames.E_META):
            pd.DataFrame([meta_list]).to_csv(
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
    # NOTE npz is not ideal to store non-numerical data, might want to filter
    # the pandas tables to remove these - as an optional parameter?
    # printing warnings returning the removed columns??
    def _write_numpy(self, meta_list:list[dict[str, Any]],
                   wave_list:list[dict[str, np.ndarray]],
                   median_list:list[dict[str, np.ndarray]],
                   target:str,
                   chunk_num:int | None,
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
            Appends the chunk number with a '_' seperator before the file
            extension.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        # Set the filenames
        _, _, _, ECG_FILE=\
            self._write_file_names(chunk_num=chunk_num)
        # #### write individual files
        res_dict = {}
        if getattr(self, TabNames.E_META):
            res_dict[CTypes.MetaData] = pd.DataFrame([meta_list]).to_numpy()
        if getattr(self, TabNames.E_WAVE):
            res_dict[CTypes.WaveForms] = pd.DataFrame([wave_list]).to_numpy()
        if getattr(self, TabNames.E_MEDIAN):
            res_dict[CTypes.MedianBeats] =\
                pd.DataFrame([median_list]).to_numpy()
        # finally write to a single file
        np.savez(os.path.join(target, ECG_FILE), **res_dict)
    # /////////////////////////////////////////////////////////////////////////
    # NOTE tfrecords cannot handle non-numerical data, might want to filter
    # the pandas tables to remove these - as an optional parameter?
    def _write_tfr(self, meta_list:list[dict[str, Any]],
                   wave_list:list[dict[str, np.ndarray]],
                   median_list:list[dict[str, np.ndarray]],
                   target:str,
                   chunk_num:int | None,
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
            Appends the chunk number with a '_' seperator before the file
            extension.
        
        Notes
        -----
        This function does not return anything.
        """
        # #### check input
        is_type(chunk_num, (int, type(None)))
        # Set the filenames
        _, _, _, ECG_FILE=\
            self._write_file_names(chunk_num=chunk_num)
        # #### write individual files
        res_dict = {}
        if getattr(self, TabNames.E_META):
            res_dict[CTypes.MetaData] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=pd.DataFrame([meta_list]).to_numpy().flatten()
                ))
        if getattr(self, TabNames.E_WAVE):
            res_dict[CTypes.WaveForms] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=pd.DataFrame([wave_list]).to_numpy().flatten()
                ))
        if getattr(self, TabNames.E_MEDIAN):
            res_dict[CTypes.MedianBeats] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=pd.DataFrame([median_list]).to_numpy().flatten()
                ))
        # finally write to a single file
        with tf.io.TFRecordWriter(os.path.join(target, ECG_FILE)) as writer:
            writer.write(
                tf.train.Example(feature=tf.train.Features(feature=res_dict)).\
                SerializeToString()
            )
    # # /////////////////////////////////////////////////////////////////////////
    # def write_pdf(self, ecgdrawing:ECGDrawing,
    #               target_path:str='.', write_failed:bool=True,
    #               kwargs_reader:dict[Any,Any] | None=None,
    #               kwargs_drawing:dict[Any,Any] | None=None,
    #               kwargs_savefig:dict[Any,Any] | None=None,
    #               ) -> Self:
    #     '''
    #     Extracts dicom files, and write these one by one to a pdf files
    #     using a supplied `ECGDrawing` instance.
        
    #     Parameters
    #     ----------
    #     ecgdrawing : ECGDrawing
    #         An instance of the ECGDrawing data class.
    #     target_path : `str`, default '.'
    #         The full path where the pdfs should be written to.
    #     write_failed : `bool`, default `True`
    #         Whether to write a text file to disk containing the failed file
    #         names.
    #     kwargs_*: dict [`any`, `any`], default `NoneType`
    #         dictionaries with keyword arguments for the `plt.savefig`,
    #         ECGDrawing, or BaseReader instances.
        
    #     Attributes
    #     ----------
    #     target_path : `str`
    #         The directory or tar file path were the files are written to.
    #     NoDataList : `list` [`str`]
    #         A list of dicom files without a waveform_array.
        
    #     Returns
    #     -------
    #     self : `ECGDICOMTable` instance
    #         Returns the class instance with updated attributes.
        
    #     Notes
    #     -----
    #     The dicom UID instance will be used as file name for the pdfs.
        
    #     Raises
    #     ------
    #     NotADirectoryError or PermissionError
    #         If the target directory does not exist or is not writable.
    #     '''
    #     # #### check input and set constants
    #     is_type(kwargs_reader, (type(None), dict))
    #     is_type(kwargs_drawing, (type(None), dict))
    #     is_type(kwargs_savefig, (type(None), dict))
    #     is_type(ecgdrawing, ECGDrawing)
    #     is_type(target_path, (pathlib.PosixPath, pathlib.WindowsPath, str))
    #     is_type(write_failed, bool)
    #     # check readability
    #     _check_presence(target_path)
    #     _check_readable(target_path)
    #     # map None to dict
    #     kwargs_savefig, kwargs_reader, kwargs_drawing= assign_empty_default(
    #             [kwargs_savefig, kwargs_reader, kwargs_drawing], dict)
    #     # map info type to type of plot
    #     if getattr(self, PDNames.INFO_TYPE) == PDNames.INFO_TYPE_MET:
    #         raise AttributeError('`info` should be {0} or {1}.'.format(
    #             PDNames.INFO_TYPE_MED, PDNames.INFO_TYPE_RTM))
    #     elif getattr(self, PDNames.INFO_TYPE) == PDNames.INFO_TYPE_ALL:
    #         signal_type = PDNames.WAVETYPE_RHYTHM
    #     else:
    #         signal_type = getattr(self, PDNames.INFO_TYPE)
    #     # #### create target path
    #     if target_path == '.':
    #         target_path = os.getcwd()
    #     # assign to self
    #     target = target_path
    #     setattr(self, PDNames.WRITE_ECG_PATH, target)
    #     # #### check if __call__ has been run
    #     if not hasattr(self, PDNames.CPATH_L):
    #         raise NotCalledError()
    #     # #### extract dicom data
    #     key_list, no_data_list = [[] for _ in range(2)]
    #     # loop over individual dcm files
    #     for p in getattr(self, PDNames.CPATH_L):
    #         # NOTE _write_internal has been superseded by _loop_table
    #         no_data_list, key_list, ecg_inst = self._write_internal(
    #             path=p, no_data_list=no_data_list, key_list=key_list,
    #             **kwargs_reader,
    #             )
    #         if isinstance(ecg_inst, str):
    #             continue
    #         # #### updated leads
    #         # if update_keys is not None:
    #         #     w = {update_keys.get(k, k): v for k, v in w.items()}
    #         # ##### draw and write figure
    #         artist = ecgdrawing(ecgreader=ecg_inst, wave_type=signal_type,
    #                             **kwargs_drawing)
    #         filename_pdf = re.sub(r"[ ,\-\(\)\{\}]", '_', key_list[-1]) + '.pdf'
    #         plt.savefig(fname=os.path.join(target, filename_pdf), **kwargs_savefig)
    #         plt.close(artist.fig)
    #     # #### write failed files, note not compressing these
    #     DELIM = '\t'
    #     if write_failed == True:
    #         # adding the reason for failing
    #         total_failures = [
    #             (p, PDNames.SKIP_PERMISSIONS) for p in\
    #             getattr(self, PDNames.FPATH_L) ] + [
    #             (p, PDNames.SKIP_DATA) for p in\
    #                 getattr(self, PDNames.FAILED_DATA_L)]
    #         # writing to text file
    #         with open(os.path.join(target, PDNames.FAILED_FILE), 'w') as file:
    #             for p, cause in total_failures:
    #                 file.write(p + DELIM + cause + "\n")
    #     # #### return
    #     return self
