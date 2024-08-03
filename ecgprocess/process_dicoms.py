'''
A module to extract median beats and raw waveforms from DICOM ECGs wrapping
pydicom.
'''


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import os
import sys
import uuid
import pathlib
import warnings
import numpy as np
import pandas as pd
from pydicom import dcmread
from pydicom.dataset import FileDataset as DCM_Class
from datetime import datetime
from scipy import signal
from dataclasses import dataclass
from typing import List, Type, Union, Tuple, Self, Dict, Optional, Any
from ecgprocess.errors import (
    NotCalledError,
    is_type,
    MissingDICOMTagError,
    Error_MSG,
    STDOUT_MSG,
    _check_readable,
    _check_presence,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    DICOMTags,
)
from ecgprocess.utils.general import (
    replace_with_tar,
)
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Base class with slots
class BaseECGDICOMReader:
    '''
    An ECGDICOMReader base class implementing the more efficient __slots__ for
    the waveform arrays, while still retaining __dict__ dynamic attribute
    creation.
    '''
    __slots__ = (PDNames.LEAD_VOLTAGES, PDNames.LEAD_VOLTAGES2)
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, lead_voltages=None, lead_voltages2=None):
        '''
        Initialises both slot entries to `None`.
        '''
        setattr(self, PDNames.LEAD_VOLTAGES, lead_voltages)
        setattr(self, PDNames.LEAD_VOLTAGES2, lead_voltages2)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGDICOMReader(BaseECGDICOMReader):
    """
    Takes an ECG DICOM file and extracts metadata, median beats (if available)
    and raw waveforms.
    
    Parameters
    ----------
    augment_leads: bool, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample: bool, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    retain_raw: bool, default `False`
        Whether the raw pydicom instance and raw waveforms should be retained.
        Set to `False` to decrease memory usage. Set to `True` to explore the
        orignal pydicom instance. For example, use this one a few files to
        identify none-standard information to extract.
    
    Attributes
    ----------
    augment_leads: bool, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample: bool, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    METADATA: dict [`str`, `str`]
        A dictionary describing the metadata one wants to extract from a
        DICOM. The dictionary keys represents the `target` (new) name and the
        dictionary values the `source` (old) names.
    RESULTS_LIST: list [`str`, `str`]
        A list of attribute one wants to extract, should map predominantly to
        the keys in  `METADATA` and `WAVE_FROMS`.
    STUDY_DATE_SOURCE: str
        The study date format of the source DICOM.  This will be used in
        `datetime.strptime` as format argument.
    STUDY_DATE_TARGET: str
        The target formatting of the study date.  This will be used in
        `datetime.strptime` as format argument.
    ACQUISITION_DATE_SOURCE: str
        The acquisition date and time format of the source DICOM.  This will be
        used in `datetime.strptime` as format argument.
    ACQUISITION_DATE_TARGET: str
        The target formatting of the acquisition date and time.  This will be
        used in `datetime.strptime` as format argument.
    
    Methods
    -------
    make_leadvoltages(waveform_array, lead_info, augment_leads)
        Extracts the voltages from a DICOM file. Will automatically extract the
        limb leads if missing.

    Notes
    -----
    The waveforms are stored using `__slots__` to decrease memory usage, which
    is further improved by setting `retain_raw` to `False` - the default
    behaviour.
    """
    # #### set slots
    # __slots__ = (PDNames.LEAD_VOLTAGES, PDNames.LEAD_VOLTAGES2)
    # #### parameters, with defaults
    augment_leads: bool=False
    resample_500:bool=True
    retain_raw:bool=False
    # #### check input
    is_type(augment_leads, bool, 'augment_leads')
    is_type(resample_500, bool, 'resample_500')
    # #### default tags
    DEFAULT_DICTS = DICOMTags()
    METADATA = DEFAULT_DICTS.METADATA
    WAVE_FORMS = DEFAULT_DICTS.WAVE_FORMS
    WAVE_FORMS_LIST = DEFAULT_DICTS.WAVE_FORMS_LIST
    MEDIAN_BEATS_LIST = DEFAULT_DICTS.MEDIAN_BEATS_LIST
    ECG_TRAIT_LIST = DEFAULT_DICTS.ECG_INTERPERTATION_LIST
    RESULTS_LIST = DEFAULT_DICTS.RESULTS_LIST
    # #### default dates to extract and format
    STUDY_DATE_SOURCE = "%Y%m%d"
    STUDY_DATE_TARGET = "%Y-%m-%d"
    ACQUISITION_DATE_SOURCE = "%Y%m%d%H%M%S"
    ACQUISITION_DATE_TARGET = "%Y-%m-%d %H:%M:%S"
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, skip_empty:bool=True, verbose:bool=False,
                 ) -> Self:
        """
        Read a `.dcm` DICOM file and extracts metadata, raw waveforms, and
        median beats.
        
        see `constants.DICOMTags` for the `METADATA`, `WAVE_FORMS`, and
        `MEADIAN_BEATS` tags looked for.
        
        Parameters
        ----------
        path: str
            The path to the .dcm file.
        skip_empty: bool, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose: bool, default `False`
            Prints missing tags if skip_empty is set to `True`.
        
        Attributes
        ----------
        GeneralInfo: list [`str`]
            A list of dcmread extracted attributes.
        Waveforms: dict of arrays
            The lead specific ECG waveforms.
        MedianWaveforms: dict of arrays
            The lead specific ECG median beats.
        DMCReadInstance: DCM class instance
            The original dcmread instance.
        
        
        Returns
        -------
        self: `ECGDICOMReader` instance
            Returns the class instance with updated attributes extracted
            from `dcmread`.
        """
        is_type(path, (pathlib.PosixPath, str), 'path')
        is_type(skip_empty, bool, 'skip_empty')
        is_type(verbose, bool, 'verbose')
        # confirm file is readable
        _check_readable(path)
        # #### Read DICOM
        # NOTE `with` closes automatically if an error is raised
        with open(path, 'rb') as dicom:
            # reads standard dicom content
            ECG=dcmread(dicom)
            # #### extract metadata
            empty_metadata = []
            for t, s in self.METADATA.items():
                if hasattr(ECG, s):
                    # Assign if present
                    setattr(self, t, getattr(ECG, s))
                elif skip_empty == False:
                    # Should an Error be returned
                    raise MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    setattr(self, t, np.nan)
                    empty_metadata.append(s)
            # #### Extract waveforms
            try:
                nam, el = self.WAVE_FORMS_LIST[PDNames.WAVE_ARRAY]
                setattr(self, PDNames.WAVE_ARRAY,
                        getattr(ECG, nam)(el).T)
            except:
                raise ValueError(Error_MSG.MISSING_DICOM.format(nam))
            WAVE = getattr(ECG, PDNames.WAVE_FORM_SEQ)[0]
            SETTINGS = getattr(WAVE, PDNames.CHANNEL_DEF_SEQ)[0]
            # loop over the remaining wave form data
            empty_wave_forms = []
            for t, s in self.WAVE_FORMS.items():
                # if present in WAVE or SETTINGS assign
                if hasattr(WAVE, s):
                    setattr(self, t, getattr(WAVE, s))
                elif hasattr(SETTINGS, s):
                    setattr(self, t, getattr(SETTINGS, s))
                elif skip_empty == False:
                    # Should an Error be returned
                    raise MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    setattr(self, t, np.nan)
                    empty_wave_forms.append(s)
                # Check number of channels in ECG waveform
            if getattr(self, PDNames.CHANNEL_NUMBER) >= 8:
                channel_seq = getattr(getattr(ECG, PDNames.WAVE_FORM_SEQ)[0],
                                      PDNames.CHANNEL_DEF_SEQ)
                lead_info_waveform=self._get_lead_info(channel_seq)
                setattr(self, PDNames.LEAD_VOLTAGES,
                        self.make_leadvoltages(
                            lead_info=lead_info_waveform,
                            waveform_array=getattr(self, PDNames.WAVE_ARRAY),
                            augment_leads=self.augment_leads,
                            ))
                setattr(self, PDNames.SAMPLING_FREQ,
                        getattr(self, PDNames.SF_ORIGINAL))
                if self.retain_raw == False:
                    delattr(self, PDNames.WAVE_ARRAY)
            else:
                # set to NA
                setattr(self, PDNames.LEAD_VOLTAGES, np.nan)
                empty_wave_forms.append(PDNames.LEAD_VOLTAGES)
                setattr(self, PDNames.SAMLING_FREQ,
                        getattr(self, PDNames.SF_ORIGINAL))
            # #### Extract Median beats
            nam, el = self.MEDIAN_BEATS_LIST[PDNames.MEDIAN_ARRAY]
            if hasattr(ECG, nam):
                # Assign if present
                channel_seq_median = getattr(
                    getattr(ECG, PDNames.WAVE_FORM_SEQ)[1],
                    PDNames.CHANNEL_DEF_SEQ)
                lead_info_median=self._get_lead_info(channel_seq_median)
                setattr(self, PDNames.MEDIAN_ARRAY,
                        getattr(ECG, nam)(el).T)
                setattr(self, PDNames.MEDIAN_PRESENT, True)
                setattr(self, PDNames.LEAD_VOLTAGES2,
                        self.make_leadvoltages(
                            lead_info=lead_info_median,
                            waveform_array=\
                            getattr(self, PDNames.MEDIAN_ARRAY),
                            augment_leads=self.augment_leads,
                            ))
            elif skip_empty == False:
                raise ValueError(Error_MSG.MISSING_DICOM.format(nam))
            else:
                # set to missing
                setattr(self, PDNames.MEDIAN_ARRAY, np.nan)
                setattr(self, PDNames.LEAD_VOLTAGES2, np.nan)
                setattr(self, PDNames.MEDIAN_PRESENT, False)
            if self.retain_raw == False:
                delattr(self, PDNames.MEDIAN_ARRAY)
            # do we need to resample the freq
            if self.resample_500 == True:
                # the function will internally adjust
                # LEAD_VOLTAGES, and LEAD_VOLTAGES2
                # Nothing is returned
                self._resampling_500hz()
                setattr(self, PDNames.OVERSAMPLED, True)
                setattr(self, PDNames.SF, 500)
                setattr(self, PDNames.SAMPLING_FREQ, 500)
            else:
                setattr(self, PDNames.OVERSAMPLED, False)
        # #### Extract standard ECG measurments
        # first set everything to NA
        for e in self.ECG_TRAIT_LIST:
            setattr(self, e, np.nan)
        # next see if we can extract some interpertations.
        if hasattr(ECG, PDNames.ECG_INTERPERTATION):
            for w in getattr(ECG, PDNames.ECG_INTERPERTATION):
                if hasattr(w, PDNames.ECG_CONCEPTNAME):
                    ecg_int = getattr(w, PDNames.ECG_CONCEPTNAME)[0]
                    try:
                        # if the ECG name is in self.ECG_TRAIT_LIST add to self
                        ecg_trait = getattr(ecg_int, PDNames.ECG_TRAIT_NAME)
                        if ecg_trait in self.ECG_TRAIT_LIST:
                            setattr(self, ecg_trait,
                                    getattr(w, PDNames.ECG_TRAIT_VALUE),
                                    )
                    except AttributeError:
                        pass
        # which ECG traits are still nan
        missing_ecg_traits =\
            [e for e in self.ECG_TRAIT_LIST if np.isnan(getattr(self, e))]
        if skip_empty == False and len(missing_ecg_traits) > 0:
            # Should an Error be returned
            raise ValueError('The following ECG measurments are '
                             'unavailable: {}'.format(missing_ecg_traits))
                             
        else:
            # add missing metadata
            empty_metadata = empty_metadata + missing_ecg_traits
        # #### end of `dicom` part, optionally printing tags which were missing
        if verbose == True:
            if len(empty_metadata) + len(empty_wave_forms) > 0:
                warnings.warn(
                    'The following DICOM tags could not be found: {}.'.format(
                        empty_metadata + empty_wave_forms))
        # add duration, NOTE both values are either int/float or NA so no need
        # for a try except
        setattr(self, PDNames.DURATION,
                (
                    getattr(self, PDNames.SAMPLING_NUMBER)/
                    getattr(self, PDNames.SAMPLING_FREQ)
                )
        )
        # #### The results dictionary
        results_dict = {}
        for t in self.RESULTS_LIST:
            # if present in WAVE or SETTINGS assign
            if hasattr(self, t):
                results_dict[t] = getattr(self, t)
            else:
                raise ValueError('`{0}` is not available.'.format(t))
        # add time variables
        results_dict[PDNames.STUDY_TIME] = getattr(self, PDNames.STUDY_TIME)
        raw_AD = getattr(self, PDNames.ACQUISITION_DATE)
        raw_SD = getattr(self, PDNames.STUDY_DATE)
        results_dict[PDNames.ACQUISITION_DATE] = \
            datetime.strptime(raw_AD, self.ACQUISITION_DATE_SOURCE).\
            strftime(self.ACQUISITION_DATE_TARGET)
        results_dict[PDNames.STUDY_DATE] = \
            datetime.strptime(raw_SD, self.STUDY_DATE_SOURCE).\
            strftime(self.STUDY_DATE_TARGET)
        setattr(self, PDNames.RESULTS_DICT, results_dict)
        # add the original dcmread instance
        if self.retain_raw == True:
            setattr(self, PDNames.ORIG_DCMREAD_INST, ECG)
        # #### return stuff
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _get_lead_info(self, channel_seq: DCM_Class
                  ) -> Dict[int, str]:
        """
        Extracts the lead names from a `dcmread` instance.
        
        Parameters
        ----------
        channel_seq: DCM_Class
            A `pydicom.sequence.Sequence` instance.
        
        Returns
        -------
        leadnames: dict [`int`, `str`]
            A dictionary with numerical (interval) keys and the lead names as
            values.
        """
        # #### extracting the lead names
        leadnames = {}
        for k, channel in enumerate(channel_seq):
            # extracting lead names
            source = getattr(getattr(channel,PDNames.CHANNEL_SOURCE_SEQ)[0],
                             PDNames.CHANNEL_CODE_MEANING)
            # units = PDNames.UNIT
            # # NOTE unit is currently not returned,
            # # Looks like CHANNEL_SENS should be assigned to unit and returned?
            # # Need to discuss this.
            # if hasattr(channel, PDNames.CHANNEL_SENS):
            #     units = getattr(channel, PDNames.CHANNEL_SENS)
            # assign lead names to numericals
            leadnames[k] = source.replace(PDNames.LEAD, '').strip()
        # return stuff
        return leadnames
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def make_leadvoltages(self, waveform_array: np.ndarray,
                          lead_info:Dict[int, str],
                          augment_leads:bool,
                          ) -> Dict[str, np.ndarray]:
        """
        Extracts the voltages from a DICOM file. Will automatically extract the
        limb leads if missing, please see:
        `url <https://ecgwaves.com/topic/ekg-ecg-leads-electrodes-systems-limb-chest-precordial/>`_.
        
        Parameters
        ----------
        waveform_array: np.ndarray
            An array with the waveforms.
        lead_info: dict [`int`, `str`]
            A dictionary where the keys match the `waveform_array` rows and
            the dictionary values contain the lead name strings.
        augment_leads: bool
            Whether to calculate the additional augmented leads. Will only work
            if there are exactly 8 leads available.
        
        Returns
        -------
        leads: dict [`str`, `np.ndarray`]
            A dictionary with the lead name string as keys and leads as
            np.ndarray values.
        """
        # #### check input and set constants
        is_type(waveform_array, np.ndarray, 'waveform_array')
        is_type(lead_info, dict, 'lead_info')
        leads = {}
        # #### the main function
        for k, lead in enumerate(waveform_array):
            leads[lead_info[k]] = lead
        if (k+1) == 8 and augment_leads == True:
            # Calculate limb leads
            leads[PDNames.LEAD_III] = np.subtract(leads[PDNames.LEAD_II],
                                                  leads[PDNames.LEAD_I])
            leads[PDNames.LEAD_aVR] = np.add(leads[PDNames.LEAD_I],
                                  leads[PDNames.LEAD_II]) * (-0.5)
            leads[PDNames.LEAD_aVL] = np.subtract(leads[PDNames.LEAD_I],
                                       0.5 * leads[PDNames.LEAD_II])
            leads[PDNames.LEAD_aVF] = np.subtract(leads[PDNames.LEAD_II],
                                       0.5 * leads[PDNames.LEAD_I])
        # return
        return leads
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _resampling_500hz(self):
        """
        Re-sample the frequency to 500 hz.
        """
        if int(getattr(self, PDNames.SF)) != 500:
            # #### wave forms
            lead_volt_temp = getattr(self, PDNames.LEAD_VOLTAGES)
            for i in lead_volt_temp:
                lead_volt_temp[f"{i}"] =\
                    signal.resample(lead_volt_temp[f"{i}"], 5000)
            setattr(self, PDNames.LEAD_VOLTAGES, lead_volt_temp)
            # #### median beats
            if getattr(self, PDNames.MEDIAN_PRESENT) == True:
                lead_volt_temp2 = getattr(self, PDNames.LEAD_VOLTAGES2)
                for i in lead_volt_temp2:
                    lead_volt_temp2[f"{i}"] = \
                        signal.resample(lead_volt_temp2[f"{i}"], 600)
                setattr(self, PDNames.LEAD_VOLTAGES2, lead_volt_temp2)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class ECGDICOMTable(object):
    '''
    Takes an `ECGDICOMReader` instance and loops over a list of dicom paths
    and maps these to numpy or pandas tables which can be saved to disk.
    
    Attributes
    ----------
    RawPathList : list [`str`]
        A list of dcm file paths which have not been confirmed to exist.
    
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
    '''
    
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, ecgdicomreader:ECGDICOMReader, path_list:List[str],
                 ) -> None:
        """
        Initialises a new instance of `ECGDICOMTable`.
        
        Parameters
        ----------
        ecgdicomreader : ECGDICOMReader
            An instance of the ECGDICOMReader data class.
        path_list : list [`str`]
            A list of paths to one or more .dcm files.
        """
        # #### check input
        is_type(ecgdicomreader, ECGDICOMReader, 'ecgdicomreader')
        is_type(path_list, list, 'path_list')
        self.ecgdicomreader = ecgdicomreader
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
    def __call__(self, skip_missing:bool=True, verbose:bool=False,
                 ) -> Self:
        """
        Will take a ECGDICOMReader and loops over a list of dcm file paths and
        and confirm the files exist and have appropriate read permission
        
        Parameters
        ----------
        skip_missing : bool, default `True`
            Whether missing files or files without read permissions should
            be skipped.
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
        self: `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        is_type(skip_missing, bool, 'skip_missing')
        is_type(verbose, bool, 'verbose')
        self.skip_missing = skip_missing
        self.verbose = verbose
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
                if skip_missing == True:
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
            Keyword arguments used in the call method of a `ECGDICOMReader`
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
        
        Returns
        -------
        self: `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        self.kwargs = kwargs
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.CPATH_L):
            raise NotCalledError()
        # #### extract dicom data
        key_list, info_list, wave_list, median_list = [[] for _ in range(4)]
        # loop over individual dcm files
        for p in getattr(self, PDNames.CPATH_L):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance
            ecg_inst = self.ecgdicomreader(p, **self.kwargs)
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
            info_list.append(getattr(ecg_inst, PDNames.RESULTS_DICT))
            wave_list.append(getattr(ecg_inst, PDNames.LEAD_VOLTAGES))
            median_list.append(getattr(ecg_inst, PDNames.LEAD_VOLTAGES2))
        # #### make tables
        setattr(self, PDNames.KEY_L, key_list)
        # general info
        setattr(self, PDNames.INFO_T, pd.DataFrame(
            info_list, index=getattr(self, PDNames.KEY_L)
        ))
        # wave forms, and median beta
        setattr(self, PDNames.WAVE_T, self._get_long_table(
            wave_list, wave_type=PDNames.WAVETYPE_RHYTHM,
            update_keys=update_keys,
        ))
        setattr(self, PDNames.MEDIAN_T, self._get_long_table(
            median_list, wave_type=PDNames.WAVETYPE_MEDIAN,
            update_keys=update_keys,
        ))
        # #### Return
        setattr(self, PDNames.TABLE_CALLED, 'True')
        return self
    # /////////////////////////////////////////////////////////////////////////
    def _get_long_table(self, lead_list:List[Dict[str, np.ndarray]],
                        wave_type:str,
                        update_keys:Optional[Dict[str,str]]=None,
                        previous_header:Optional[List[str]]=None,
                        **kwargs,
                        ) -> pd.DataFrame:
        '''
        Mapping lists of dictionaries containing lead specific numpy arrays
        to a long-formatted pandas table.
        
        Parameters
        ----------
        lead_list: list of dicts
            A list of dictionaries with the lead mapped to the keys and the
            voltage mapped to the values.
        wave_type: str,
            Adds a column `Waveform type` containing this string as a constant.
        update_keys: dict [`str`, `str`], default `NoneType`
            A dictionary to remap lead names: [`old`, `new`]
        **kwargs: optional
            keyword arguments passed to pd.DataFrame.
        
        Attributes
        ----------
        kwargs_pdd: optional
            The keyword arguments supplied to pd.DataFrame.
        
        Returns
        -------
        self: pd.DataFrame
            A long-formatted table with lead, voltage, sampling indicator
            columns grouped by file (including an unique file indicator column)
        '''
        # #### check input and set constants
        is_type(lead_list, list, 'lead_list')
        is_type(wave_type, str, 'wave_type')
        self.kwargs_pdd = kwargs
        # #### initiate table and map lists
        table = pd.DataFrame()
        if previous_header is None:
            previous = None
        else:
            previous = previous_header
        for w, k in zip(lead_list, getattr(self, PDNames.KEY_L)):
            # do we need to remap key names
            if update_keys is not None:
                w = {update_keys.get(k, k): v for k, v in w.items()}
            # confirm the dictionary keys are identical
            current_keys = list(w.keys())
            if previous is not None:
                if current_keys != previous:
                    raise KeyError('The dictionaries contain distinct keys. '
                                   'The last set of valid keys was {}, '
                                   'compared to {}.'.\
                                   format(previous, current_keys))
            # if the same map to dataframe
            temp_df = pd.DataFrame(w, **self.kwargs_pdd)
            temp_df[PDNames.SOP_UID] = k
            table = pd.concat([table, temp_df], ignore_index=True)
            # clean
            previous=current_keys
            del current_keys
        # #### formatting to long
        table[PDNames.SAMPLING_SEQ] = table.groupby(
            PDNames.SOP_UID).cumcount()
        long_table = pd.melt(table, id_vars=\
                          [PDNames.SOP_UID, PDNames.SAMPLING_SEQ],
                          value_vars=previous, var_name=PDNames.COL_LEAD,
                          value_name=PDNames.COL_VOLTAGE
                          )
        long_table[PDNames.COL_WAVETYPE] = wave_type
        # #### return
        return long_table
    # /////////////////////////////////////////////////////////////////////////
    def write_ecg(self, target_tar:Union[None,str]=None, target_path:str='.',
                  sep:str='\t', mode:str='w:gz', compression:str='gzip',
                  update_keys:Optional[Dict[str,str]]=None,
                  **kwargs:Optional[Any],
                  ):
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
        **kwargs : Optional[Any],
            Keyword arguments used in the call method of a `ECGDICOMReader`
            instance.
        
        Attributes
        ----------
        target_path : str
            The directory or tar file path were the files are written to.
        
        Returns
        -------
        None
        
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
        is_type(target_tar, (type(None), str), 'target_tar')
        is_type(target_path, (pathlib.PosixPath, str), 'target_path')
        is_type(sep, str, 'sep')
        is_type(mode, str, 'mode')
        is_type(compression, str, 'compression')
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
            setattr(self, PDNames.WRITE_ECS_PATH, target)
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.CPATH_L):
            raise NotCalledError()
        # #### write empty files, note not compressing these
        with open(os.path.join(target, PDNames.FAILED_FILE), 'w') as file:
            for p in getattr(self, PDNames.FPATH_L):
                file.write(p + '\n')
        # #### extract dicom data
        first=True
        key_list = []
        # loop over individual dcm files
        for p in getattr(self, PDNames.CPATH_L):
            if self.verbose == True:
                print(STDOUT_MSG.PROCESSING_PATH.format(p), file=sys.stdout)
            # get instance
            ecg_inst = self.ecgdicomreader(p, **self.kwargs)
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
            setattr(self, PDNames.KEY_L, [key])
            info=getattr(ecg_inst, PDNames.RESULTS_DICT)
            wave=getattr(ecg_inst, PDNames.LEAD_VOLTAGES)
            median=getattr(ecg_inst, PDNames.LEAD_VOLTAGES2)
            # write to disk
            if first==True:
                first = False
                # metadata
                pd.DataFrame([info], index=[key]).to_csv(
                    os.path.join(target, PDNames.INFO_FILE), sep=sep,
                    header=True, compression=compression)
                # waveforms
                self._get_long_table(
                    [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                    update_keys=update_keys,
                ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=True, compression=compression)
                wave_head = list(wave.keys())
                # median beats
                self._get_long_table(
                    [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                    update_keys=update_keys,
                ).to_csv(
                        os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                        header=True, compression=compression)
                median_head = list(median.keys())
            else:
                # appending using mode = 'a'
                # metadata
                pd.DataFrame([info], index=[key]).to_csv(
                    os.path.join(target, PDNames.INFO_FILE), sep=sep,
                    header=False, mode='a', compression=compression)
                # waveforms
                self._get_long_table(
                    [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                    update_keys=update_keys,
                    previous_header=wave_head,
                ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=False, mode='a', compression=compression)
                wave_head = list(wave.keys())
                # median beats
                self._get_long_table(
                    [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                    update_keys=update_keys,
                    previous_header=median_head,
                ).to_csv(
                        os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                        header=False, mode='a', compression=compression)
                median_head = list(median.keys())
            # delete key
            delattr(self, PDNames.KEY_L)
        # #### if needed replace directory by tar.gz version
        if target_tar is not None:
            # create the final target path
            target_final = os.path.join(target_path, target_tar)
            replace_with_tar(target, target_final, mode=mode)
            setattr(self, PDNames.WRITE_ECS_PATH, target_final)
        # #### return
        return self


