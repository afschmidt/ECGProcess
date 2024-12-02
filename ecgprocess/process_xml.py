'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''
import pathlib
from lxml import etree
from dataclasses import dataclass, field
from typing import (
    Optional, Self, Any, Literal,
)
from ecgprocess.process_dicoms import (
    BaseECGDICOMReader,
)
from ecgprocess.utils.general import(
    validate_xml,
    xml_to_dict,
    flatten_dict,
    property_factory as prop_fac,
    ManagedProperty,

)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)
from ecgprocess.errors import (
    is_type,
    _check_readable,
    _check_presence,
    Error_MSG,
)
from ecgprocess.constants import (
    ProcessXMLNames as PXMLNam,
    CoreData as Core,
)

# NOTE REMOVE THIS
from ecgprocess.example_data.examples import (
    list_xml_paths
)
path = list_xml_paths()['example_1']
validate = list_xml_paths()['example_1_shema']
verbose=True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ecgxml_reader = ECGXMLReader()
parsed_xml = ecgxml_reader(path=path, validate=validate, verbose=True)
parsed_xml.temp
parsed_xml.temp['CardiologyXML']['RestingECGMeasurements']
temp_l = parsed_xml.temp['CardiologyXML']['RestingECGMeasurements']['MedianSamples']['WaveformData']
# already \n\t\t here
temp_l[0]['#text']
# NOTE array data in flatten_dict output contains  \n\t\t see where these
# should be addressed either in flatted_dict or xml_to_dict
parsed_xml.xml_dict['RestingECGMeasurements.MedianSamples.WaveformData_11.#text']
parsed_xml.xml_dict['StripData.WaveformData_0.#text']
parsed_xml.xml_dict['StripData.WaveformData_0.@lead']

