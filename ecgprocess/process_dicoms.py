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
import copy
import matplotlib.pylab as plt
from pydicom import dcmread
from pydicom.dataset import FileDataset as DCM_Class
from datetime import datetime
from scipy import signal
from dataclasses import dataclass, field
from typing import (
    List, Literal, Type, Union, Tuple, Self, Dict, Optional, Any,
)
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
    assign_empty_default,
    _update_kwargs,
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
    __slots__ = (PDNames.LEAD_VOLTAGES, PDNames.LEAD_VOLTAGES2,
                 PDNames.RESULTS_DICT)
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, lead_voltages=None, lead_voltages2=None,
                 results_dict=None):
        '''
        Initialises slots entries to `None`.
        '''
        setattr(self, PDNames.LEAD_VOLTAGES, lead_voltages)
        setattr(self, PDNames.LEAD_VOLTAGES2, lead_voltages2)
        setattr(self, PDNames.RESULTS_DICT, results_dict)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGDICOMReader(BaseECGDICOMReader):
    """
    Takes an ECG DICOM file and extracts metadata, median beats (if available)
    and raw waveforms.
    
    Parameters
    ----------
    augment_leads : bool, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample : bool, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    retain_raw : bool, default `False`
        Whether the raw pydicom instance and raw waveforms should be retained.
        Set to `False` to decrease memory usage. Set to `True` to explore the
        orignal pydicom instance. For example, use this one a few files to
        identify none-standard information to extract.
    
    Attributes
    ----------
    augment_leads : bool
        Whether the augmented leads were calculated if these were unavailable.
    resample : bool
        Whether the ECG was resampled to a 500 Hertz frequency.
    retain_raw : bool
        Whether the raw pydicom data was retained.
    METADATA : dict [`str`, `str`]
        A dictionary describing the metadata one wants to extract from a
        DICOM. The dictionary keys represents the `target` (new) name and the
        dictionary values the `source` (old) names.
    ECG_TRAIT_DICT : dict [`str`, `list[str]`]
        A dictionary with the keys reflecting the desired name of the ECG trait.
        Each key will have a list of strings as a value. These strings will be
        compared to the names in `WaveformAnnotationSequence` attribute.
        Matching is done without case-sensitivity.  If for any key there are
        multiple matching strings the algorithm will check if the extracted
        values are all the same, if not multiple entries will be returned for
        the user to decide what to do next. The extracted ECG traits will be
        included with the extracted METADATA.
    STUDY_DATE_SOURCE : str
        The study date format of the source DICOM.  This will be used in
        `datetime.strptime` as format argument.
    STUDY_DATE_TARGET : str
        The target formatting of the study date.  This will be used in
        `datetime.strptime` as format argument.
    ACQUISITION_DATE_SOURCE : str
        The acquisition date and time format of the source DICOM.  This will be
        used in `datetime.strptime` as format argument.
    ACQUISITION_DATE_TARGET : str
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
    # #### default tags - hacking about to make these non-persistance
    # NOTE this is probably related to DICOMTags being a @dataclass
    METADATA = copy.deepcopy(DICOMTags().METADATA)
    WAVE_FORMS = copy.deepcopy(DICOMTags().WAVE_FORMS)
    WAVE_FORMS_DICT = copy.deepcopy(DICOMTags().WAVE_FORMS_DICT)
    MEDIAN_BEATS_DICT = copy.deepcopy(DICOMTags().MEDIAN_BEATS_DICT)
    ECG_TRAIT_DICT = copy.deepcopy(DICOMTags().ECG_INTERPERTATION_DICT)
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
        path : str
            The path to the .dcm file.
        skip_empty : bool, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose : bool, default `False`
            Prints missing tags if skip_empty is set to `True`.
        
        Attributes
        ----------
        GeneralInfo : list [`str`]
            A list of dcmread extracted attributes.
        Waveforms : dict [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianWaveforms : dict [`str`, `np.array`]
            The lead specific ECG median beats.
        
        Returns
        -------
        self : `ECGDICOMReader` instance
            Returns the class instance with updated attributes extracted
            from `dcmread`.
        """
        is_type(path, (pathlib.PosixPath, str), 'path')
        is_type(skip_empty, bool, 'skip_empty')
        is_type(verbose, bool, 'verbose')
        # confirm file is readable
        _check_readable(path)
        # results dict for the tabular part
        results_dict = {}
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
                    results_dict[t] = getattr(ECG, s)
                elif skip_empty == False:
                    # Should an Error be returned
                    raise MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    results_dict[t] = np.nan
                    empty_metadata.append(s)
            # #### Extract waveforms
            try:
                nam, el = self.WAVE_FORMS_DICT[PDNames.WAVE_ARRAY]
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
                    results_dict[t] = getattr(WAVE, s)
                elif hasattr(SETTINGS, s):
                    results_dict[t] = getattr(SETTINGS, s)
                elif skip_empty == False:
                    # Should an Error be returned
                    raise MissingDICOMTagError(s)
                else:
                    # assign NA and append missing metadata
                    results_dict[t] = np.nan
                    empty_wave_forms.append(s)
                # Check number of channels in ECG waveform
            if results_dict[PDNames.CHANNEL_NUMBER] >= 8:
                channel_seq = getattr(getattr(ECG, PDNames.WAVE_FORM_SEQ)[0],
                                      PDNames.CHANNEL_DEF_SEQ)
                lead_info_waveform, lead_units=self._get_lead_info(channel_seq)
                setattr(self, PDNames.LEAD_VOLTAGES,
                        self.make_leadvoltages(
                            lead_info=lead_info_waveform,
                            waveform_array=getattr(self, PDNames.WAVE_ARRAY),
                            augment_leads=self.augment_leads,
                            ))
                results_dict[PDNames.LEAD_UNITS] = lead_units
                results_dict[PDNames.SAMPLING_FREQ] =\
                    results_dict[PDNames.SF_ORIGINAL]
                if self.retain_raw == False:
                    delattr(self, PDNames.WAVE_ARRAY)
            else:
                # set to NA
                setattr(self, PDNames.LEAD_VOLTAGES, np.nan)
                empty_wave_forms.append(PDNames.LEAD_VOLTAGES)
                results_dict[PDNames.SAMPLING_FREQ] =\
                    results_dict[PDNames.SF_ORIGINAL]
                results_dict[PDNames.LEAD_UNITS] = np.nan
            # #### Extract Median beats
            nam, el = self.MEDIAN_BEATS_DICT[PDNames.MEDIAN_ARRAY]
            # NOTE WAVE_FORM_SEQ is present because the code
            # above for the waveforms would have failed otherwise. So just
            # checking the number of elements - the median beats info should be
            # element 1 (i.e. len(x) == 2)
            try:
                sccss = True
                # note this is a method call
                getattr(ECG, nam)(el)
            except:
                sccss = False
            if sccss == True and len(getattr(ECG, PDNames.WAVE_FORM_SEQ)) == 2:
                # Assign if present
                channel_seq_median = getattr(
                    getattr(ECG, PDNames.WAVE_FORM_SEQ)[1],
                    PDNames.CHANNEL_DEF_SEQ)
                lead_info_median, lead_units2=\
                    self._get_lead_info(channel_seq_median)
                setattr(self, PDNames.MEDIAN_ARRAY,
                        getattr(ECG, nam)(el).T)
                setattr(self, PDNames.LEAD_VOLTAGES2,
                        self.make_leadvoltages(
                            lead_info=lead_info_median,
                            waveform_array=\
                            getattr(self, PDNames.MEDIAN_ARRAY),
                            augment_leads=self.augment_leads,
                            ))
                setattr(self, PDNames.MEDIAN_PRESENT, True)
                results_dict[PDNames.MEDIAN_PRESENT] = True
                results_dict[PDNames.LEAD_UNITS2] = lead_units2
            elif skip_empty == False:
                raise ValueError(Error_MSG.MISSING_DICOM.format(nam))
            else:
                # set to missing
                setattr(self, PDNames.MEDIAN_ARRAY, np.nan)
                setattr(self, PDNames.LEAD_VOLTAGES2, np.nan)
                setattr(self, PDNames.MEDIAN_PRESENT, False)
                results_dict[PDNames.MEDIAN_PRESENT] = False
                results_dict[PDNames.LEAD_UNITS2] = np.nan
            if self.retain_raw == False:
                delattr(self, PDNames.MEDIAN_ARRAY)
            # do we need to resample the freq
            if self.resample_500 == True:
                # the function will internally adjust
                # LEAD_VOLTAGES, and LEAD_VOLTAGES2
                # Nothing is returned
                self._resampling_500hz(frequency=results_dict[PDNames.SF])
                setattr(self, PDNames.OVERSAMPLED, True)
                results_dict[PDNames.OVERSAMPLED] = True
                results_dict[PDNames.SF] = 500
                results_dict[PDNames.SAMPLING_FREQ] = 500
            else:
                setattr(self, PDNames.OVERSAMPLED, False)
                results_dict[PDNames.OVERSAMPLED] = False
            # #### Extract standard ECG measurements
            temp_results_dict = {}
            temp_unit_dict = {}
            # first set everything to NA
            for e in self.ECG_TRAIT_DICT:
                results_dict[e] = np.nan
                results_dict[e+PDNames.ECG_UNIT_STRING] = np.nan
            # next see if we can extract some interpretations.
            if hasattr(ECG, PDNames.ECG_INTERPERTATION):
                # get the values lower-case strings (which are lists)
                ECG_CMPR_LWR = [it.lower() for sl\
                                in self.ECG_TRAIT_DICT.values() for it in sl]
                for w in getattr(ECG, PDNames.ECG_INTERPERTATION):
                    if hasattr(w, PDNames.ECG_CONCEPTNAME):
                        ecg_int = getattr(w, PDNames.ECG_CONCEPTNAME)[0]
                        try:
                            ecg_trait = getattr(ecg_int, PDNames.CODE_MEANING)
                            # find matching element - using lower case again
                            if ecg_trait.lower() in ECG_CMPR_LWR:
                                # get the measurement and set to float
                                temp_results_dict[ecg_trait.lower()] = float(
                                            getattr(w, PDNames.ECG_TRAIT_VALUE)
                                        )
                                # get the unit
                                try:
                                    temp_unit_dict[
                                        ecg_trait.lower()+\
                                        PDNames.ECG_UNIT_STRING]=getattr(
                                            getattr(w, PDNames.ECG_UNIT)[0],
                                            PDNames.CODE_MEANING)
                                except (AttributeError, IndexError):
                                    pass
                        except AttributeError:
                            pass
            # now assign temp_results_dict to results_dict dealing with
            # keys with more than one matching string.
            if len(temp_results_dict) > 0:
                for k, idx in self.ECG_TRAIT_DICT.items():
                    # Check if idx has more than one entry
                    # extract all entries and make sure they are the
                    # same  - NOTE using set comprehension to get the
                    # unique elements
                    unique_set = list({temp_results_dict[el.lower()] for el in\
                                       idx if el.lower() in temp_results_dict})
                    if len(unique_set) == 1:
                        # if only one unique entry simply assign this to k
                        for e in idx:
                            try:
                                results_dict[k] =\
                                    temp_results_dict[e.lower()]
                                results_dict[k+PDNames.ECG_UNIT_STRING] =\
                                    temp_unit_dict[
                                        e.lower()+PDNames.ECG_UNIT_STRING]
                            except KeyError:
                                # NOTE the KeyError is expected behaviour,
                                # some of the `e`'s will not be in the
                                # temp_results_dict
                                pass
                    elif len(unique_set) > 1:
                        # given that the results are not unique
                        # we will return all using the individual `idx` elements
                        # instead of `k` - NOTE the index without call to lower
                        # is intended.
                        for e in idx:
                            try:
                                results_dict[e] =\
                                    temp_results_dict[e.lower()]
                                results_dict[e+PDNames.ECG_UNIT_STRING] =\
                                    temp_unit_dict[
                                        e.lower()+PDNames.ECG_UNIT_STRING]
                            except KeyError:
                                pass
            # which ECG traits are still nan
            missing_ecg_traits = [k for k in self.ECG_TRAIT_DICT if\
                                  np.isnan(results_dict[k])]
            if skip_empty == False and len(missing_ecg_traits) > 0:
                # Should an Error be returned
                raise ValueError('The following ECG measurments are '
                                 'unavailable: {}'.format(missing_ecg_traits))
                                 
            else:
                # add missing metadata
                empty_metadata = empty_metadata + missing_ecg_traits
        # #### add duration,
        # NOTE both values are either int/float or NA so no need
        # for a try except
        results_dict[PDNames.DURATION] = (
            results_dict[PDNames.SAMPLING_NUMBER] /
            results_dict[PDNames.SAMPLING_FREQ]
        )
        # #### end of `dicom` part, optionally printing tags which were missing
        if verbose == True:
            if len(empty_metadata) + len(empty_wave_forms) > 0:
                warnings.warn(
                    'The following DICOM tags could not be found: {}.'.format(
                        empty_metadata + empty_wave_forms))
        # add time variables
        raw_AD = results_dict[PDNames.ACQUISITION_DATE]
        raw_SD = results_dict[PDNames.STUDY_DATE]
        results_dict[PDNames.ACQUISITION_DATE] = \
            datetime.strptime(raw_AD, self.ACQUISITION_DATE_SOURCE).\
            strftime(self.ACQUISITION_DATE_TARGET)
        results_dict[PDNames.STUDY_DATE] = \
            datetime.strptime(raw_SD, self.STUDY_DATE_SOURCE).\
            strftime(self.STUDY_DATE_TARGET)
        # #### assign results_dict
        setattr(self, PDNames.RESULTS_DICT, results_dict)
        # assign unique identifier
        setattr(self, PDNames.SOP_UID, results_dict[PDNames.SOP_UID])
        # add the original dcmread instance
        if self.retain_raw == True:
            setattr(self, PDNames.ORIG_DCMREAD_INST, ECG)
        # #### return stuff
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _get_lead_info(self, channel_seq: DCM_Class
                       ) -> tuple[dict[int, str], str]:
        """
        Extracts the lead names from a `dcmread` instance.
        
        Parameters
        ----------
        channel_seq : DCM_Class
            A `pydicom.sequence.Sequence` instance.
        
        Returns
        -------
        tuple of a dict and a string:
                
                - leadnames : dict [`int`, `str`]
                    A dictionary with numerical (interval) keys and the lead names as
                    values.
                - leadunit : str
                    The measurment unit of the ECG leads.
        """
        # #### extracting the lead names
        leadnames = {}
        leadunits = {}
        for k, channel in enumerate(channel_seq):
            # extracting lead names
            source = getattr(getattr(channel,PDNames.CHANNEL_SOURCE_SEQ)[0],
                             PDNames.CHANNEL_CODE_MEANING)
            # extracting units
            if hasattr(channel, PDNames.CHANNEL_SENS_UNIT):
                unit = getattr(
                    getattr(channel, PDNames.CHANNEL_SENS_UNIT)[0],
                    PDNames.CODE_MEANING)
            else:
                unit = np.nan
            # assign lead names to numericals
            leadnames[k] = source.replace(PDNames.LEAD, '').strip()
            leadunits[leadnames[k]] = unit
        # confirm the units are all the same
        unique_unit = list(set(leadunits.values()))
        if len(unique_unit) != 1:
            raise ValueError('The ECG leads were measured using different '
                             'units: `{}`.'.format(unique_unit))
        # return stuff
        return leadnames, unique_unit[0]
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
        waveform_array : np.ndarray
            An array with the waveforms.
        lead_info: dict [`int`, `str`]
            A dictionary where the keys match the `waveform_array` rows and
            the dictionary values contain the lead name strings.
        augment_leads : bool
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
    def _resampling_500hz(self, frequency:int|float):
        """
        Re-sample the frequency to 500 hz.
        
        Parameters
        ----------
        frequency : int or float
            The original sampling frequency. Will simply check that this is
            not 500 and if not proceed with the resampling.
        
        """
        if int(frequency) != 500:
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
    and maps these to which can be used in analyses or saved to disk.
    
    Attributes
    ----------
    RawPathList : list [`str`]
        A list of dcm file paths.
    
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
        skip_missing : `bool`, default `True`
            Whether missing files or files without read permissions should
            be skipped.
        verbose : `bool`, default `False`
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
        self : `ECGDICOMTable` instance
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
        # wave forms, and median beats
        setattr(self, PDNames.WAVE_T, self._get_long_table(
            wave_list, wave_type=PDNames.WAVETYPE_RHYTHM,
            update_keys=update_keys,
            purge_header=True,
        ))
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
        for w, k in zip(lead_list, getattr(self, PDNames.KEY_L)):
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
        table[PDNames.SAMPLING_SEQ] = table.groupby(
            PDNames.SOP_UID).cumcount()
        long_table = pd.melt(table, id_vars=\
                             [PDNames.SOP_UID, PDNames.SAMPLING_SEQ],
                             value_vars=getattr(self, PREV),
                             var_name=PDNames.COL_LEAD,
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
                    purge_header=True,
                ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=True, compression=compression)
                # median beats
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
                pd.DataFrame([info], index=[key]).to_csv(
                    os.path.join(target, PDNames.INFO_FILE), sep=sep,
                    header=False, mode='a', compression=compression)
                # waveforms
                self._get_long_table(
                    [wave], wave_type=PDNames.WAVETYPE_RHYTHM,
                    update_keys=update_keys,
                    purge_header=False,
                ).to_csv(
                        os.path.join(target, PDNames.WAVE_FILE), sep=sep,
                        header=False, mode='a', compression=compression)
                # median beats
                self._get_long_table(
                    [median], wave_type=PDNames.WAVETYPE_MEDIAN,
                    update_keys=update_keys,
                    purge_header=False,
                ).to_csv(
                        os.path.join(target, PDNames.MEDIAN_FILE), sep=sep,
                        header=False, mode='a', compression=compression)
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


