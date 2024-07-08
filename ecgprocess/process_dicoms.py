'''
A module to extract median beats and raw waveforms from DICOM ECGs wrapping
pydicom.
'''


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import numpy as np
import pathlib
import warnings
from pydicom import dcmread
from pydicom.dataset import FileDataset as DCM_Class
from pydicom.waveforms import multiplex_array
from datetime import datetime
from scipy import signal
from dataclasses import dataclass
from typing import Any, List, Type, Union, Tuple, Self, Dict
from ecgprocess.errors import (
    is_type,
    MissingDICOMTagError,
    Error_MSG,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    DICOMTags,
)
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# NOTE check the following: the unit object not being returned
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
        
        Returns
        -------
        self: `ECGDICOMReader` instance
            Returns the class instance with updated attributes exracted
            from `dcmread`.
        """
        is_type(path, (pathlib.PosixPath, str), 'path')
        is_type(skip_empty, bool, 'skip_empty')
        is_type(verbose, bool, 'verbose')
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
                    'The following DICOM tags could not be found:{}'.format(
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
            An `pydicom.sequence.Sequence` instance.
        
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
            units = PDNames.UNIT
            # NOTE unit is currently not returned,
            # Looks like CHANNEL_SENS should be assigned to unit and returned?
            # Need to discuss this.
            if hasattr(channel, PDNames.CHANNEL_SENS):
                units = getattr(channel, PDNames.CHANNEL_SENS)
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
        Re-sampling the sampling frequency from 250 to 500 hz.
        """
        if int(getattr(self, PDNames.SF)) != 500:
            lead_volt_temp = getattr(self, PDNames.LEAD_VOLTAGES)
            for i in lead_volt_temp:
                lead_volt_temp[f"{i}"] =\
                    signal.resample(lead_volt_temp[f"{i}"], 5000)
            # assign to self again
            setattr(self, PDNames.LEAD_VOLTAGES, lead_volt_temp)
            if getattr(self, PDNames.MEDIAN_PRESENT) == True:
                lead_volt_temp2 = getattr(self, PDNames.LEAD_VOLTAGES2)
                for i in lead_volt_temp2:
                    lead_volt_temp2[f"{i}"] = \
                        signal.resample(lead_volt_temp2[f"{i}"], 600)
                # assign to self again
                setattr(self, PDNames.LEAD_VOLTAGES2, lead_volt_temp2)

