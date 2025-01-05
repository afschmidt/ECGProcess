'''
A module to process ECG signal data and metadata to tabular form. This also
includes 2D figures - which are strictly speaking tables of pixels.

The module leverages the existing process class instances and based on their
class attributes extracts the requested data.
'''

# NOTE keep track of whether a XML was validated or not - if skip, then
# record this in the failed doc. Probably also add this for the DICCOM and keep
# the column empyt

# NOTE add a function to write tables in bulk, with an option to first
# find the union of headers and add empty columns if a header is missing

# NOTE add functions to write ECG (wave, median) and metdata to HDF5 (perhaps skip, better for random access)
# TFRecord, numpy files, or parquet (perhaps not?). Allowing to subset the metadata. Getting
# an optional header text file mapping the array locations to their headers.
# and allowing to extract any combination of wave, median, or metadata (providing
# a list). https://chatgpt.com/c/676487d1-0dc8-8011-a3cb-2a9b2ee1ea6c

# NOTE allow for a custom function to be applied to the waveforms and/or
# medianbeats, which can optionally select data from the metadata.

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
    TabularNamesTemp as PDNames,
)
from ecgprocess.utils.general import (
    replace_with_tar,
    _update_kwargs,
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
    RawPathList : `list` [`str`]
        A list of file paths.
    
    Methods
    -------
    get_table(update_keys,**kwargs)
        extracts data from multiple dicom files and maps these to
        pandas.DataFrames.
    write_ecg(target_tar, target_path, sep, mode, compression, update_keys,
    **kwargs)
        writes each dicom file to a single sets of files (metadata,
        waveforms, median beats). This is done by appending the extracted
        data from each file the target file set, minimising the memory
        footprint.
    write_pdf(ecgdrawing, target_path, write_failed, kwargs_reader,
    kwargs_drawing, kwargs_savefig)
        writes dicom files to pdfs using the dicom unique id as file name.
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
        verbose : bool, default `False`
            Whether to print warnings.
        
        Attributes
        ----------
        FailedPathList : list [`str`]
            File paths which were either absent or without read permission.
        CuratedPathList : list [`str`]
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
    # NOTE make this into a parameter so that it can be chunked by parent
    # functions: getattr(self, TabNames.CPATH_L)
    def _loop_table(self, path_list:list[str], unique:bool=True,
                    **kwargs:Optional[Any],
                  ) -> tuple[list, list, list]:
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
        self.kwargs = kwargs
        # #### check if __call__ has been run
        # note that we are not directly using this attribute otherwise and
        # instead using the supplied path_list.
        if not hasattr(self, TabNames.CPATH_L):
            raise NotCalledError()
        # #### extract data
        meta_list, wave_list, median_list = [[] for _ in range(3)]
        if hasattr(self, TabNames.KEY_L) == False:
            setattr(self, TabNames.KEY_L, [])
        if hasattr(self, TabNames.NO_DATA_L) == False:
            setattr(self, TabNames.NO_DATA_L, [])
        if hasattr(self, TabNames.INVALID_L) == False:
            setattr(self, TabNames.INVALID_L, [])
        # loop over individual files
        for i, p in enumerate(path_list, start=1):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance and check how errors should be handled
            if not getattr(self, TabNames.SCHEMA) is None:
                try:
                    ecg_inst = self.ecgreader(
                        p, schema=getattr(self, TabNames.SCHEMA),
                        **self.kwargs)
                except XMLValidationError as XML_VAL:
                    getattr(self, TabNames.INVALID_L).append(p)
                    if getattr(self, TabNames.SKIP_INVALID):
                        continue
                    else:
                        raise XML_VAL
            else:
                try:
                    ecg_inst = self.ecgreader(p, **self.kwargs)
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
        meta_list, wave_list, median_list = self._loop_table(
            getattr(self, TabNames.CPATH_L), unique, **kwargs)
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
        
        Attributes
        ----------
        kwargs_pdd : optional
            The keyword arguments supplied to pd.DataFrame.
        
        Returns
        -------
        self : pd.DataFrame
            A long-formatted table with lead, voltage, sampling indicator
            columns grouped by file (including an unique file indicator column)
        '''
        # #### check input and set constants
        is_type(lead_list, list, 'lead_list')
        is_type(signal_type, str, 'signal_type')
        self.kwargs_pdd = kwargs
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
            temp_df = pd.DataFrame(w, **self.kwargs_pdd)
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
    # NOTE add a `chunk` integer to process the file paths in chunks.
    # set this to None to simply process all, the default for get_table (hard-coded)
    # implement this in write_ecg and set this to 1 as default.
    def write_ecg(self, chunk:int=256, target_tar: None | str = None,
                  target_path:str='.', tar_mode:str='w:gz',
                  file_type:Literal['table', 'numpy', 'tensorflow'] = 'table',
                  tab_sep:str='\t', tab_compression:str | None ='gzip',
                  tab_append:bool=True, write_failed:bool=True,
                  kwargs_reader: None | dict[str, Any] = None,
                  kwargs_tab: None | dict[str, Any] = None,
                  kwargs_numpy: None | dict[str, Any] = None,
                  kwargs_tfr: None | dict[str, Any] = None,
                  ) -> Self:
        '''
        Extracts chunks of ECG data, and writes these to a single or multiple
        target files, which can be optionally tar compressed.
        
        Parameters
        ----------
        chunk : `int`, default 256
            The number of files written to a single file. For `file_type` set
            this to 1 with `tab_append=True` minimise the memory fingerprint.
        target_tar : `str`, default `NoneType`
            The `name` of an optional tarfile where the individual files will
            be written to. The target_tar will be concatenated to
            `target_path` and depending on `mode` this directory will be
            tar.gz compressed. Set `target_tar` to `NoneType` to simply add
            the files directly to `target_path`. Note this will overwrite
            any potential directory or files with the identical names.
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
            The file compression passed to pandas.DataFrame.write_csv.
        tab_append : `bool`, default True
            Whether individual chunks should be appended to the `tsv` file.
        write_failed : `bool`, default `True`
            Whether to write a text file to disk containing the failed file
            names.
        kwargs_reader : `dict` [`str`, `any`], default `None`
            Keyword arguments used in the call method of a `BaseReader`
            instance.
        kwargs_tab : `dict` [`str`, `any`], default `None`
            Keyword argument for `pd.DataFrame.to_csv`.
        kwargs_numpy : `dict` [`str`, `any`], default `None`
            Keyword argument for `numpy.savez`.
        kwargs_tfr : `dict` [`str`, `any`], default `None`
            Keyword argument for `tensorflow.io.TFRecordWriter`.
        
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
        '''
        # #### set defaults
        # if kwargs is None assigned an empty dict
        self.kwargs = kwargs_reader or {}
        kwargs_tab = kwargs_tab or {}
        # update kwargs with supplied parameters
        kwargs_tab = _update_kwargs(update_dict=kwargs_tab,
                                    compression=tab_append,
                                    sep=tab_sep,
                                    )
        # expected file_types
        EXP_WRITE=[TabNames.WRITE_TAB, TabNames.WRITE_NUMPY,
                   TabNames.WRITE_TFLOW]
        # #### check input
        is_type(chunk, int)
        is_type(target_tar, (type(None), str))
        is_type(target_path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(tar_mode, str)
        is_type(tab_append, bool)
        is_type(tab_sep, str)
        is_type(tab_compression, (type(None), str))
        is_type(write_failed, bool)
        is_type(file_type, str)
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
        # TODO continue from here using _loop_table and chunk.
        first=True
        key_list, no_data_list = [[] for _ in range(2)]
        # loop over individual dcm files
        for p in getattr(self, PDNames.CPATH_L):
            no_data_list, key_list, ecg_inst = self._write_internal(
                path=p, no_data_list=no_data_list, key_list=key_list,
                **self.kwargs,
                )
            if isinstance(ecg_inst, str):
                continue
            # #### extract data from ecg_inst
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                info=getattr(ecg_inst, PDNames.RESULTS_DICT)
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                wave=getattr(ecg_inst, PDNames.LEAD_VOLTAGES)
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                median=getattr(ecg_inst, PDNames.LEAD_VOLTAGES2)
            # assign key to self for use in `_get_long_table`
            setattr(self, PDNames.KEY_L, [key_list[-1]])
            # #### write to disk
            if first==True:
                first = False
                # metadata
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                    pd.DataFrame([info], index=[key_list[-1]]).to_csv(
                        os.path.join(target, PDNames.INFO_FILE), sep=sep,
                        header=True, compression=compression,
                        **kwargs_write,)
                # waveforms
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                    self._get_long_table(
                        [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                        update_keys=update_keys,
                        purge_header=True,
                    ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=True, compression=compression,
                        **kwargs_write,)
                # median beats
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                    self._get_long_table(
                        [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                        update_keys=update_keys,
                        purge_header=True,
                    ).to_csv(
                        os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                        header=True, compression=compression,
                        **kwargs_write,)
            else:
                # appending using mode = 'a'
                # metadata
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                    pd.DataFrame([info], index=[key_list[-1]]).to_csv(
                        os.path.join(target, PDNames.INFO_FILE), sep=sep,
                        header=False, mode='a', compression=compression,
                        **kwargs_write,)
                # waveforms
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                    self._get_long_table(
                        [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                        update_keys=update_keys,
                        purge_header=False,
                    ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=False, mode='a', compression=compression,
                        **kwargs_write,)
                # median beats
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                    self._get_long_table(
                        [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                        update_keys=update_keys,
                        purge_header=False,
                    ).to_csv(
                        os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                        header=False, mode='a', compression=compression,
                        **kwargs_write,)
            # delete key
            delattr(self, PDNames.KEY_L)
        # #### write failed files, note not compressing these
        DELIM = '\t'
        if write_failed == True:
            # adding the reason for failing
            total_failures = [
                (p, PDNames.SKIP_PERMISSIONS) for p in\
                getattr(self, PDNames.FPATH_L) ] + [
                (p, PDNames.SKIP_DATA) for p in\
                    getattr(self, PDNames.FAILED_DATA_L)]
            # writing to text file
            with open(os.path.join(target, PDNames.FAILED_FILE), 'w') as file:
                for p, cause in total_failures:
                    file.write(p + DELIM + cause + "\n")
        # #### if needed replace directory by tar.gz version
        if target_tar is not None:
            # create the final target path
            target_final = os.path.join(target_path, target_tar)
            replace_with_tar(target, target_final, mode=mode)
            setattr(self, TabNames.WRITE_ECG_PATH, target_final)
        # #### return
        return self
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
    # # /////////////////////////////////////////////////////////////////////////
    def _write_internal(self, path:str, no_data_list:list[str],
                        key_list:list[str],
                        **kwargs,
                        ) -> tuple[list, list, BaseReader|str]:
        '''
        An internal function to read ECG dicom data, check whether there these
        data may have been extracted before (compared to key_list) and record
        whether some files did not contain waveform_array attributes.
        
        Parameters
        ----------
        no_data_list : list [`str`]
            A list of file names without an waveform_array attribute.
        key_list : list [`str`]
            A list of dicom UIDs which were processed before.
        
        Returns
        -------
        `tuple`
            A tuple with `no_data_list`, `key_list`, and an BaseReader
            instance.
        
        Raises
        ------
        AttributeError
            raised if waveform_array or SOPinstanceUID attributes are absent.
        IndexError
            raised if a dicom with the same SOPinstanceUID is processed
        '''
        
        if self.verbose == True:
            print(STDOUT_MSG.PROCESSING_PATH.format(path), file=sys.stdout)
        # get instance
        try:
            ecg_inst = self.ecgdicomreader(path, **kwargs)
        except AttributeError as AE:
            if self.skip_missing == PDNames.SKIP_DATA:
                no_data_list.append(path)
                # moving to the next path - cannot use continue here
                return no_data_list, key_list, 'continue'
            else:
                raise AE
        # extract unique identifier and check if it has been used before
        if hasattr(ecg_inst, PDNames.SOP_UID) == False:
            raise AttributeError(Error_MSG.MISSING_ATTR.format(
                PDNames.SOP_UID, 'ecg_inst'))
        key = str(getattr(ecg_inst, PDNames.SOP_UID))
        if key in key_list:
            raise IndexError('{0}:{1} was already extracted before. Please '
                             'ensure the supplied files are unique.'.\
                             format(PDNames.SOP_UID, key))
        else:
            key_list.append(key)
        # extract the remaining
        setattr(self, PDNames.FAILED_DATA_L, no_data_list)
        # return
        return no_data_list, key_list, ecg_inst



