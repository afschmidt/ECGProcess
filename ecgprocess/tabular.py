'''
A module to process ECG signal data and metadata to tabular form. This also
includes 2D figures - which are strictly speaking tables of pixels.
'''

# NOTE implement the following
# skip_emtpy should be renamed to empty_attribute which should be a literal with
# options `Error`, `Skip`, `Skip-all`, where the Error should just raise errors
# and `Skip` should skip empty attributes, while `Skip-all` Should also
# skip empy wavform files - if you only want metadata.

# NOTE should also rename skip_missing to file_errors usign the same Literals
# but replacing None by Error.


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import os
import re
import sys
import uuid
import pathlib
import warnings
import numpy as np
import pandas as pd
import matplotlib.pylab as plt
from typing import (
    List, Type, Union, Tuple, Self, Dict, Optional, Any, Literal,
)
from ecgprocess.errors import (
    NotCalledError,
    is_type,
    Error_MSG,
    STDOUT_MSG,
    _check_readable,
    _check_presence,
)
from ecgprocess.constants import (
    TabularNames as PDNames,
)
from ecgprocess.utils.general import (
    replace_with_tar,
    assign_empty_default,
)
from ecgprocess.plot_ecgs import (
    ECGDrawing,
)
from ecgprocess.utils.reader_tools import(
    BaseReader,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class ECGTable(object):
    '''
    Takes an `BaseReader` instance and loops over a list of dicom paths
    and maps these to which can be used in analyses or saved to disk.
    
    Parameters
    ----------
    ecgdicomreader : BaseReader
        An instance of the BaseReader data class.
    path_list : list [`str`]
        A list of paths to one or more .dcm files.
    info_type : {`all`, `rhythm`, `median`, `meta`}
        Which information should be extracted.
    
    Attributes
    ----------
    RawPathList : list [`str`]
        A list of dcm file paths.
    info_type : `str`, default `all`
        The type of information one wants to extract from the dicom files.
    
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
    def __init__(self, ecgdicomreader:BaseReader, path_list:List[str],
                 info_type:Literal['all', 'rhythm', 'median', 'meta'] = 'all'
                 ) -> None:
        """
        Initialises a new instance of `ECGDICOMTable`.
        """
        EXP_INFO=[PDNames.INFO_TYPE_ALL, PDNames.INFO_TYPE_RTM,
                  PDNames.INFO_TYPE_MED, PDNames.INFO_TYPE_MET,
                  ]
        self.INFO_MET = [PDNames.INFO_TYPE_ALL, PDNames.INFO_TYPE_MET]
        self.INFO_MED = [PDNames.INFO_TYPE_ALL, PDNames.INFO_TYPE_MED]
        self.INFO_RTM = [PDNames.INFO_TYPE_ALL, PDNames.INFO_TYPE_RTM]
        # #### check input
        is_type(ecgdicomreader, BaseReader, 'ecgdicomreader')
        is_type(path_list, list, 'path_list')
        if not info_type in EXP_INFO:
            raise ValueError(f'`info_type` is restricted to `{EXP_INFO}`.')
        self.ecgdicomreader = ecgdicomreader
        setattr(self, PDNames.INFO_TYPE, info_type)
        setattr(self, PDNames.RPATH_L, path_list)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME} instance with "
                f"ecgdicomreader={self.ecgdicomreader}, "
                f"path_list={getattr(self, PDNames.RPATH_L)}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME}(ecgdicomreader={self.ecgdicomreader}, "
                f"augment_leads={getattr(self, PDNames.RPATH_L)})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(
        self, skip_missing:Literal['Permissions', 'Data', 'None']='Permissions',
        verbose:bool=False,
    ) -> Self:
        """
        Will take a BaseReader instance and loops over a list of dcm file paths
        and and confirm the files exist and have appropriate read permission
        
        Parameters
        ----------
        skip_missing : {'Permissions', 'Data', 'None'}, default `Permissions`
            Whether files with a `PermissionError` or `AttributeError` should
            be skipped, or whether all errors should be raised.
            A PermissionError implies either the file is absent or it cannot
            be read. An AttributeError indicates the waveform_array
            attribute is absent from the pydicom instance.
            `Permissions` will only skip PermissionErrors, while `Data` will
            skip both PermssionErrors and AttributeErrors (due to a missing
            waveform_array), `None` will not skip errors.
        verbose : bool, default `False`
            Prints missing files if skip_missing is set to `True`.
        
        Attributes
        ----------
        FailedPathList : list [`str`]
            File paths which were either absent or without read permission.
        CuratedPathList : list [`str`]
            File paths which are readable.
        
        Returns
        -------
        self : `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        is_type(skip_missing, str)
        is_type(verbose, bool)
        self.skip_missing = skip_missing
        self.verbose = verbose
        SKIP_MISSING = [PDNames.SKIP_PERMISSIONS,
                        PDNames.SKIP_DATA,
                        PDNames.SKIP_NONE,
                        ]
        if not skip_missing in SKIP_MISSING:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('skip_missing', ', '.join(SKIP_MISSING)))
        # #### loop over path
        empty_list = []
        curated_list = []
        # #### loop over individual dcm files and assign to self
        for p in getattr(self, PDNames.RPATH_L):
            try:
                # add p and remove if skipp_missing == True
                curated_list.append(p)
                _check_readable(p)
            except PermissionError as PE:
                empty_list.append(p)
                # try next
                if self.skip_missing != PDNames.SKIP_NONE:
                    curated_list.pop()
                    pass
                else:
                    raise PE
        setattr(self, PDNames.FPATH_L, empty_list)
        setattr(self, PDNames.CPATH_L, curated_list)
        # #### do we want to print empty_list
        if self.verbose == True:
            if len(getattr(self, PDNames.FPATH_L))>0:
                warnings.warn(
                    'The following files could not be accessed or found: {}.'.\
                    format(getattr(self, PDNames.FPATH_L))
                )
        # #### Return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def get_table(self, update_keys:Optional[Dict[str, str]]=None,
                  **kwargs:Optional[Any],
                  ) -> Self:
        """
        Will extracted dicom data to tables.
        
        Parameters
        ----------
        update_keys: dict [`str`, `str`], default `NoneType`
            A dictionary to remap lead names: [`old`, `new`]
        **kwargs: optional
            Keyword arguments used in the call method of a `BaseReader`
            instance
        
        Attributes
        ----------
        IndexList: list [`str`]
            A list of unique identifiers.
        GeneralInfoTable: pandas.DataFrame
            A table of the dicom metadata.
        WaveFormsTable: pandas.DataFrame
            A  long-format table with waveforms.
        MedianWaveTable: pandas.DataFrame
            A long-format table with the median beat waveforms.
        NoDataList : `list` [`str`]
            A list of dicom files without a waveform_array.
        
        Returns
        -------
        self : `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        self.kwargs = kwargs
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.CPATH_L):
            raise NotCalledError()
        # #### extract dicom data
        no_data_list, key_list, info_list, wave_list, median_list =\
            [[] for _ in range(5)]
        # loop over individual dcm files
        for p in getattr(self, PDNames.CPATH_L):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance
            try:
                ecg_inst = self.ecgdicomreader(p, **self.kwargs)
            except AttributeError as AE:
                if self.skip_missing == PDNames.SKIP_DATA:
                    no_data_list.append(p)
                    # moving to the next path
                    continue
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
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                info_list.append(getattr(ecg_inst, PDNames.RESULTS_DICT))
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                wave_list.append(getattr(ecg_inst, PDNames.LEAD_VOLTAGES))
            if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                median_list.append(getattr(ecg_inst, PDNames.LEAD_VOLTAGES2))
        # #### make tables
        setattr(self, PDNames.FAILED_DATA_L, no_data_list)
        setattr(self, PDNames.KEY_L, key_list)
        # general info
        if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
            setattr(self, PDNames.INFO_T, pd.DataFrame(
                info_list, index=getattr(self, PDNames.KEY_L)
            ))
        # wave forms, and median beats
        if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
            setattr(self, PDNames.WAVE_T, self._get_long_table(
                wave_list, wave_type=PDNames.WAVETYPE_RHYTHM,
                update_keys=update_keys,
                purge_header=True,
            ))
        if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
            setattr(self, PDNames.MEDIAN_T, self._get_long_table(
                median_list, wave_type=PDNames.WAVETYPE_MEDIAN,
                update_keys=update_keys,
                purge_header=True,
            ))
        # #### Return
        setattr(self, PDNames.TABLE_CALLED, 'True')
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _get_long_table(self, lead_list:List[Dict[str, np.ndarray]],
                        wave_type:str,
                        update_keys:Optional[Dict[str,str]]=None,
                        purge_header:bool=True,
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
        wave_type : str,
            Adds a column `Waveform type` containing this string as a constant.
        update_keys : dict [`str`, `str`], default `NoneType`
            A dictionary to remap lead names: [`old`, `new`]
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
        is_type(wave_type, str, 'wave_type')
        self.kwargs_pdd = kwargs
        PREV = 'previous'
        # do we need to purge the header information
        # otherwise this persists throughout calls
        if purge_header == True:
            setattr(self, PREV, None)
        else:
            if not hasattr(self, PREV):
                setattr(self, PREV, None)
        # #### initiate table and map lists
        table = pd.DataFrame()
        for w, k in zip(lead_list, getattr(self, PDNames.KEY_L), strict=True):
            # do we need to remap key names
            if update_keys is not None:
                w = {update_keys.get(k, k): v for k, v in w.items()}
            # confirm the dictionary keys are identical
            current_keys = list(w.keys())
            if getattr(self, PREV) is not None:
                if current_keys != getattr(self, PREV):
                    raise KeyError('The dictionaries contain distinct keys. '
                                   'The last set of valid keys was {}, '
                                   'compared to {}.'.\
                                   format(getattr(self, PREV), current_keys))
            # if the same map to dataframe
            temp_df = pd.DataFrame(w, **self.kwargs_pdd)
            temp_df[PDNames.SOP_UID] = k
            table = pd.concat([table, temp_df], ignore_index=True)
            # clean
            setattr(self, PREV, current_keys)
            del current_keys
        # #### formatting to long
        if table.empty == False:
            table[PDNames.SAMPLING_SEQ] = table.groupby(
                PDNames.SOP_UID).cumcount()
            long_table = pd.melt(table, id_vars=\
                                 [PDNames.SOP_UID, PDNames.SAMPLING_SEQ],
                                 value_vars=getattr(self, PREV),
                                 var_name=PDNames.COL_LEAD,
                                 value_name=PDNames.COL_VOLTAGE
                                 )
            long_table[PDNames.COL_WAVETYPE] = wave_type
        else:
            long_table = table
        # #### return
        return long_table
    # /////////////////////////////////////////////////////////////////////////
    def write_ecg(self, target_tar: None | str = None, target_path:str='.',
                  sep:str='\t', mode:str='w:gz',
                  compression:str | None ='gzip',
                  update_keys: None | dict[str,str] =None,
                  write_failed:bool=True,
                  **kwargs:Optional[Any],
                  ) -> Self:
        '''
        Extracts dicom files, and write these one by one to a set of target
        files. By appending each dicom individually to the target files the
        memory footprint of this function will be minimal.
        
        Parameters
        ----------
        target_tar : str, default `NoneType`
            The `name` of an optional tarfile where the individual files will
            be written to. The target_tar will be concatenated to
            `target_path` and depending on `mode` this directory will be
            tar.gz compressed. Set `target_tar` to `NoneType` to simply add
            the files directly to `target_path`. Note this will overwrite
            any potential directory or files with the identical names.
        target_path : str, default '.'
            The full path where the files should be written to. if provided
            `target_tar` will be created underneath this path, otherwise the
            files will be directly written to the `target_path` terminal
            directory (assuming this is writable).
        sep : str, default '\t'`
            The file separator, which will be passed to
            pandas.DataFrame.to_csv.
        mode : str, default `w:gz`
            The tarfile.open mode.
        compression : str, default `gzip`
            The file compression passed to pandas.DataFrame.write_csv.
        update_keys : dict [`str`, `str`], default `NoneType`
            A dictionary to remap lead names: [`old`, `new`]
        write_failed : bool, default `True`
            Whether to write a text file to disk containing the failed file
            names.
        **kwargs : Optional[Any],
            Keyword arguments used in the call method of a `BaseReader`
            instance.
        
        Attributes
        ----------
        target_path : str
            The directory or tar file path were the files are written to.
        NoDataList : `list` [`str`]
            A list of dicom files without a waveform_array.
        
        Returns
        -------
        self : `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        
        Notes
        -----
        This method writes the following files to disk:
        - `GeneralInfoTable.tsv`
        - `WaveFormsTable.tsv`
        - `MedianWaveTable.tsv`
        - `FailedFiles.txt`
        
        Raises
        ------
        NotADirectoryError or PermissionError
            If the target directory does not exist or is not writable.
        '''
        self.kwargs = kwargs
        # #### check input and set constants
        is_type(target_tar, (type(None), str))
        is_type(target_path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(sep, str)
        is_type(mode, str)
        is_type(compression, (type(None), str))
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
            setattr(self, PDNames.WRITE_ECG_PATH, target)
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.CPATH_L):
            raise NotCalledError()
        # #### extract dicom data
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
                print([key_list[-1]])
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                    pd.DataFrame([info], index=[key_list[-1]]).to_csv(
                        os.path.join(target, PDNames.INFO_FILE), sep=sep,
                        header=True, compression=compression)
                # waveforms
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                    self._get_long_table(
                        [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                        update_keys=update_keys,
                        purge_header=True,
                    ).to_csv(
                            os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                            header=True, compression=compression)
                # median beats
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                    self._get_long_table(
                        [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                        update_keys=update_keys,
                        purge_header=True,
                    ).to_csv(
                            os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                            header=True, compression=compression)
            else:
                # appending using mode = 'a'
                # metadata
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MET:
                    pd.DataFrame([info], index=[key_list[-1]]).to_csv(
                        os.path.join(target, PDNames.INFO_FILE), sep=sep,
                        header=False, mode='a', compression=compression)
                # waveforms
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_RTM:
                    self._get_long_table(
                        [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                        update_keys=update_keys,
                        purge_header=False,
                    ).to_csv(
                            os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                            header=False, mode='a', compression=compression)
                # median beats
                if getattr(self, PDNames.INFO_TYPE) in self.INFO_MED:
                    self._get_long_table(
                        [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                        update_keys=update_keys,
                        purge_header=False,
                    ).to_csv(
                            os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                            header=False, mode='a', compression=compression)
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
            setattr(self, PDNames.WRITE_ECG_PATH, target_final)
        # #### return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def write_pdf(self, ecgdrawing:ECGDrawing,
                  target_path:str='.', write_failed:bool=True,
                  kwargs_reader:Dict[Any,Any] | None=None,
                  kwargs_drawing:Dict[Any,Any] | None=None,
                  kwargs_savefig:Dict[Any,Any] | None=None,
                  ) -> Self:
        '''
        Extracts dicom files, and write these one by one to a pdf files
        using a supplied `ECGDrawing` instance.
        
        Parameters
        ----------
        ecgdrawing : ECGDrawing
            An instance of the ECGDrawing data class.
        target_path : `str`, default '.'
            The full path where the pdfs should be written to.
        write_failed : `bool`, default `True`
            Whether to write a text file to disk containing the failed file
            names.
        kwargs_*: dict [`any`, `any`], default `NoneType`
            dictionaries with keyword arguments for the `plt.savefig`,
            ECGDrawing, or BaseReader instances.
        
        Attributes
        ----------
        target_path : `str`
            The directory or tar file path were the files are written to.
        NoDataList : `list` [`str`]
            A list of dicom files without a waveform_array.
        
        Returns
        -------
        self : `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        
        Notes
        -----
        The dicom UID instance will be used as file name for the pdfs.
        
        Raises
        ------
        NotADirectoryError or PermissionError
            If the target directory does not exist or is not writable.
        '''
        # #### check input and set constants
        is_type(kwargs_reader, (type(None), dict))
        is_type(kwargs_drawing, (type(None), dict))
        is_type(kwargs_savefig, (type(None), dict))
        is_type(ecgdrawing, ECGDrawing)
        is_type(target_path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(write_failed, bool)
        # check readability
        _check_presence(target_path)
        _check_readable(target_path)
        # map None to dict
        kwargs_savefig, kwargs_reader, kwargs_drawing= assign_empty_default(
                [kwargs_savefig, kwargs_reader, kwargs_drawing], dict)
        # map info type to type of plot
        if getattr(self, PDNames.INFO_TYPE) == PDNames.INFO_TYPE_MET:
            raise AttributeError('`info` should be {0} or {1}.'.format(
                PDNames.INFO_TYPE_MED, PDNames.INFO_TYPE_RTM))
        elif getattr(self, PDNames.INFO_TYPE) == PDNames.INFO_TYPE_ALL:
            signal_type = PDNames.WAVETYPE_RHYTHM
        else:
            signal_type = getattr(self, PDNames.INFO_TYPE)
        # #### create target path
        if target_path == '.':
            target_path = os.getcwd()
        # assign to self
        target = target_path
        setattr(self, PDNames.WRITE_ECG_PATH, target)
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.CPATH_L):
            raise NotCalledError()
        # #### extract dicom data
        key_list, no_data_list = [[] for _ in range(2)]
        # loop over individual dcm files
        for p in getattr(self, PDNames.CPATH_L):
            no_data_list, key_list, ecg_inst = self._write_internal(
                path=p, no_data_list=no_data_list, key_list=key_list,
                **kwargs_reader,
                )
            if isinstance(ecg_inst, str):
                continue
            # #### updated leads
            # if update_keys is not None:
            #     w = {update_keys.get(k, k): v for k, v in w.items()}
            # ##### draw and write figure
            artist = ecgdrawing(ecgreader=ecg_inst, wave_type=signal_type,
                                **kwargs_drawing)
            filename_pdf = re.sub(r"[ ,\-\(\)\{\}]", '_', key_list[-1]) + '.pdf'
            plt.savefig(fname=os.path.join(target, filename_pdf), **kwargs_savefig)
            plt.close(artist.fig)
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
        # #### return
        return self
    # /////////////////////////////////////////////////////////////////////////
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