# # standard A4 size in mm - landscape!
# paper_w = 297.0
# paper_h = 210.0
# # Dimensions in mm of plot area
# width = 250.0
# height = 170.0
# margin_left =  .5 * (paper_w - width)
# # margin_right = .5 * (paper_w - width)
# margin_bottom = 10.0
# # Normalized in [0, 1]
# left = margin_left / paper_w
# right = left + width / paper_w
# bottom = margin_bottom / paper_h
# top = bottom + height / paper_h
# # The grid constants
# color = {'minor': '#ff5333', 'major': '#d43d1a'}
# linewidth = {'minor': .1, 'major': .2}
# inch_mm = 24.5
# layout= [['I', 'aVR', 'V1', 'V4'],
#          ['II', 'aVL', 'V2', 'V5'],
#          ['III', 'aVF', 'V3', 'V6'],
#          ['II']]
# ecg_signal=getattr(ecgdicomreader, PDNames.LEAD_VOLTAGES)
# plt.ion()
# # #### using a default A4 landscape page
# f, axes = plt.subplots(figsize=(paper_w/inch_mm,
#                                 paper_h/inch_mm))
# # set the canvas
# f.subplots_adjust(left=left, right=right, top=top,
#                     bottom=bottom)
# # set the plotting axis
# axes.set_ylim([0, height])
# axes.set_ylim([0, 5000])
# # set to self
# fig = f
# ax = axes