print(*parsed_xml.xml_tags, sep='\n')
# >>> print(*parsed_xml.xml_tags, sep='\n')
# ObservationType
# ObservationDateTime.Hour
# ObservationDateTime.Minute
# ObservationDateTime.Second
# ObservationDateTime.Day
# ObservationDateTime.Month
# ObservationDateTime.Year
# UID.DICOMStudyUID
# ClinicalInfo.ReasonForStudy
# ClinicalInfo.Technician.FamilyName
# ClinicalInfo.Technician.GivenName
# ClinicalInfo.Technician.PersonID
# ClinicalInfo.ObservationComment
# ClinicalInfo.DeviceInfo.Desc
# ClinicalInfo.DeviceInfo.SoftwareVer
# ClinicalInfo.DeviceInfo.AnalysisVer
# PatientVisit.PatientClass
# PatientVisit.AssignedPatientLocation.Facility
# PatientVisit.AssignedPatientLocation.LocationNumber
# PatientVisit.AssignedPatientLocation.LocationName
# PatientVisit.PatientRoom
# PatientVisit.AdmissionType
# PatientVisit.OrderingProvider.FamilyName
# PatientVisit.OrderingProvider.GivenName
# PatientVisit.OrderingProvider.PersonID
# PatientVisit.AttendingDoctor.FamilyName
# PatientVisit.AttendingDoctor.GivenName
# PatientVisit.AttendingDoctor.PersonID
# PatientVisit.ReferringDoctor.FamilyName
# PatientVisit.ReferringDoctor.GivenName
# PatientVisit.ReferringDoctor.PersonID
# PatientVisit.ServicingFacility.Name
# PatientVisit.ServicingFacility.Address.Street1
# PatientVisit.ServicingFacility.Address.City
# PatientVisit.SysBP.@units
# PatientVisit.DiaBP.@units
# PatientVisit.MedicalHistory.MedicalHistoryText
# PatientVisit.OrderNumber
# PatientVisit.Medications.Drug
# PatientVisit.Medications.Dosage
# PatientVisit.ExtraQuestions.Label_0.@Type
# PatientVisit.ExtraQuestions.Label_1.@Type
# PatientVisit.ExtraQuestions.Content_0
# PatientVisit.ExtraQuestions.Content_1
# PatientInfo.PID
# PatientInfo.Name.FamilyName
# PatientInfo.Name.GivenName
# PatientInfo.Age.@units
# PatientInfo.Age.#text
# PatientInfo.BirthDateTime.Day
# PatientInfo.BirthDateTime.Month
# PatientInfo.BirthDateTime.Year
# PatientInfo.Gender
# PatientInfo.Race
# PatientInfo.Height.@units
# PatientInfo.Height.#text
# PatientInfo.Weight.@units
# PatientInfo.Weight.#text
# PatientInfo.PaceMaker
# FilterSetting.CubicSpline
# FilterSetting.Filter50Hz
# FilterSetting.Filter60Hz
# FilterSetting.LowPass.@units
# FilterSetting.LowPass.#text
# FilterSetting.HighPass.@units
# FilterSetting.HighPass.#text
# Device-Type
# Interpretation.Diagnosis.DiagnosisText_0
# Interpretation.Diagnosis.DiagnosisText_1
# Interpretation.Diagnosis.DiagnosisText_2
# Interpretation.Diagnosis.DiagnosisText_3
# Interpretation.Diagnosis.DiagnosisText_4
# Interpretation.Conclusion.ConclusionText_0
# Interpretation.Conclusion.ConclusionText_1
# Interpretation.Conclusion.ConclusionText_2
# Interpretation.Conclusion.ConclusionText_3
# Interpretation.Conclusion.ConclusionText_4
# RestingECGMeasurements.DiagnosisVersion
# RestingECGMeasurements.VentricularRate.@units
# RestingECGMeasurements.VentricularRate.#text
# RestingECGMeasurements.PQInterval.@units
# RestingECGMeasurements.PQInterval.#text
# RestingECGMeasurements.PDuration.@units
# RestingECGMeasurements.PDuration.#text
# RestingECGMeasurements.QRSDuration.@units
# RestingECGMeasurements.QRSDuration.#text
# RestingECGMeasurements.QTInterval.@units
# RestingECGMeasurements.QTInterval.#text
# RestingECGMeasurements.QTCInterval.@units
# RestingECGMeasurements.QTCInterval.#text
# RestingECGMeasurements.RRInterval.@units
# RestingECGMeasurements.RRInterval.#text
# RestingECGMeasurements.PPInterval.@units
# RestingECGMeasurements.PPInterval.#text
# RestingECGMeasurements.SokolovLVHIndex.@units
# RestingECGMeasurements.PAxis.@units
# RestingECGMeasurements.PAxis.#text
# RestingECGMeasurements.RAxis.@units
# RestingECGMeasurements.RAxis.#text
# RestingECGMeasurements.TAxis.@units
# RestingECGMeasurements.TAxis.#text
# RestingECGMeasurements.QTDispersion.@units
# RestingECGMeasurements.QTDispersionBazett.@units
# RestingECGMeasurements.QRSNum
# RestingECGMeasurements.MeasurementTable.@Creation
# RestingECGMeasurements.MeasurementTable.LeadOrder
# RestingECGMeasurements.MeasurementTable.QDuration.@units
# RestingECGMeasurements.MeasurementTable.QDuration.#text
# RestingECGMeasurements.MeasurementTable.RDuration.@units
# RestingECGMeasurements.MeasurementTable.RDuration.#text
# RestingECGMeasurements.MeasurementTable.SDuration.@units
# RestingECGMeasurements.MeasurementTable.SDuration.#text
# RestingECGMeasurements.MeasurementTable.RpDuration.@units
# RestingECGMeasurements.MeasurementTable.RpDuration.#text
# RestingECGMeasurements.MeasurementTable.PAmplitude.@units
# RestingECGMeasurements.MeasurementTable.PAmplitude.#text
# RestingECGMeasurements.MeasurementTable.QAmplitude.@units
# RestingECGMeasurements.MeasurementTable.QAmplitude.#text
# RestingECGMeasurements.MeasurementTable.RAmplitude.@units
# RestingECGMeasurements.MeasurementTable.RAmplitude.#text
# RestingECGMeasurements.MeasurementTable.SAmplitude.@units
# RestingECGMeasurements.MeasurementTable.SAmplitude.#text
# RestingECGMeasurements.MeasurementTable.R1Amplitude.@units
# RestingECGMeasurements.MeasurementTable.R1Amplitude.#text
# RestingECGMeasurements.MeasurementTable.S1Amplitude.@units
# RestingECGMeasurements.MeasurementTable.S1Amplitude.#text
# RestingECGMeasurements.MeasurementTable.JAmplitude.@units
# RestingECGMeasurements.MeasurementTable.JAmplitude.#text
# RestingECGMeasurements.MeasurementTable.JXAmplitude.@units
# RestingECGMeasurements.MeasurementTable.JXAmplitude.#text
# RestingECGMeasurements.MeasurementTable.TAmplitude.@units
# RestingECGMeasurements.MeasurementTable.TAmplitude.#text
# RestingECGMeasurements.MeasurementTable.JXSlope.@units
# RestingECGMeasurements.MeasurementTable.JXSlope.#text
# RestingECGMeasurements.MeasurementTable.R1Duration.@units
# RestingECGMeasurements.MeasurementTable.R1Duration.#text
# RestingECGMeasurements.MeasurementTable.P1Amplitude.@units
# RestingECGMeasurements.MeasurementTable.P1Amplitude.#text
# RestingECGMeasurements.MeasurementTable.JXEAmplitude.@units
# RestingECGMeasurements.MeasurementTable.JXEAmplitude.#text
# RestingECGMeasurements.MeasurementTable.T1Amplitude.@units
# RestingECGMeasurements.MeasurementTable.T1Amplitude.#text
# RestingECGMeasurements.POnset.@units
# RestingECGMeasurements.POnset.#text
# RestingECGMeasurements.POffset.@units
# RestingECGMeasurements.POffset.#text
# RestingECGMeasurements.QOnset.@units
# RestingECGMeasurements.QOnset.#text
# RestingECGMeasurements.QOffset.@units
# RestingECGMeasurements.QOffset.#text
# RestingECGMeasurements.TOffset.@units
# RestingECGMeasurements.TOffset.#text
# RestingECGMeasurements.MedianSamples.NumberOfLeads
# RestingECGMeasurements.MedianSamples.SampleRate.@units
# RestingECGMeasurements.MedianSamples.SampleRate.#text
# RestingECGMeasurements.MedianSamples.ChannelSampleCountTotal
# RestingECGMeasurements.MedianSamples.Resolution.@units
# RestingECGMeasurements.MedianSamples.Resolution.#text
# RestingECGMeasurements.MedianSamples.FirstValid.@units
# RestingECGMeasurements.MedianSamples.FirstValid.#text
# RestingECGMeasurements.MedianSamples.LastValid.@units
# RestingECGMeasurements.MedianSamples.LastValid.#text
# RestingECGMeasurements.MedianSamples.WaveformData_0.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_0.#text
# RestingECGMeasurements.MedianSamples.WaveformData_1.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_1.#text
# RestingECGMeasurements.MedianSamples.WaveformData_2.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_2.#text
# RestingECGMeasurements.MedianSamples.WaveformData_3.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_3.#text
# RestingECGMeasurements.MedianSamples.WaveformData_4.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_4.#text
# RestingECGMeasurements.MedianSamples.WaveformData_5.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_5.#text
# RestingECGMeasurements.MedianSamples.WaveformData_6.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_6.#text
# RestingECGMeasurements.MedianSamples.WaveformData_7.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_7.#text
# RestingECGMeasurements.MedianSamples.WaveformData_8.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_8.#text
# RestingECGMeasurements.MedianSamples.WaveformData_9.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_9.#text
# RestingECGMeasurements.MedianSamples.WaveformData_10.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_10.#text
# RestingECGMeasurements.MedianSamples.WaveformData_11.@lead
# RestingECGMeasurements.MedianSamples.WaveformData_11.#text
# VectorLoops.@Creation
# VectorLoops.Resolution.@units
# VectorLoops.Resolution.#text
# VectorLoops.ChannelSampleCountTotal
# VectorLoops.POnset.@units
# VectorLoops.POnset.#text
# VectorLoops.POffset.@units
# VectorLoops.POffset.#text
# VectorLoops.QOnset.@units
# VectorLoops.QOnset.#text
# VectorLoops.QOffset.@units
# VectorLoops.QOffset.#text
# VectorLoops.TOffset.@units
# VectorLoops.TOffset.#text
# VectorLoops.Frontal_0.@Lead
# VectorLoops.Frontal_0.#text
# VectorLoops.Frontal_1.@Lead
# VectorLoops.Frontal_1.#text
# VectorLoops.Horizontal_0.@Lead
# VectorLoops.Horizontal_0.#text
# VectorLoops.Horizontal_1.@Lead
# VectorLoops.Horizontal_1.#text
# VectorLoops.Sagittal_0.@Lead
# VectorLoops.Sagittal_0.#text
# VectorLoops.Sagittal_1.@Lead
# VectorLoops.Sagittal_1.#text
# StripData.NumberOfLeads
# StripData.SampleRate.@units
# StripData.SampleRate.#text
# StripData.ChannelSampleCountTotal
# StripData.Resolution.@units
# StripData.Resolution.#text
# StripData.WaveformData_0.@lead
# StripData.WaveformData_0.#text
# StripData.WaveformData_1.@lead
# StripData.WaveformData_1.#text
# StripData.WaveformData_2.@lead
# StripData.WaveformData_2.#text
# StripData.WaveformData_3.@lead
# StripData.WaveformData_3.#text
# StripData.WaveformData_4.@lead
# StripData.WaveformData_4.#text
# StripData.WaveformData_5.@lead
# StripData.WaveformData_5.#text
# StripData.WaveformData_6.@lead
# StripData.WaveformData_6.#text
# StripData.WaveformData_7.@lead
# StripData.WaveformData_7.#text
# StripData.WaveformData_8.@lead
# StripData.WaveformData_8.#text
# StripData.WaveformData_9.@lead
# StripData.WaveformData_9.#text
# StripData.WaveformData_10.@lead
# StripData.WaveformData_10.#text
# StripData.WaveformData_11.@lead
# StripData.WaveformData_11.#text
# StripData.ArrhythmiaResults.Time_0.@units
# StripData.ArrhythmiaResults.Time_0.#text
# StripData.ArrhythmiaResults.Time_1.@units
# StripData.ArrhythmiaResults.Time_1.#text
# StripData.ArrhythmiaResults.Time_2.@units
# StripData.ArrhythmiaResults.Time_2.#text
# StripData.ArrhythmiaResults.Time_3.@units
# StripData.ArrhythmiaResults.Time_3.#text
# StripData.ArrhythmiaResults.Time_4.@units
# StripData.ArrhythmiaResults.Time_4.#text
# StripData.ArrhythmiaResults.Time_5.@units
# StripData.ArrhythmiaResults.Time_5.#text
# StripData.ArrhythmiaResults.Time_6.@units
# StripData.ArrhythmiaResults.Time_6.#text
# StripData.ArrhythmiaResults.Time_7.@units
# StripData.ArrhythmiaResults.Time_7.#text
# StripData.ArrhythmiaResults.BeatClass_0
# StripData.ArrhythmiaResults.BeatClass_1
# StripData.ArrhythmiaResults.BeatClass_2
# StripData.ArrhythmiaResults.BeatClass_3
# StripData.ArrhythmiaResults.BeatClass_4
# StripData.ArrhythmiaResults.BeatClass_5
# StripData.ArrhythmiaResults.BeatClass_6
# StripData.ArrhythmiaResults.BeatClass_7
# FullDisclosure.NumberOfChannels
# FullDisclosure.SampleRate.@units
# FullDisclosure.SampleRate.#text
# FullDisclosure.Resolution.@units
# FullDisclosure.Resolution.#text
# FullDisclosure.LeadOrder
# FullDisclosure.FullDisclosureData.SampleCountTotal
# FullDisclosure.FullDisclosureData.#text
# FullDisclosure.EventList.Event_0
# FullDisclosure.EventList.Event_1
# FullDisclosure.EventList.Event_2
# FullDisclosure.EventList.Event_3
# FullDisclosure.EventList.Time_0.Minute
# FullDisclosure.EventList.Time_0.Second
# FullDisclosure.EventList.Time_1.Minute
# FullDisclosure.EventList.Time_1.Second
# FullDisclosure.EventList.Time_2.Minute
# FullDisclosure.EventList.Time_2.Second
# FullDisclosure.EventList.Time_3.Minute
# FullDisclosure.EventList.Time_3.Second
# FullDisclosure.ArrhythmiaResults.QRS
# Export
# CSWeb.a.@href

