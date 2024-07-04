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
from pydicom.waveforms import multiplex_array
from datetime import datetime
from scipy import signal
from typing import Any, List, Type, Union, Tuple, Callable, Self
from ecgprocess.errors import (
    is_type,
    MissingDICOMTagError,
    Error_MSG,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    DICOMTags,
)

path = '/home/amand/google_drive/Research/ECGProcess/ecgprocess/example_data/example_datasets/example-DICOM.dcm'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

class ECGDICOMReader(object):
    """
    Takes an ECG DICOM file and extracts metadata, median beats (if available)
    and raw waveforms.
    
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
    WAVE_FORMS: dict
        A dictionary describing the waveform data one wants to extract. This
        is identically organised as `METADATA`.
    MEDIAN_BEATS_LIST
        A dictionary describing the median beats data one wants to extract.
        The dictionary value contains a list with an object name (str) and
        element to extract.
    STUDY_DATE_SOURCE
        The study date format of the source DICOM.
    STUDY_DATE_TARGET
        The target formatting of the study date.
    ACQUISITION_DATE_SOURCE
        The acquisition date and time format of the source DICOM.
    ACQUISITION_DATE_TARGET
        The target formatting of the acquisition date and time.
    """
    
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, augment_leads:bool=False, resample_500:bool=True):
        """
        Initialises a new instance of `ECGDICOMReader`.
        
        Parameters
        ----------
        augment_leads: bool, default `False`
            Whether the augmented leads are available in the DICOM, if not
            these are calculated.
        resample: bool, default `True`
            Whether to resample the ECG to a frequency of 500 Hertz.
        """
        # test input
        is_type(augment_leads, bool, 'augment_leads')
        is_type(resample_500, bool, 'resample_500')
        # assign
        self.augment_leads = augment_leads
        self.resample_500 = resample_500
        # default tags to extract
        DEFAULT_DICTS = DICOMTags()
        self.METATDATA = DEFAULT_DICTS.METATDATA
        self.WAVE_FORMS = DEFAULT_DICTS.WAVE_FORMS
        self.WAVE_FORMS_LIST = DEFAULT_DICTS.WAVE_FORMS_LIST
        self.MEDIAN_BEATS_LIST = DEFAULT_DICTS.MEDIAN_BEATS_LIST
        self.RESULTS_DICTIONARY = DEFAULT_DICTS.RESULTS_DICTIONARY
        # default dates to extract and format
        self.STUDY_DATE_SOURCE = "%Y%m%d"
        self.STUDY_DATE_TARGET = "%Y-%m-%d"
        self.ACQUISITION_DATE_SOURCE = "%Y%m%d%H%M%S"
        self.ACQUISITION_DATE_TARGET = "%Y-%m-%d %H:%M:%S"
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        return (f"ECGDICOMReader instance with "
                f"augment_leads={self.augment_leads}, "
                f"resample_500={self.resample_500}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        return (f"ECGDICOMReader(augment_leads={self.augment_leads}, "
                f"resample_500={self.resample_500})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, skip_empty:bool=True, verbose:bool=False,
                 ) -> Self:
        """
        Read a `.dcm` DICOM file and extracts metadata, raw waveforms, and
        median beats.
        
        see `constants.DICOMTags` for the `METATDATA`, `WAVE_FORMS`, and
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
        # with closes automatically if an error is raised
        with open(path, 'rb') as dicom:
            # reads standard dicom content
            ECG=dcmread(dicom)
            # #### extract metadata
            empty_metadata = []
            for t, s in self.METATDATA.items():
                if hasattr(ECG, s):
                    # Assign if present
                    setattr(self, t, ECG.__getattr__(s))
                elif skip_empty == False:
                    # Should an Error be returned
                    MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    setattr(self, t, np.nan)
                    empty_metadata.append(t)
            # #### Extract waveforms
            try:
                nam, el = self.WAVE_FORMS_LIST[PDNames.WAVE_ARRAY]
                setattr(self, PDNames.WAVE_ARRAY,
                        ECG.__getattr__(nam)(el).T)
            except:
                raise ValueError(Error_MSG.MISSING_DICOM.format(nam))
            WAVE = ECG.__getattr__(PDNames.WAVE_FORM_SEQ)[0]
            SETTINGS = WAVE.__getattr__(PDNames.CHANNEL_DEF_SEQ)[0]
            # loop over the remaining wave form data
            empty_wave_forms = []
            for t, s in self.WAVE_FORMS.items():
                # if present in WAVE or SETTINGS assign
                if hasattr(WAVE, s):
                    setattr(self, t, WAVE.__getattr__(s))
                elif hasattr(SETTINGS, s):
                    setattr(self, t, SETTINGS.__getattr__(s))
                elif skip_empty == False:
                    # Should an Error be returned
                    MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    setattr(self, t, np.nan)
                    empty_wave_forms.append(t)
                # Check number of channels in ECG waveform
            if self.__getattribute__(PDNames.CHANNEL_NUMBER) >= 8:
                # TODO apply functions `get_lead_info`, `make_leadvoltages`.
                pass
                # TODO include the error if skip_empty == False
                # else:
                #     # raise errorr
                #     MissingDICOMTagError(','.join(
                #         [PDNames.LEAD_INFO, PDNames.LEAD_VOLTAGES]
                #     ))
                setattr(self, PDNames.LEAD_INFO, np.nan)
                setattr(self, PDNames.LEAD_VOLTAGES, np.nan)
                # NOTE replace this by the resampling_500hz output
                setattr(self, PDNames.SAMPLING_FREQ,
                        self.__getattribute__(PDNames.SF_ORIGINAL))
                # self.samplingfrequency     = self.resampling_500hz()
            else:
                # set to NA
                setattr(self, PDNames.LEAD_INFO, np.nan)
                setattr(self, PDNames.LEAD_VOLTAGES, np.nan)
                empty_wave_forms.append(PDNames.LEAD_INFO)
                empty_wave_forms.append(PDNames.LEAD_VOLTAGES)
                setattr(self, PDNames.SAMLING_FREQ,
                        self.__getattribute__(PDNames.SF_ORIGINAL))
            # #### Extract Median beats
            nam, el = self.MEDIAN_BEATS_LIST[PDNames.MEDIAN_ARRAY]
            if hasattr(ECG, nam):
                    # Assign if present
                    setattr(self, PDNames.MEDIAN_ARRAY,
                            ECG.__getattr__(nam)(el).T)
                    setattr(self, PDNames.MEDIAN_PRESENT, True)
                    # NOTE apply `get_lead_info`, `make_leadvoltages` functions
                    # NOTE DETETE
                    setattr(self, PDNames.LEAD_VOLTAGES2, np.nan)
                    setattr(self, PDNames.LEAD_INFO, np.nan)
            elif skip_empty == False:
                raise ValueError(Error_MSG.MISSING_DICOM.format(nam))
            else:
                # set to missing
                setattr(self, PDNames.MEDIAN_ARRAY, np.nan)
                setattr(self, PDNames.LEAD_VOLTAGES2, np.nan)
                setattr(self, PDNames.LEAD_INFO, np.nan)
                setattr(self, PDNames.MEDIAN_PRESENT, False)
        # #### end of `dicom` part, optionally printing tags which were missing
        if verbose == True:
            if len(empty_metadata) + len(empty_wave_forms) > 0:
                warnings.warn(
                    'The following DICOM tags could not be found:{}'.format(
                        empty_metadata + empty_wave_forms))
        # #### The results dictionary
        for t, s in self.RESULTS_DICTIONARY.items():
            # if present in WAVE or SETTINGS assign
            results_dict = {}
            if hasattr(self, s):
                results_dict[t] = self.__getattribute__(s)
            else:
                raise ValueError('`{0}` is not available.'.format(s))
            # add time variables
            results_dict[PDNames.STUDY_TIME] =\
                self.__getattribute__(PDNames.STUDY_TIME)
            raw_AD = self.__getattribute__(PDNames.ACQUISITION_DATE)
            raw_SD = self.__getattribute__(PDNames.STUDY_DATE)
            results_dict[PDNames.ACQUISITION_DATE] = \
                datetime.strptime(raw_AD, self.ACQUISITION_DATE_SOURCE).\
                strftime(self.ACQUISITION_DATE_TARGET)
            results_dict[PDNames.STUDY_DATE] = \
                datetime.strptime(raw_SD, self.STUDY_DATE_SOURCE).\
                strftime(self.STUDY_DATE_TARGET)
            setattr(self, PDNames.RESULTS_DICT, results_dict)
        # #### return stuff
        return self