# from ecgprocess.example_data.examples import (
#     list_data_paths,
# )
# verbose=False
# skip_empty=True
# path = list_data_paths()['example_dicom_1']
# ecgdicomreader = ECGDICOMReader()
# ecgdicomreader = ecgdicomreader(path=path, skip_empty=skip_empty,
#                                verbose=verbose)
# plt.ion()
# artist = ECGDICOMDrawing()
# f, axes = plt.subplots(figsize=(20, 4))

# test = artist(ecgdicomreader, add_grid=True, minor_axis=False,
#               ax=axes)
# set2 = set(dir(test))
# set2-set1

# # artist._set_canvas()
# # artist._draw_grid()
# # artist._draw_signal()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# NOTE add tests
# NOTE add a numpy method - mapping a matplotlib illustration to a numpy array.
class ECGDICOMDrawing(object):
    '''
    Takes a called `ECGDICOMReader` instance and plots the lead-specific
    ECG signals.
    
    Attributes
    ----------
    mm_mv : `float`, default 10
        The scaling factor applied to the ECG signals, mapping these from
        1mm/mV to mm_vv * mm/mv.
    paper_w : `float`, default 297 mm
        The figure width.
    paper_h : `float`
        The figure height, default 210 mm
    width : `float`
        The plotting area width, default 250 mm
    height : `float`
        The plotting area height, default 170 mm
    grid_color : `dict` {`minor`: colour_1, `major`: color_2}
        The grid line colours.
    grid_linewidth : `dict`
        The grid line width.
    text_pad_x : `float`, default 40
        Padding of the text x-axis coordinate.
    
    Notes
    -----
    Calling the class instance will check the ECG unit, and if needed convert
    microvolts (µV) to millivolts (mV).
    
    '''
    
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self) -> None:
        """
        Initialises a new instance of `ECGDICOMDrawing`.
        """
        # scaling factor for 1/mV to FACTOR/mV
        setattr(self, PDNames.WAVE_SCALING, 10)
        # #### set sensible plotting defaults matching an actual ECG printout
        self.inch_mm = 24.5
        # standard A4 size in mm - landscape!
        self.paper_w = 297.0
        self.paper_h = 210.0
        # Dimensions in mm of plot area
        self.width = 250.0
        self.height = 170.0
        # The grid constants
        self.grid_color = {'minor': '#ff5333', 'major': '#d43d1a'}
        self.grid_linewidth = {'minor': .1, 'major': .2}
        # the text constants
        self.text_pad_x = 40
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME} instance with "
                f"ecgdicomreader={self.ecgdicomreader}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        CLASS_NAME = type(self).__name__
        return (f"{CLASS_NAME}(ecgdicomreader={self.ecgdicomreader})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, ecgdicomreader:ECGDICOMReader,
                 wave_type:Literal['rhythm', 'median']='rhythm',
                 add_grid:bool=False, minor_axis:bool=True,
                 image_layout:list[list[str]] | None=None,
                 auto_margins:bool=True,
                 verbose:bool=True,
                 ax:plt.Axes | None=None,
                 ) -> Self:
        '''
        Creates an ECG drawing using either the waveforms `rhythm` or the median
        beats signals.
        
        Parameters
        ----------
        ecgdicomreader : ECGDICOMReader
            An instance of the `ECGDICOMReader` data class that has already
            been called to process the ECG data.
        wave_type : {'rhythm', 'median'}, default `rhythm`
            The type of ECG signal to plot.
        add_grid : `bool`, default `False`
            Whether to annotate the ECG image with a canonical grid (with small
            squares indicating 0.04 seconds (x-axis) and 0.1 mV (y-axis) and
            the larger squares a 5 multiple. Depending on the intended
            deployment setting and the applied pre-processing you may want to
            remove the grid.
        minor_axis: `bool`, default `True`
            Whether to add the minor grid axes.
        image_layout : `list` [`list` [`str`]]
            A nested lists organising the image by ECG lead names.
        ax : plt.Axes, default `NoneType`
            An optional `matplotlib.axes.Axes` instance on which the ECG
            signals are plotted. If ommited will simply take an A4 x/y axes
            aspect ratio and mimic a cononical ECG image.
            canonical ECG image (using an A4 size y and x-axis aspect ratio).
        verbose : `bool`, default `False`
            Prints missing files if skip_missing is set to `True`.
        
        Attributes
        ----------
        ecg_signal : `dict` [`str`, `np.ndarray`]
            The ECG signals depicted in the figure. Organised as a dictionary
            with keys matching the lead name and np.ndarray as values recording
            the ECG measurement.
        ecg_unit : `str`
            The measurement unit - should be `millivolt`. Included here for
            checking/debugging.
        image_layout : `list` [`list` [`str`]]
            A nested lists organising the image by ECG lead names.
        wave_type : `str`
            The type of ECG signal.
        fig : `plt.figure`
            The matplotlib figure.
        ax : `plt.axes`
            The matplotlib axes.
        
        Returns
        -------
        self : `ECGDICOMDraw` instance
            Returns the class instance with updated attributes.
        '''
        # constants
        WARN1 = ('The Waveform unit is unavailable. Assuming '
                 f'measurements were in {PDNames.MILLIVOLT}.')
        WARN2 = ('The Waveform unit is not recognised: `{}`. Assuming '
                 f'measurements were in {PDNames.MILLIVOLT}.')
        # check input and assign to self
        is_type(verbose, bool)
        is_type(wave_type, str)
        is_type(add_grid, bool)
        is_type(minor_axis, bool)
        is_type(ax, (type(None), plt.Axes))
        is_type(image_layout, (type(None), list))
        self.verbose = verbose
        setattr(self, PDNames.WAVE_TYPE, wave_type)
        WAVE_TYPE = [PDNames.WAVETYPE_RHYTHM,
                    PDNames.WAVETYPE_MEDIAN,
                    ]
        if not getattr(self, PDNames.WAVE_TYPE) in WAVE_TYPE:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('wave_type', ', '.join(WAVE_TYPE)))
        if image_layout is None:
            image_layout = [
                ['I', 'aVR', 'V1', 'V4'],
                ['II', 'aVL', 'V2', 'V5'],
                ['III', 'aVF', 'V3', 'V6'],
                ['II'],
            ]
        setattr(self, PDNames.PLOT_LAYOUT, image_layout)
        # #### get ecg data
        self.ecgdicomreader = ecgdicomreader
        if getattr(self, PDNames.WAVE_TYPE) == PDNames.WAVETYPE_RHYTHM:
            setattr(self, PDNames.ECG_SIGNAL,
                    getattr(self.ecgdicomreader, PDNames.LEAD_VOLTAGES)
                    )
        else:
            setattr(self, PDNames.ECG_SIGNAL,
                    getattr(self.ecgdicomreader, PDNames.LEAD_VOLTAGES2)
                    )
        # #### convert microvolts (µV) to millivolts (mV)
        try:
            unit = getattr(self.ecgdicomreader,
                           PDNames.RESULTS_DICT)[PDNames.LEAD_UNITS]
        except KeyError:
            try:
                unit = getattr(self.ecgdicomreader,
                               PDNames.RESULTS_DICT)[PDNames.LEAD_UNITS2]
            except KeyError:
                warnings.warn(WARN1)
                unit = PDNames.MILLIVOLT
        if unit == PDNames.MICROVOLT:
            setattr(self, PDNames.ECG_SIGNAL,
                    {k:v/1000 for k,v in\
                     getattr(self, PDNames.ECG_SIGNAL).items()}
                    )
            pass
        elif unit == PDNames.MILLIVOLT:
            # already correct units
            pass
        else:
            warnings.warn(WARN2.format(unit))
        # raise warning if unit is not helpful
        if unit is None or pd.isna(unit):
            warnings.warn(WARN2)
        # add unit
        setattr(self, PDNames.PLOT_UNIT, unit)
        # #### extract additional meta data
        # sampling number
        setattr(self, PDNames.SAMPLING_NUMBER,
                getattr(ecgdicomreader, PDNames.RESULTS_DICT)[
                    PDNames.SAMPLING_NUMBER])
        # #### create figure
        self._set_canvas(auto_margins=auto_margins, ax=ax)
        if add_grid == True:
            self._draw_grid(minor_axis=minor_axis)
        # #### draw ecg signal
        self._draw_signal(layout=getattr(self, PDNames.PLOT_LAYOUT))
        # #### return self
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _set_canvas(self, auto_margins:bool=True,
                    ax:plt.Axes | None=None,
                    kwargs_subplots:dict[Any, Any] | None=None,
                    kwargs_subplots_adjust:dict[Any, Any] | None=None,
                    ) -> None:
        '''
        Creates the matplotlib figure and axes objects and assigns this to the
        class instance.
        
        Parameters
        ----------
        auto_margins : `bool`, default `True`
            Whether the margins should be calculated based on the supplied
            figure and plotting area dimensions.
        ax : plt.Axes, default `NoneType`
            An optional `matplotlib.axes.Axes` instance on which the ECG
            signals are plotted. If ommited will simply take an A4 x/y axes
            aspect ratio and mimic a cononical ECG image.
            canonical ECG image (using an A4 size y and x-axis aspect ratio).
        kwargs_*_dict : `dict` [`any`, `any`], default `NoneType`
            Optional arguments supplied to the various plotting functions:
                kwargs_subplots         --> plt.subplots
                kwargs_subplots_adjust  --> figure.subplots_adjust
        
        Attributes
        ----------
        fig : `plt.figure`
            The matplotlib figure.
        ax : `plt.axes`
            The matplotlib axes.
        '''
        is_type(ax, (type(None), plt.Axes))
        is_type(auto_margins, bool)
        # ### settings empty dict defaults
        kwargs_subplots, kwargs_subplots_adjust = assign_empty_default(
            [kwargs_subplots, kwargs_subplots_adjust], dict)
        # #### set canvas
        if ax is None:
            # using a default A4 landscape page
            f, axes = plt.subplots(**kwargs_subplots)
        else:
            # assign ax and its figure
            axes = ax
            f = ax.figure
            # update height and width with the ax properties
            pos = axes.get_position()
            _, _, width_n, height_n = pos.bounds
            # Get the figure dimensions in inches
            fig_width, fig_height = f.get_size_inches()
            # Convert normalized dimensions to inches
            setattr(self, PDNames.PLOT_WIDTH,
                    np.round(width_n * fig_width * self.inch_mm))
            setattr(self, PDNames.PLOT_HEIGHT,
                    np.round(height_n * fig_height * self.inch_mm))
        # calculate marings
        if auto_margins == True:
            margin_left =  .5 * (self.paper_w -
                                 getattr(self, PDNames.PLOT_WIDTH))
            # margin_right = .5 * (paper_w - width)
            margin_bottom = 10.0
            # Normalized in [0, 1]
            self.left = margin_left / self.paper_w
            self.right = self.left +\
                getattr(self, PDNames.PLOT_WIDTH)/self.paper_w
            self.bottom = margin_bottom / self.paper_h
            self.top = self.bottom + self.height / self.paper_h
            # apply margins
            new_kwargs_adjust = _update_kwargs(
                update_dict=kwargs_subplots_adjust,
                left=self.left,
                right=self.right,
                top=self.top,
                bottom=self.bottom,
            )
            f.subplots_adjust(**new_kwargs_adjust)
        # set the plotting axis
        axes.set_ylim([0, getattr(self, PDNames.PLOT_HEIGHT)])
        # axes.set_ylim([0, 5000])
        axes.set_xlim([0, getattr(self, PDNames.SAMPLING_NUMBER) - 1])
        # set to self
        self.fig = f
        setattr(self, PDNames.PLOT_AXES, axes)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _draw_grid(self, minor_axis:bool=True) -> None:
        '''
        Draws the minor and major grid lines of an ECG image.
        
        Parameters
        ----------
        minor_axis : `bool`, default `True`
            Whether the minor grid lines should be drawn.
        '''
        # do we want to add minor axes - these should have a stepsize of 1 in
        # ECG images
        if minor_axis == True:
            getattr(self, PDNames.PLOT_AXES).xaxis.set_minor_locator(
                plt.LinearLocator(int(self.width + 1))
            )
            getattr(self, PDNames.PLOT_AXES).yaxis.set_minor_locator(
                plt.LinearLocator(int(getattr(self, PDNames.PLOT_HEIGHT)+ 1))
            )
        # annotating the major axes - these should have a stepsize of 5 in
        # ECG images
        getattr(self, PDNames.PLOT_AXES).xaxis.set_major_locator(
            plt.LinearLocator(int(self.width / 5 + 1))
        )
        getattr(self, PDNames.PLOT_AXES).yaxis.set_major_locator(
            plt.LinearLocator(int(getattr(self, PDNames.PLOT_HEIGHT)/ 5 + 1))
        )
        for a in 'x', 'y':
            for which in 'major', 'minor':
                getattr(self, PDNames.PLOT_AXES).grid(
                    which=which,
                    axis=a,
                    linestyle='-',
                    linewidth=self.grid_linewidth[which],
                    color=self.grid_color[which]
                )
                getattr(self, PDNames.PLOT_AXES).tick_params(
                    which=which,
                    axis=a,
                    color=self.grid_color[which],
                    bottom=False,
                    top=False,
                    left=False,
                    right=False
                )
    # /////////////////////////////////////////////////////////////////////////
    def _draw_signal(self, layout:list[list[str]],
                     figsize:tuple[float, float] | None=None,
                     kwargs_signal:dict[Any, Any] | None=None,
                     kwargs_text:dict[Any, Any] | None=None,
                     ) -> None:
        '''
        Draws ECG signals on a matplotlib axis.
        
        Parameters
        ----------
        layout : `list` [`list` [`str`]]
            A nested lists organising the image by ECG lead names.
        figsize : `tuple` (`floa`, `float`), default `NoneType`
            The width by height figure size in inches. If `NoneType` it will
            use the self.paper_h and self_paper_w attributes which are
            defined in millimetres divided by self.inch_mm.
        kwargs_*_dict : `dict` [`any`, `any`], default `NoneType`
            Optional arguments supplied to the various plotting functions:
                kwargs_signal        --> ax.plot
                kwargs_text          --> ax.text
        '''
        # #### check input
        is_type(layout, (type(None), list))
        is_type(figsize, (type(None), tuple))
        setattr(self, PDNames.PLOT_LAYOUT, layout)
        # check an axis is available
        if hasattr(self, PDNames.PLOT_AXES) == False:
            raise NotCalledError('The `_set_canvas` method has not been '
                                 'Called. There is no axes to draw on.')
        # confirm layout matches the signal.keys
        flat_layout = [l for s in getattr(self, PDNames.PLOT_LAYOUT) for l in s]
        msg_elements = [l for l in flat_layout if l not in\
                        getattr(self, PDNames.ECG_SIGNAL)]
        if msg_elements:
            raise KeyError(f"The following `layout` entries are unavailable "
                           f"in the waveform dictionary: {msg_elements}. "
                           f"The dictionary keys are: "
                           f"{list(getattr(self, PDNames.ECG_SIGNAL))}.")
        # set some default
        if figsize is None:
            figsize=(self.paper_w/self.inch_mm, self.paper_h/self.inch_mm)
        setattr(self, PDNames.PLOT_FIGSIZE, figsize)
        # map None to dict
        kwargs_signal, kwargs_text = assign_empty_default(
            [kwargs_signal, kwargs_text], dict)
        # #### sort out the ploting areas (note not using gridspecs currently)
        rows = len(getattr(self, PDNames.PLOT_LAYOUT))
        for numrow, row in enumerate(getattr(self, PDNames.PLOT_LAYOUT)):
            columns = len(row)
            row_height = getattr(self, PDNames.PLOT_HEIGHT) / rows
            # Horizontal shift for lead labels and separators
            h_delta = getattr(self, PDNames.SAMPLING_NUMBER)/ columns
            # Vertical shift of the origin
            v_delta = round(
                getattr(self, PDNames.PLOT_HEIGHT) * (1.0 - 1.0 / (rows * 2)) -
                numrow * (getattr(self, PDNames.PLOT_HEIGHT) / rows)
            )
            # Let's shift the origin on a multiple of 5 mm
            v_delta = (v_delta + 2.5) - (v_delta + 2.5) % 5
            # Lenght of a signal chunk
            chunk_size = int(getattr(self, PDNames.SAMPLING_NUMBER) / len(row))
            # ### actually plot the signals
            for numcol, k in enumerate(row):
                left = numcol * chunk_size
                right = (1 + numcol) * chunk_size
                # The signal chunk, vertical shifted and
                # scaled by mm/mV factor
                signal = v_delta + getattr(self, PDNames.WAVE_SCALING) *\
                    getattr(self, PDNames.ECG_SIGNAL)[k][left:right]
                # update kwargs
                new_kwargs_signal = _update_kwargs(
                    update_dict=kwargs_signal,
                    clip_on=False,
                    linewidth=0.6,
                    color='black',
                    zorder=2,
                )
                # plot the signal
                getattr(self, PDNames.PLOT_AXES).plot(
                    list(range(left, right)),
                    signal,
                    **new_kwargs_signal,
                    )
                # update kwargs
                new_kwargs_text = _update_kwargs(
                    update_dict=kwargs_text,
                    zorder=3,
                    fontsize=8,
                )
                # plot the lead name
                h = h_delta * numcol
                # v = v_delta + row_height / 2.6
                getattr(self, PDNames.PLOT_AXES).text(
                    x=h + self.text_pad_x,
                    y=v_delta + row_height / 3,
                    s=k,
                    **new_kwargs_text,
                )
            # remove the tick labels
            getattr(self, PDNames.PLOT_AXES).set_xticklabels([])
            getattr(self, PDNames.PLOT_AXES).set_yticklabels([])
            # resize figure
            self.fig.set_size_inches(figsize)