@dataclass
class ECGXMLReader(BaseECGDICOMReader):
    """
    Processes an XML file containing ECG data and extracts the metadata,
    median beats (if available), and raw waveforms.
    
    Parameters
    ----------
    augment_leads : `bool`, default `False`
        Whether the augmented leads should be calculated if these are not
        already available in the source file.
    resample : `bool`, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    retain_raw : `bool`, default `False`
        Whether the raw parsed XML tree should be retained.  Set to `False` to
        decrease memory usage. Set to `True` to explore the parsed document.
        For example, use this one a few files to identify none-standard
        information to extract.
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
    retain_raw : `bool`
        Whether the raw data was retained.
    STUDY_DATE_SOURCE : str
        The study date format.  This will be used in `datetime.strptime` as
        format argument.
    STUDY_DATE_TARGET : str
        The target formatting of the study date.  This will be used in
        `datetime.strptime` as format argument.
    ACQUISITION_DATE_SOURCE : str
        The acquisition date and time format.  This will be used in
        `datetime.strptime` as format argument.
    ACQUISITION_DATE_TARGET : str
        The target formatting of the acquisition date and time.  This will be
        used in `datetime.strptime` as format argument.
    
    Methods
    -------
    TODO
    
    Notes
    -----
    The waveforms are stored using `__slots__` to decrease memory usage, which
    is further improved by setting `retain_raw` to `False` - the default
    behaviour.
    """
    # #### properties
    # NOTE add these to the docstring
    xml_tags = ManagedProperty(PXMLNam.XML_TAGS, list)
    xml_dict = ManagedProperty(PXMLNam.XML_DICT, list)
    # #### parameters, with defaults
    augment_leads:bool = field(default=False)
    resample_500:bool = field(default=True)
    retain_raw:bool = field(default=False)
    # #### default dates to extract and format
    STUDY_DATE_SOURCE = "%Y%m%d"
    STUDY_DATE_TARGET = "%Y-%m-%d"
    ACQUISITION_DATE_SOURCE = "%Y%m%d%H%M%S"
    ACQUISITION_DATE_TARGET = "%Y-%m-%d %H:%M:%S"
    # #### Error MSG
    __MSG1=Error_MSG.MISSING_PATH_INSTANCE.format('xml_tree')
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __post_init__(self):
        """Validating inputs."""
        is_type(self.augment_leads, bool)
        is_type(self.resample_500, bool)
        is_type(self.retain_raw, bool)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, validate:str | None = None,
                 skip_empty:bool=True,
                 verbose:bool=False,
                 **kwargs:Optional[Any],
                 ) -> Self:
        """
        Reads an `.xml` file containing ECG readings and extracts  metadata,
        raw waveforms, and median beats data, based on a parsed configuration
        file mapping XML tags to class attributes.
        
        Parameters
        ----------
        path : `str`
            The path to the .xml file.
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the XML
            content to class attributes.
        validate : `str`, default `NoneType`
            A path to an XML schema which will be used to valudate the XML file
            against.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose : `bool`, default `False`
            Prints missing tags if skip_empty is set to `True`.
        **kwargs : any
            keyword arguments passed to flatten_dict.
        
        Attributes
        ----------
        MetaData : `dict` [`str`, `any`]
            ECG metadata.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianBeats : `dict` [`str`, `np.array`]
            The lead specific ECG median beats.
        
        Returns
        -------
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes containign the
            extracted XML data.
        
        Notes
        -----
        TODO add explanations on the extractor instance.
        """
        # #### check input
        is_type(path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(validate, (type(None), pathlib.PosixPath, pathlib.WindowsPath,
                           str))
        is_type(skip_empty, bool)
        is_type(verbose, bool)
        # #### assign to self
        self.verbose = verbose
        # #### confirm file is readable
        _check_readable(path)
        # #### validate XML
        if not validate is None:
            _check_readable(validate)
            parsed_xml = validate_xml(xml_path=path, xsd_path=validate,
                                      verbose=verbose)
        else:
            with open(path, 'rb') as xml:
                parsed_xml = etree.parse(xml)
        # map to flatten_dict
        self.temp = xml_to_dict(parsed_xml)
        xml_dict = flatten_dict(xml_to_dict(parsed_xml), **kwargs)
        # xml_dict = flatten_dict(xml_to_dict(parsed_xml))
        # ### store keys
        getattr(type(self), PXMLNam.XML_DICT).set_with_setter(self, xml_dict)
        getattr(type(self), PXMLNam.XML_TAGS).set_with_setter(
            self, list(xml_dict.keys()))
        # ### return
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def extract(config:ConfigParser):
        """
        TODO
        
        Parameters
        ----------
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the XML
            content to class attributes.
        """
        is_type(config, ConfigParser)


