'''
A module to extract median beats and raw waveforms from DICOM ECGs wrapping
pydicom.
'''


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import numpy as np
import pandas as pd
import pathlib
import warnings
from pydicom import dcmread
from pydicom.dataset import FileDataset as DCM_Class
from datetime import datetime
from scipy import signal
from dataclasses import dataclass
from typing import List, Type, Union, Tuple, Self, Dict
from ecgprocess.errors import (
    NotCalledError,
    is_type,
    MissingDICOMTagError,
    Error_MSG,
    _check_readable,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    DICOMTags,
)
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGDICOMReader(object):
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
    
    Attributes
    ----------
    augment_leads: bool, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample: bool, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    METADATA: dict
        A dictionary describing the metadata one wants to extract from a
        DICOM. The dictionary keys represents the `target` (new) name and the
        dictionary values the `source` (old) names.
    RESULTS_LIST: list
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
    """
    # #### parameters, with defaults
    augment_leads: bool=False
    resample_500:bool= True
    # #### check input
    is_type(augment_leads, bool, 'augment_leads')
    is_type(resample_500, bool, 'resample_500')
    # #### default tags
    DEFAULT_DICTS = DICOMTags
    METADATA = DEFAULT_DICTS.METADATA
    WAVE_FORMS = DEFAULT_DICTS.WAVE_FORMS
    WAVE_FORMS_LIST = DEFAULT_DICTS.WAVE_FORMS_LIST
    MEDIAN_BEATS_LIST = DEFAULT_DICTS.MEDIAN_BEATS_LIST
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
        GeneralInfo: list
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
            Returns the class instance with updated attributes exracted
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
        # #### end of `dicom` part, optionally printing tags which were missing
        if verbose == True:
            if len(empty_metadata) + len(empty_wave_forms) > 0:
                warnings.warn(
                    'The following DICOM tags could not be found: {}.'.format(
                        empty_metadata + empty_wave_forms))
        # #### The results dictionary
        results_dict = {}
        for t in self.RESULTS_LIST:
            # if present in WAVE or SETTINGS assign
            if hasattr(self, t):
                results_dict[t] = getattr(self, t)
            else:
                raise ValueError('`{0}` is not available.'.format(s))
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
        leadnames: dict
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
        Extracts the voltages out of the DICOM files. Will automatically
        extract the limb leads if missing, please see:
        `url <https://ecgwaves.com/topic/ekg-ecg-leads-electrodes-systems-limb-chest-precordial/>`_.
        
        Parameters
        ----------
        waveform_array: np.ndarray
            An array with the waveforms.
        lead_info: dict
            A dictionary where the keys match the `waveform_array` rows and
            the dictionary values contain the lead name strings.
        augment_leads: bool
            Whether to calculate the additional augmented leads. Will only work
            if there are exactly 8 leads available.
        
        Returns
        -------
        leads: dict
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
path = '/home/amand/google_drive/Research/ECGProcess/ecgprocess/example_data/example_datasets/example-DICOM.dcm'
ecgdicomreader = ECGDICOMReader()
path_list = [path]

class ECGDICOMTable(object):
    '''
    Takes an `ECGDICOMReader` instance and loops over a list of dicom paths
    and maps these to numpy or pandas tables which can be saved to disk.
    
    Attributes
    ----------
    path_list: list of strings
        A list of dcm file paths.
    '''
    
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, ecgdicomreader:ECGDICOMReader, path_list:List[str],
                 ) -> None:
        """
        Initialises a new instance of `ECGDICOMTable`.
        
        Parameters
        ----------
        ecgdicomreader: ECGDICOMReader
            An instance of the ECGDICOMReader data class.
        path_list: list of strings
            A list of paths to one or more .dcm files.
        """
        # #### check input
        is_type(ecgdicomreader, ECGDICOMReader, 'ecgdicomreader')
        is_type(path_list, list, 'path_list')
        self.ecgdicomreader = ecgdicomreader
        self.path_list = path_list
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        return (f"ECGDICOMTable instance with "
                f"augment_leads={self.ecgdicomreader}, "
                f"resample_500={self.path_list}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        return (f"ECGDICOMTable(augment_leads={self.ecgdicomreader}, "
                f"resample_500={self.path_list})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, skip_missing:bool=True, verbose:bool=False,
                 **kwargs:Optional[Any],
                 ) -> Self:
        """
        Will take a ECGDICOMReader and loops over a list of dcm file paths and
        maps these to metadata, waveforms, median beats tables.
        
        Parameters
        ----------
        skip_missing: bool, default `True`
            Whether missing files or files without read permsissions should
            be skipped.
        verbose: bool, default `False`
            Prints missing files if skip_missing is set to `True`.
        **kwargs: optional
            Keyword arguments used in teh call method of the `ECGDICOMReader`
            instance
        
        Attributes
        ----------
        FailedPathsList: list of string
            File paths which were either absent or without read permission.
        IndexList: list
            A list of unique identifiers.
        GeneralInfoList: list
            A list of metadata with the same order as `INdexList`.
        WaveformsList: list of dicts
            A list of dictionaries with the individual leads as keys and
            the waveforms as numpy arrays assigned to the values.
        MedianWaveformsList: list of dicts
            A list of dictionaries with the individual leads as keys and
            the MedianWaveforms as numpy arrays assigned to the values.
        
        Returns
        -------
        self: `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        is_type(skip_missing, bool, 'skip_missing')
        is_type(verbose, bool, 'verbose')
        self.skip_missing = skip_missing
        self.verbose = verbose
        self.kwargs = kwargs
        # #### loop over path
        key_list, info_list, wave_list, median_list, empty_list =\
            [[] for _ in range(5)]
        # loop over individual dcm files
        for p in self.path_list:
            try:
                ecg_inst = ecgdicomreader(p, **self.kwargs)
            except PermissionError:
                empty_list.append(p)
                # try next
                pass
            # extract unique identifier and check if it has been used before
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
        # #### set to self
        setattr(self, PDNames.FAILED_PATHS_L, empty_list)
        setattr(self, PDNames.INFO_L, info_list)
        setattr(self, PDNames.WAVE_L, wave_list)
        setattr(self, PDNames.MEDIAN_L, median_list)
        setattr(self, PDNames.KEY_L, key_list)
        # #### verbose
        if self.verbose == True:
            if len(getattr(self, PDNames.FAILED_PATHS_L))>0:
                warnings.warn(
                    'The following files could not be accessed or found: {}.'.\
                    format(getattr(self, PDNames.FAILED_PATHS_L))
                )
        # #### return
        return self
    # /////////////////////////////////////////////////////////////////////////
    def table(self) -> Self:
        """
        Will map extracted dicom data to tables.
        
        Attributes
        ----------
        
        Returns
        -------
        self: `ECGDICOMTable` instance
            Returns the class instance with updated attributes.
        """
        # #### check if __call__ has been run
        if not hasattr(self, PDNames.KEY_L):
            raise NotCalledError()
        # #### make tables
        setattr(self, PDNames.INFO_T, pd.DataFrame(
            getattr(self, PDNames.INFO_L), index=getattr(self, PDNames.KEY_L)
        ))
# make this into a _private method with waveform column to differentiate between
# rhythm and median beats
wave_tab = pd.DataFrame()
for w, k in zip(wave_list, key_list):
    temp_df = pd.DataFrame(w)
    temp_df['key'] = k
    wave_tab = pd.concat([wave_tab, temp_df], ignore_index=True)

wave_tab['sample_id'] = wave_tab.groupby('key').cumcount()
df_long = pd.melt(wave_tab, id_vars=['key', 'sample_id'],
                  value_vars=\
                  ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'],
                  var_name='lead', value_name='voltage'
                  )
df_long['waveform'] = 'rhythm'

wave_tab = pd.wide_to_long(wave_tab, stubnames ='lead_', i="id", j="lead",suffix = '\w+').sort_index(level=0)
        WaveformsTable = pd.DataFrame(wave_list, index=key_list)
            

                getattr(ecg_inst, 'SOPinstanceUID')
            w = pd.DataFrame(ecg_inst.Waveforms)

        w = w.add_prefix('lead_')
        w["id"] = w.index
        w = pd.wide_to_long(w, stubnames ='lead_', i="id", j="lead",suffix = '\w+').sort_index(level=0)
        w["SOPinstanceUID"] = ecg_inst.SOPinstanceUID
        w["waveform"] = "rhythm"
        w = w.reset_index()
        w = w[["SOPinstanceUID", "waveform","lead", "id","lead_"]]
        w = w.rename(columns = {'lead_':'voltage', 'id':'sample_id', 'SOPinstanceUID':'record_id_ecg'})

        



# ecginst(path)
# ecginst.general_info
