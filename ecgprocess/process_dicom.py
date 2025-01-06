'''
A module for extracting metadata, median beats, and raw waveforms from ECG
DICOM files.

This module provides an API through a reader class, which maps ECG data from
DICOM files to class attributes. These attributes can be programmatically accessed
and further processed by downstream ECGprocess modules or external programs
leveraging the API.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import pathlib
import pydicom
import warnings
import numpy as np
import pandas as pd
import ecgprocess.utils.ecg_tools as ecg_utils
import ecgprocess.utils.reader_tools as reader_utils
from ecgprocess.process_xml import ECGXMLReader
from dataclasses import dataclass, field
from typing import (
    Self, Dict, Any, Optional
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    Warn_MSG,
    _check_readable,
    MissingTagError,
)
from ecgprocess.utils.general import(
    parse_number,
    string_concat,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    FixedReaderNames as FRNames,
    CoreData as Core,
    DICOMTags,
)
from ecgprocess.utils.reader_tools import(
    BaseReader,
)
from ecgprocess.utils.general import(
    ManagedProperty,
)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CProc = Core.ProcessingData
CMeta = Core.MetaData
CLeads = Core.Leads

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGDICOMReader(ECGXMLReader):
    """
    Processes an DICOM file containing ECG data and extracts the metadata,
    median beats, and raw waveforms.
    
    Parameters
    ----------
    augment_leads : `bool`, default `False`
        Whether the augmented leads should be calculated if these are not
        already available in the source file.
    resample : `bool`, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
    
    Methods
    -------
    extract(config, skip_empty, parse_numeric, **kwargs)
        Processes the DICOM file content applying optional lead augmentation
        and resampling. The DICOM content will be mapped to class attributes.
    
    """
    # #### properties
    tags = ManagedProperty(CProc.TAGS, list)
    raw_data = ManagedProperty(CProc.RAW, dict)
    _as_array:bool = True
    # #### parameters, with defaults
    augment_leads:bool = field(default=False)
    resample_500:bool = field(default=True)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __post_init__(self):
        """Validating inputs."""
        is_type(getattr(self, PDNames.AUG_LEADS), bool)
        is_type(getattr(self, PDNames.RESAMPLE), bool)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, verbose:bool=False,
                 **kwargs:Optional[Any],
                 ) -> Self:
        """
        Reads an `.dcm` file containing ECG readings.
        
        Parameters
        ----------
        path : `str`
            The path to a .dcm file.
        verbose : `bool`, default `False`
            Whether warnings and process info should be printed.
        **kwargs : any
            keyword arguments passed to flatten_dict.
        
        Attributes
        ----------
        tags : `list` [`str`]
            A list of strings with parsed tags matching the `raw_data` keys.
        raw_data : `dict` [`str`, `any`]
            The raw parsed data.
        
        Returns
        -------
        self : `ECGDICOMReader` instance
            Returns the class instance with updated attributes including the
            extracted DICOM data.
        """
        # #### check input
        is_type(path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(verbose, bool)
        # #### assign to self
        self.verbose = verbose
        # #### confirm file is readable
        _check_readable(path)
        # #### read dicom file
        try:
            ds = pydicom.dcmread(path)
        except pydicom.errors.InvalidDicomError as e:
            raise ValueError(f"Failed to read DICOM file at {path}: {e}")
        # map to flatten_dict
        dicom_dict = reader_utils.flatten_dict(
            reader_utils.dicom_to_dict(ds),
            skip_root=False,
            **kwargs,
        )
        # ### store keys and data
        getattr(type(self), CProc.RAW).set_with_setter(self, dicom_dict)
        getattr(type(self), CProc.TAGS).set_with_setter(
            self, list(dicom_dict.keys()))
        # ### return
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def extract(self, config:ConfigParser, bits:np.dtype | None =None,
                skip_empty:bool=True, parse_numeric:bool=True,
                pattern:dict[str, str]|None=None,
                substitute:tuple[str,str]|None=(r'_[0-9]{1,2}\.*', ' '),
                character_trim:int=0,
                **kwargs:Optional[Any]) -> Self:
        """
        Processes the raw ECG data and assign these to class attributes
        performing resampling and lead augmentation if requested.
        
        Parameters
        ----------
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the DICOM
            content to class attributes. Specifically this should include
            dictionary attributes `MetaData`, `WaveForms`, `MedianBeats`,
            `OtherData`. The `MetaData` includes some privileged keys including
            essential information to describe an ECG instance, as well as
            non-privileged  information. The difference between `OtherData` and
            `MetaData` is the way it is processed by other functions or methods
            with the `OtherData` processed without strong checks on its content.
            `WaveForms` and `MedianBeats` simply include the lead mappings.
            Please refer to the `constants.CoreData` class for the specifics
        parse_numeric : bool, default `True`
            Whether to check for numeric data accidentally recorded as string and
            try to parse these to int or float depending on the presence of a
            decimal separator.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        bits : `np.dtype`, default `None`
            np.array bits passed to numpy.array dtype.
        pattern : `dict` [`str`, `str`], default `NoneType`
            Use this to extract a subset of items from `MetaData` based on the
            pattern key, and adds a unique name as a prefix to the keys of the
            selected subset. The unique name will be base on the value from the
            key which matches the pattern value.
        substitute : `tuple` [`str`,`str`] or `None`, default `(r"_[0-9]{1,2}\\.*", " ")`
            A tuple containing a regular expression pattern and replacement string.
            This substitution is applied to the remaining portion of the `data` key
            after removing the matching prefix.
        character_trim : int, default `0`
            The number of charecters which should be removed from the right-hand
            side of the `data` key which did not match the `pattern` key.
        **kwargs
            The keyword arguments for reader_tools.get_ecg_data.
            For the waveforms and medianbeats as_array and bits are hard coded
            so these will raise an error if supplied as kwargs.
        
        Attributes
        ----------
        MetaData : `dict` [`str`, `any`]
            ECG metadata.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianBeats : `dict` [`str`, `np.array`]
            The lead specific ECG median beats.
        OtherData : `dict` [`str`, `any`]
            Other data.
        
        Returns
        -------
        self : `ECGDICOMReader` instance
            Returns the class instance with updated attributes including the
            extracted DICOM data.
        """
        # #### run ECGXMLReader.extract
        super().extract(config=config, skip_empty=skip_empty,
                        parse_numeric=parse_numeric, **kwargs)
        # #### extract based on a string pattern
        if not pattern is None:
            new_meta = reader_utils.subset_dict(
                data=getattr(self, CProc.RAW), pattern=pattern,
                substitute=substitute, verbose=self.verbose,
                skip_empty=skip_empty,
                character_trim=character_trim)
            # make sure everything is af loat add perform optional mapping
            # to numeric
            new_meta = {k:str(v) for k, v in new_meta.items()}
            if parse_numeric:
                for k, v in new_meta.items():
                    try:
                        new_meta[k] = parse_number(v)
                        if isinstance(new_meta[k], list):
                            if len(new_meta[k]) == 1:
                                new_meta[k] = new_meta[k][0]
                    except ValueError:
                        new_meta[k] = v
            # assign to meta
            getattr(self, CTypes.MetaData).update(new_meta)
        # #### return
        return self

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class FixedDICOMReader(BaseReader):
    """
    Takes an ECG DICOM file and extracts metadata, median beats (if available)
    and raw waveforms.
    
    Parameters
    ----------
    augment_leads : `bool`, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample : `bool`, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    retain_raw : `bool`, default `False`
        Whether the raw pydicom instance and raw waveforms should be retained.
        Set to `False` to decrease memory usage. Set to `True` to explore the
        orignal pydicom instance. For example, use this one a few files to
        identify none-standard information to extract.
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
    retain_raw : `bool`
        Whether the raw pydicom data was retained.
    METADATA : `dict` [`str`, `str`]
        A dictionary describing the metadata one wants to extract from a
        DICOM. The dictionary keys represents the `target` (new) name and the
        dictionary values the `source` (old) names.
    ECG_TRAIT_DICT : `dict` [`str`, `list[str]`]
        A dictionary with the keys reflecting the desired name of the ECG trait.
        Each key will have a list of strings as a value. These strings will be
        compared to the names in `WaveformAnnotationSequence` attribute.
        Matching is done without case-sensitivity.  If for any key there are
        multiple matching strings the algorithm will check if the extracted
        values are all the same, if not multiple entries will be returned for
        the user to decide what to do next. The extracted ECG traits will be
        included with the extracted METADATA.
    
    Methods
    -------
    get_metadata(path, skip_empty)
        Extract the dicom metadata.
    make_leadvoltages(waveform_array, lead_info, augment_leads)
        Extracts the voltages from a DICOM file. Will automatically extract the
        limb leads if missing.
    
    Notes
    -----
    While the type of information that is extracted by this class is relatively
    extensive and can be axpanded through for example `METADATA`, the
    pydicom attributes which these data can be extracted from are fixed. This
    therfore provides a less flexible solution than FixedDICOMReader.
    """
    warnings.warn(
        "'FixedDICOMReader' will be deprecated in a future version. "
        "Please use 'ECGDICOMReader' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # #### parameters, with defaults
    augment_leads: bool=False
    resample_500:bool=True
    retain_raw:bool=False
    # #### check input
    is_type(augment_leads, bool, 'augment_leads')
    is_type(resample_500, bool, 'resample_500')
    # #### default tags
    METADATA:dict = field(default_factory=lambda: DICOMTags().METADATA)
    WAVE_FORMS:dict = field(default_factory=lambda: DICOMTags().WAVE_FORMS)
    MEDIAN_BEATS:dict = field(default_factory=lambda: DICOMTags().MEDIAN_BEATS)
    ECG_TRAIT_DICT:dict =\
        field(default_factory=lambda: DICOMTags().ECG_INTERPERTATION_DICT)
    # #### Error MSG
    __MSG1=Error_MSG.MISSING_PATH_INSTANCE.format('dicom_instance')
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
        path : `str`
            The path to the .dcm file.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose : `bool`, default `False`
            Prints missing tags if skip_empty is set to `True`.
        
        Attributes
        ----------
        GeneralInfo : `list` [`str`]
            A list of dcmread extracted attributes.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianWaveforms : `dict` [`str`, `np.array`]
            The lead specific ECG median beats.
        
        Returns
        -------
        self : `FixedDICOMReader` instance
            Returns the class instance with updated attributes extracted
            from `dcmread`.
        """
        is_type(path, (pathlib.PosixPath, pathlib.WindowsPath, str), 'path')
        is_type(skip_empty, bool, 'skip_empty')
        is_type(verbose, bool, 'verbose')
        self.verbose=verbose
        # confirm file is readable
        _check_readable(path)
        # #### Read DICOM
        ECG, results_dict, empty_metadata = self.get_metadata(
            path, skip_empty=skip_empty)
        # #### Extract waveforms
        _, wave_dict, empty_wave_forms = self.get_waveforms(
            dicom_instance=ECG, skip_empty=skip_empty)
        results_dict.update(wave_dict)
        # #### Extract Median beats
        _, median_dict, empty_median_beats = self.get_median_beats(
            dicom_instance=ECG, skip_empty=skip_empty)
        results_dict.update(median_dict)
        # #### add duration,
        try:
            results_dict[CProc.Duration] = (
                results_dict[CMeta.SN_W] /
                results_dict[CMeta.SF]
            )
        except TypeError:
            results_dict[CProc.Duration] = None
        # #### do we need to resample
        results_dict[CProc.SF_NEW] = None
        if self.resample_500 == True:
            # confirm SF is present
            if not CMeta.SF in results_dict or results_dict[CMeta.SF] is None:
                raise KeyError(f'`{CMeta.SF}` is necessary to resample '
                               'the ECG signal.')
            # if it is, check whether there is a need to resample the signals.
            if int(results_dict[CMeta.SF]) != 500 and\
                    not results_dict[CProc.Duration] is None:
                # update the waveforms
                if not getattr(self, CTypes.WaveForms) is None:
                    wave_dict = ecg_utils.resampling_500hz(
                        wave_dict, duration=results_dict[CProc.Duration])
                    setattr(self, CTypes.WaveForms, wave_dict)
                if not getattr(self, CTypes.MedianBeats) is None:
                    median_dict = ecg_utils.resampling_500hz(
                        median_dict, duration=results_dict[CProc.Duration],
                        median=True)
                    setattr(self, CTypes.MedianBeats, median_dict)
                results_dict[CProc.SF_NEW] = 500
        # #### Extract standard ECG measurements
        _, ecg_traits, missing_ecg_traits = self._get_waveform_annotation(
            dicom_instance=ECG, skip_empty=skip_empty)
        results_dict.update(ecg_traits)
        empty_metadata = empty_metadata + missing_ecg_traits
        # #### end of extractions, optionally printing tags which were missing
        if verbose == True:
            if len(empty_metadata) + len(empty_wave_forms) +\
                    len(empty_median_beats)> 0:
                warnings.warn(
                    'The following DICOM tags could not be found: {}.'.format(
                        empty_metadata + empty_wave_forms +\
                    empty_median_beats))
        # #### assign results_dict
        setattr(self, CTypes.MetaData, results_dict)
        # add the original dcmread instance
        if self.retain_raw == True:
            setattr(self, FRNames.ORIG_DCMREAD_INST, ECG)
        # #### return stuff
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def get_metadata(self, path:str|None=None,
                     dicom_instance:pydicom.dataset.FileDataset|None=None,
                     skip_empty:bool=True
                     ) -> tuple[pydicom.dataset.FileDataset, dict[str, Any],
                                list[str]]:
        '''
        Takes a dicom file and extracts its metadata
        
        Parameters
        ----------
        path : `str`, default `NoneType`.
            The path to the .dcm file.
        dicom_instance : `DCM_Class`, default `NoneType`.
            A DCM_Class instance.
        
        Returns
        -------
        dict,DCM_Class
            - A `DCM_Class` instance.
            - A dictionary with extracted metadata.
            - A list of missing `DCM_Class` attribute names.
        
        Notes
        -----
        Either supply a path to a dicom file or a DCM_Class instance
        '''
        # #### check input
        is_type(path, (type(None), pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(dicom_instance, (type(None), pydicom.dataset.FileDataset))
        is_type(skip_empty, bool)
        results_dict = {}
        if (not dicom_instance is None) and (not path is None):
            raise ValueError(self.__MSG1)
        # #### Read DICOM
        if not path is None:
            with open(path, 'rb') as dicom:
                # reads standard dicom content
                ECG=pydicom.dcmread(dicom)
        else:
            ECG=dicom_instance
        # #### extract metadata
        empty_metadata = []
        for t, s in self.METADATA.items():
            if hasattr(ECG, s):
                # Assign if present
                results_dict[t] = getattr(ECG, s)
            elif skip_empty == False:
                # Should an Error be returned
                raise MissingTagError(s)
            else:
                # assign NA and append missing metadata
                results_dict[t] = np.nan
                empty_metadata.append(s)
        # return
        return ECG, results_dict, empty_metadata
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def get_waveforms(self, path:str|None=None,
                     dicom_instance: pydicom.dataset.FileDataset|None=None,
                     skip_empty:bool=True
                     ) -> tuple[pydicom.dataset.FileDataset,
                                dict[str, Any], list[str]]:
        '''
        Takes a dicom file and extracts the waveforms and waveform metadata.
        
        Parameters
        ----------
        path : `str`, default `NoneType`.
            The path to the .dcm file.
        dicom_instance : `DCM_Class`, default `NoneType`.
            A DCM_Class instance.
        
        Returns
        -------
        results : dict,DCM_Class
            - A `DCM_Class` instance.
            - A dictionary with extracted metadata.
            - A list of missing `DCM_Class` attribute names.
        
        Notes
        -----
        Either supply a path to a dicom file or a DCM_Class instance
        '''
        # #### check input
        is_type(path, (type(None), pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(dicom_instance, (type(None), pydicom.dataset.FileDataset))
        is_type(skip_empty, bool)
        temp_results_dict = {}
        if (not dicom_instance is None) and (not path is None):
            raise ValueError(self.__MSG1)
        # #### constants
        LEAD_UNITS = 'WaveformUnits'
        WAVE_FORM_ARR = 'waveform_array'
        # #### Read DICOM
        # NOTE `with` closes automatically if an error is raised
        if not path is None:
            with open(path, 'rb') as dicom:
                # reads standard dicom content
                ECG=dcmread(dicom)
        else:
            ECG=dicom_instance
        # #### extract waveforms
        try:
            WAVE_TEMP = getattr(ECG, WAVE_FORM_ARR)(0).T
        except:
            raise AttributeError(Error_MSG.MISSING_DICOM.format(WAVE_FORM_ARR))
        WAVE = getattr(ECG, FRNames.WAVE_FORM_SEQ)[0]
        SETTINGS = getattr(WAVE, FRNames.CHANNEL_DEF_SEQ)[0]
        # #### Extract waveform metadata
        empty_wave_forms = []
        for t, s in self.WAVE_FORMS.items():
            # if present in WAVE or SETTINGS assign
            if hasattr(WAVE, s):
                temp_results_dict[t] = getattr(WAVE, s)
            elif hasattr(SETTINGS, s):
                temp_results_dict[t] = getattr(SETTINGS, s)
            elif skip_empty == False:
                # Should an Error be returned
                raise MissingTagError(s)
            else:
                # assign NA and append missing metadata
                temp_results_dict[t] = np.nan
                empty_wave_forms.append(s)
        # #### Add the lead strings
        channel_seq = getattr(getattr(ECG, FRNames.WAVE_FORM_SEQ)[0],
                              FRNames.CHANNEL_DEF_SEQ)
        lead_info_waveform, lead_units=self._get_lead_info(channel_seq)
        temp_results_dict[LEAD_UNITS] = lead_units
        WAVE_LEADS = {}
        for k, lead in enumerate(WAVE_TEMP):
            WAVE_LEADS[lead_info_waveform[k]] = lead
        del WAVE_TEMP
        # #### do we want to extract the augmented leads
        if getattr(self, PDNames.AUG_LEADS) == True and\
                len(WAVE_LEADS) < 12:
            WAVE_LEADS = ecg_utils.get_limb_leads(WAVE_LEADS)
        # ####  set the processed WAVE FORM data
        setattr(self, CTypes.WaveForms, WAVE_LEADS)
        # return
        return ECG, temp_results_dict, empty_wave_forms
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def get_median_beats(self, path:str|None=None,
                     dicom_instance: pydicom.dataset.FileDataset|None=None,
                     skip_empty:bool=True
                     ) -> tuple[pydicom.dataset.FileDataset,
                                dict[str, Any], list[str]]:
        '''
        Takes a dicom file and extracts the median beats and its metadata.
        
        Parameters
        ----------
        path : `str`, default `NoneType`.
            The path to the .dcm file.
        dicom_instance : `DCM_Class`, default `NoneType`.
            A DCM_Class instance.
        
        Returns
        -------
        results : dict,DCM_Class
            - A `DCM_Class` instance.
            - A dictionary with extracted metadata.
            - A list of missing `DCM_Class` attribute names.
        
        Notes
        -----
        Either supply a path to a dicom file or a DCM_Class instance
        '''
        # #### check input
        is_type(path, (type(None), pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(dicom_instance, (type(None), pydicom.dataset.FileDataset))
        is_type(skip_empty, bool)
        temp_results_dict = {}
        if (not dicom_instance is None) and (not path is None):
            raise ValueError(self.__MSG1)
        # #### constants
        WAVE_FORM_ARR = 'waveform_array'
        LEAD_UNITS2 = 'MedianWaveformUnits'
        # #### Read DICOM
        # NOTE `with` closes automatically if an error is raised
        if not path is None:
            with open(path, 'rb') as dicom:
                # reads standard dicom content
                ECG=pydicom.dcmread(dicom)
        else:
            ECG=dicom_instance
        # ##### extract the median beats data
        # check if the wave form is present and if the index is correct
        # the median beats should be index 1 (starting at 0)
        temp_results_dict = {k: None for k in self.MEDIAN_BEATS}
        empty_median_beats = list(self.MEDIAN_BEATS.keys())
        sccss = True
        try:
            TEMP_MEDIAN = getattr(ECG, WAVE_FORM_ARR)(1).T
        except:
            if skip_empty == True:
                setattr(self, CTypes.MedianBeats, None)
                sccss = False
                pass
            else:
                raise AttributeError(
                    Error_MSG.MISSING_DICOM.format(WAVE_FORM_ARR))
        # ##### getting WaveformSequence and ChannelDefinitionSequence attributes
        if sccss == True:
            WAVE_M = getattr(ECG, FRNames.WAVE_FORM_SEQ)[1]
            SETTINGS_M = getattr(WAVE_M, FRNames.CHANNEL_DEF_SEQ)[1]
            for t, s in self.MEDIAN_BEATS.items():
                # if present in WAVE or SETTINGS assign
                if hasattr(WAVE_M, s):
                    temp_results_dict[t] = getattr(WAVE_M, s)
                    empty_median_beats.remove(t)
                elif hasattr(SETTINGS_M, s):
                    temp_results_dict[t] = getattr(SETTINGS_M, s)
                    empty_median_beats.remove(t)
                elif skip_empty == False:
                    # Should an Error be returned
                    raise MissingTagError(s)
                else:
                    # the dict and list have already been pre-populated
                    pass
            # #### Add the lead strings
            channel_seq_median=getattr(getattr(ECG, FRNames.WAVE_FORM_SEQ)[0],
                                       FRNames.CHANNEL_DEF_SEQ)
            lead_info_waveform, lead_units2=\
                self._get_lead_info(channel_seq_median)
            temp_results_dict[LEAD_UNITS2] = lead_units2
            MEDIAN_LEAD = {}
            for k, lead in enumerate(TEMP_MEDIAN):
                MEDIAN_LEAD[lead_info_waveform[k]] = lead
            del TEMP_MEDIAN
            # #### do we want to extract the augmented leads
            if getattr(self, PDNames.AUG_LEADS) == True and\
                    len(MEDIAN_LEAD) < 12:
                MEDIAN_LEAD = ecg_utils.get_limb_leads(MEDIAN_LEAD)
            # #### set median beats
            setattr(self, CTypes.MedianBeats, MEDIAN_LEAD)
        # #### return
        return ECG, temp_results_dict, empty_median_beats
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _get_waveform_annotation(
        self, path:str|None=None,
        dicom_instance: pydicom.dataset.FileDataset|None=None,
        skip_empty:bool=True,) -> tuple[pydicom.dataset.FileDataset,
                                        dict[str, Any], list[str]]:
        '''
        Extract information from the `WaveformAnnotationSequence` attribute
        of an dicom file.
        
        Parameters
        ----------
        path : `str`, default `NoneType`.
            The path to the .dcm file.
        dicom_instance : `DCM_Class`, default `NoneType`.
            A DCM_Class instance.
        
        Returns
        -------
        results : dict,DCM_Class
            - A `DCM_Class` instance.
            - A dictionary with the extracted data.
            - A list of missing `DCM_Class` attribute names.
        
        Notes
        -----
        Either supply a path to a dicom file or a DCM_Class instance
        '''
        # #### check input
        is_type(path, (type(None), pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(dicom_instance, (type(None), pydicom.dataset.FileDataset))
        is_type(skip_empty, bool)
        default_results_dict = {}
        temp_results_dict = {}
        temp_unit_dict = {}
        if (not dicom_instance is None) and (not path is None):
            raise ValueError(self.__MSG1)
        # #### constants
        ECG_UNIT_STRING = ' UNIT'
        PACEMAKER_SPIKE = 'Pacemaker Spike'
        ECG_INTERPERTATION = 'WaveformAnnotationSequence'
        ECG_CONCEPTNAME = 'ConceptNameCodeSequence'
        CODE_MEANING = 'CodeMeaning'
        ECG_UNIT = 'MeasurementUnitsCodeSequence'
        ECG_TRAIT_VALUE = 'NumericValue'
        REFERENCED_POS = 'ReferencedSamplePositions'
        FREE_TEXT = 'UnformattedTextValue'
        # #### Read DICOM
        # NOTE `with` closes automatically if an error is raised
        if not path is None:
            with open(path, 'rb') as dicom:
                # reads standard dicom content
                ECG=pydicom.dcmread(dicom)
        else:
            ECG=dicom_instance
        # first set everything to NA
        for e in self.ECG_TRAIT_DICT:
           default_results_dict[e] = np.nan
           default_results_dict[e+ ECG_UNIT_STRING] = np.nan
           default_results_dict[FREE_TEXT] = None
           default_results_dict[PACEMAKER_SPIKE]=np.nan
        # next see if we can extract some interpretations.
        if hasattr(ECG, ECG_INTERPERTATION):
            free_text = ''
            # get the values lower-case strings (which are lists)
            ECG_CMPR_LWR = [it.lower() for sl\
                            in self.ECG_TRAIT_DICT.values() for it in sl]
            for w in getattr(ECG, ECG_INTERPERTATION):
                # # set annot_count to -1 if not there
                # # ANNOT GROUP  of > 0 represents annotations (1), arrythmia
                # # markers (2), or pacemaker spikes (3).
                # # group 0 will be the free text.
                # annot_count = getattr(w, PDNames.ANNOTATION_GROUP, -1)
                # if hasattr(w, PDNames.ECG_CONCEPTNAME) and annot_count > 0:
                if hasattr(w, ECG_CONCEPTNAME):
                    ecg_int = getattr(w, ECG_CONCEPTNAME)[0]
                    try:
                        ecg_trait = getattr(ecg_int, CODE_MEANING)
                        # find matching element - using lower case again
                        if ecg_trait.lower() in ECG_CMPR_LWR:
                            # get the measurement and set to float, will
                            # skip float conversion if None type.
                            try:
                                temp_results_dict[ecg_trait.lower()] = float(
                                            getattr(w, ECG_TRAIT_VALUE)
                                        )
                            except TypeError:
                                temp_results_dict[ecg_trait.lower()] = \
                                    getattr(w, ECG_TRAIT_VALUE)
                                # see if we need to warn
                                if self.verbose == True:
                                    warnings.warn(Warn_MSG.NUMB_IS_NONE.\
                                                  format(ecg_trait.lower()))
                            # get the unit
                            try:
                                temp_unit_dict[
                                    ecg_trait.lower()+\
                                    ECG_UNIT_STRING]=getattr(
                                        getattr(w, ECG_UNIT)[0],
                                        CODE_MEANING)
                            except (AttributeError, IndexError):
                                pass
                        # #### ancillary info
                        # see if there is a PaceMakerSpike
                        if ecg_trait.lower() == PACEMAKER_SPIKE.lower():
                            try:
                                v = default_results_dict[
                                    PACEMAKER_SPIKE]
                                nv = str(getattr(w, REFERENCED_POS))
                                default_results_dict[
                                    PACEMAKER_SPIKE] = string_concat(
                                        v, nv, sep=', ')
                                del v, nv
                            except AttributeError:
                                pass
                    except AttributeError:
                        pass
                # get free text
                # if annot_count == 0:
                if hasattr(w, FREE_TEXT):
                    try:
                        v = default_results_dict[FREE_TEXT]
                        nv = getattr(w, FREE_TEXT)
                        default_results_dict[FREE_TEXT] =\
                            string_concat(old=v, new=nv, sep='\n')
                        del v, nv
                    except AttributeError:
                        pass
        # now assign temp_results_dict todefault_results_dict dealing with
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
                           default_results_dict[k] =\
                                temp_results_dict[e.lower()]
                           default_results_dict[k+ECG_UNIT_STRING] =\
                                temp_unit_dict[
                                    e.lower()+ECG_UNIT_STRING]
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
                           default_results_dict[e] =\
                                temp_results_dict[e.lower()]
                           default_results_dict[e+ECG_UNIT_STRING] =\
                                temp_unit_dict[
                                    e.lower()+ECG_UNIT_STRING]
                        except KeyError:
                            pass
        # which ECG traits are still nan
        missing_ecg_traits =\
            [k for k,v in default_results_dict.items() if pd.isna(v)]
        if skip_empty == False and len(missing_ecg_traits) > 0:
            # Should an Error be returned
            raise ValueError('The following ECG measurments are '
                             'unavailable: {}'.format(missing_ecg_traits))
        # return
        return ECG, default_results_dict, missing_ecg_traits
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def _get_lead_info(self, channel_seq:pydicom.dataset.FileDataset,
                       ) -> tuple[dict[int, str], str]:
        """
        Extracts the lead names from a `dcmread` instance.
        
        Parameters
        ----------
        channel_seq : `DCM_Class`
            A `pydicom.sequence.Sequence` instance.
        
        Returns
        -------
        `tuple` ['dict', `str`]:
            - leadnames : dict [`int`, `str`]
                A dictionary with numerical (interval) keys and the lead names
                as values.
            - leadunit : str
                The measurment unit of the ECG leads.
        """
        # #### extracting the lead names
        leadnames = {}
        leadunits = {}
        # #### constants
        CHANNEL_SOURCE_SEQ  = 'ChannelSourceSequence'
        CHANNEL_CODE_MEANING = 'CodeMeaning'
        CHANNEL_SENS_UNIT = 'ChannelSensitivityUnitsSequence'
        CODE_MEANING = 'CodeMeaning'
        LEAD = 'Lead'
        for k, channel in enumerate(channel_seq):
            # extracting lead names
            source = getattr(getattr(channel,CHANNEL_SOURCE_SEQ)[0],
                             CHANNEL_CODE_MEANING)
            # extracting units
            if hasattr(channel, CHANNEL_SENS_UNIT):
                unit = getattr(
                    getattr(channel, CHANNEL_SENS_UNIT)[0], CODE_MEANING)
            else:
                unit = np.nan
            # assign lead names to numericals
            if k == 'I (Einthoven)':
                k = CLeads.I
            leadnames[k] = source.replace(LEAD, '').strip()
            leadunits[leadnames[k]] = unit
        # confirm the units are all the same
        unique_unit = list(set(leadunits.values()))
        if len(unique_unit) != 1:
            raise ValueError('The ECG leads were measured using different '
                             'units: `{}`.'.format(unique_unit))
        # return stuff
        return leadnames, unique_unit[0]
