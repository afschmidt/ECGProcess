'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''
import pathlib
import warnings
import ecgprocess.utils.config_tools as config
import ecgprocess.utils.reader_tools as reader_utils
import ecgprocess.utils.ecg_tools as ecg_utils
from lxml import etree
from ecgprocess.utils.reader_tools import(
    BaseReader,
)
from dataclasses import dataclass, field
from typing import (
    Optional, Self, Any, Literal,
)
from ecgprocess.utils.general import(
    ManagedProperty,
)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)
from ecgprocess.errors import (
    is_type,
    _check_readable,
    Warn_MSG,
    Error_MSG,
)
from ecgprocess.constants import (
    ProcessXMLNames as PXMLNam,
    CoreData as Core,
)

# NOTE REMOVE THIS
# from ecgprocess.example_data.examples import (
#     config_file,
#     list_xml_paths,
# )
# from tempfile import NamedTemporaryFile
# path = list_xml_paths()['example_1']
# validate = list_xml_paths()['example_1_schema']
# verbose=True
# # getting a parsed config file
# example_config = {
#     "WaveForms": [
#         "I\tStripData.WaveformData_0.#text",
#         "WRONG\tStripData.WaveformData_1.#text",
#     ],
#     "MedianBeats": [
#         "aVF\tRestingECGMeasurements.MedianSamples.WaveformData_5.#text",
#         "V1\tRestingECGMeasurements.MedianSamples.WaveformData_6.#text",
#     ],
#     "MetaData": [
#         "unique identifier\t\t\tUID.DICOMStudyUID",
#         "number of leads\t\t\t\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
#         "resolution unit (waveforms)\t\tStripData.Resolution.@units",
#         "resolution (waveforms)\t\t\tStripData.Resolution.#text",
#         "resolution unit (medianbeats)\t\tRestingECGMeasurements.MedianSamples.Resolution.@units",
#         "resolution (medianbeats)\t\tRestingECGMeasurements.MedianSamples.Resolution.#text",
#         "sampling frequency (original)\t\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
#         "sampling frequency unit\t\t\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
#         "sampling number (waveforms)\t\tStripData.ChannelSampleCountTotal",
#         "sampling number (medianbeats)\t\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
#         "observation hour\t\t\tObservationDateTime.Hour",
#         "observation minute\t\t\tObservationDateTime.Minute",
#         "observation second\t\t\tObservationDateTime.Second",
#         "observation day\t\t\t\tObservationDateTime.Day",
#         "observation month\t\t\tObservationDateTime.Month",
#         "observation year\t\t\tObservationDateTime.Year",
#     ]
# }
# with NamedTemporaryFile("w") as tmp_file:
#     _ = config_file(path=tmp_file.name, text=example_config)
#     parsed_confg = config.ConfigParser(tmp_file.name)()

# config=parsed_confg.get_section('WaveForms')
# skip_empty = True
# ecgxml_reader = ECGXMLReader()
# parsed_xml = ecgxml_reader(path=path, schema=validate, verbose=True)
# data_dict = parsed_xml.raw_data.copy()

# ~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CLeads = Core.Leads
CMeta = Core.MetaData
CProc = Core.ProcessingData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGXMLReader(BaseReader):
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
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
    
    Methods
    -------
    extract(config, skip_empty, parse_numeric, **kwargs)
        Processes the XML file content applying optional lead augmentation and
        resampling. The XML content will be mapped to class attributes.
    
    """
    # #### properties
    # NOTE add these to the docstring
    xml_tags = ManagedProperty(PXMLNam.XML_TAGS, list)
    raw_data = ManagedProperty(CProc.RAW, dict)
    # #### parameters, with defaults
    augment_leads:bool = field(default=False)
    resample_500:bool = field(default=True)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __post_init__(self):
        """Validating inputs."""
        is_type(getattr(self, PXMLNam.AUG_LEADS), bool)
        is_type(getattr(self, PXMLNam.RESAMPLE), bool)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, schema:str | None = None,
                 verbose:bool=False,
                 **kwargs:Optional[Any],
                 ) -> Self:
        """
        Reads an `.xml` file containing ECG readings, optionally validates this
        based on a .xsd schema, and map the XML file to a flat dictionary.
        
        Parameters
        ----------
        path : `str`
            The path to the .xml file.
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the XML
            content to class attributes.
        schema : `str`, default `NoneType`
            A path to an XML schema which will be used to valudate the XML file
            against.
        verbose : `bool`, default `False`
            Whether warnings and process info should be printed.
        **kwargs : any
            keyword arguments passed to flatten_dict.
        
        Attributes
        ----------
        raw_data : `dict` [`str`, `any`]
            The raw parsed data.
        
        Returns
        -------
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes including the
            extracted XML data.
        """
        # #### check input
        is_type(path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(schema, (type(None), pathlib.PosixPath, pathlib.WindowsPath,
                           str))
        is_type(verbose, bool)
        # #### assign to self
        self.verbose = verbose
        # #### confirm file is readable
        _check_readable(path)
        # #### validate XML
        if not schema is None:
            _check_readable(schema)
            parsed_xml = reader_utils.validate_xml(
                xml_path=path, xsd_path=schema, verbose=verbose)
        else:
            with open(path, 'rb') as xml:
                parsed_xml = etree.parse(xml)
        # map to flatten_dict
        xml_dict = reader_utils.flatten_dict(
            reader_utils.xml_to_dict(parsed_xml),
            **kwargs,
        )
        # xml_dict = flatten_dict(xml_to_dict(parsed_xml))
        # ### store keys
        getattr(type(self), CProc.RAW).set_with_setter(self, xml_dict)
        getattr(type(self), PXMLNam.XML_TAGS).set_with_setter(
            self, list(xml_dict.keys()))
        # ### return
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def extract(self, config:ConfigParser, skip_empty:bool,
                parse_numeric:bool=True, **kwargs:Optional[Any]) -> Self:
        """
        Processes the raw ECG data and assign these to class attributes
        performing resampling and lead augmentation if requested.
        
        Parameters
        ----------
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the XML
            content to class attributes. Specifically this should include
            dictionary attributes `MetaData`, `WaveForms`, `MedianBeats`,
            `OtherData`. The `MetaData` includes some required keys including
            essential information to describe an ECG instance, as well as
            non-required information. The difference between `OtherData` and
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
        **kwargs
            The keyword arguments for reader_tools.get_ecg_data. Note
            as_array is hard coded so this will raise an error if supplied as
            kwargs.
        
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
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes including the
            extracted XML data.
        """
        is_type(config, ConfigParser)
        is_type(skip_empty, bool)
        is_type(parse_numeric, bool)
        # update kwargs
        kwargs = {**{'parse_numeric': parse_numeric,
                     'skip_empty': skip_empty,
                     }, **kwargs}
        # #### extract metadata
        meta_data, meta_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=config.get_section(CTypes.MetaData),
                **kwargs,
            )
        # #### extract waveforms
        wave_data, wave_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=config.get_section(CTypes.WaveForms),
                as_array=True,
                **kwargs,
            )
        # #### extract median beats
        median_data, median_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=config.get_section(CTypes.MedianBeats),
                as_array=True,
                **kwargs,
            )
        # #### extract other data
        other_data, other_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=config.get_section(CTypes.OtherData),
                **kwargs,
            )
        # #### resample to 500hz
        # first calculate the duration
        try:
            meta_data[CProc.Duration] =\
                (meta_data[CMeta.SN_W]/meta_data[CMeta.SF]
            )
        except TypeError:
            meta_data[CProc.Duration] = None
        # only run when the parameter is True, SF is not 500 and there
        # is a duration
        meta_data[CProc.SF_NEW] = None
        if getattr(self, PXMLNam.RESAMPLE) == True:
            # confirm SF is present
            if not CMeta.SF in meta_data:
                raise KeyError(f'`{CMeta.SF}` is necessary to resample '
                               'the ECG signal.')
            # if it is, check whether there is a need to resample the signals.
            if int(meta_data[CMeta.SF]) != 500 and\
                    not meta_data[CProc.Duration] is None:
                # set the new SF
                meta_data[CProc.SF_NEW] = 500
                # confirm there is waveform data
                if len(wave_missing) == 12:
                    if skip_empty == False:
                        raise AttributeError(
                            Error_MSG.MISSING_SIGNAL.format('waveform'))
                else:
                    wave_data = ecg_utils.resampling_500hz(
                        wave_data, duration=meta_data[CProc.Duration])
                # confirm there is median beats data
                if len(median_missing) == 12:
                    if skip_empty == False:
                        raise AttributeError(
                            Error_MSG.MISSING_SIGNAL.format('median beat'))
                else:
                    median_data = ecg_utils.resampling_500hz(
                        median_data, median=True)
        # ### See if we need to get the augmented leads
        if getattr(self, PXMLNam.AUG_LEADS) == True and len(wave_missing) > 0:
            wave_data = ecg_utils.get_limb_leads(wave_data)
            median_data = ecg_utils.get_limb_leads(median_data)
        # ### do we print missing tags
        if self.verbose == True:
            missing_tags=meta_missing+wave_missing+median_missing+other_missing
            if len(missing_tags)>0:
                warnings.warn(Warn_MSG.MISSING_TAG.format(missing_tags))
        # #### assing stuff to attributes
        setattr(self, CTypes.MetaData, meta_data)
        setattr(self, CTypes.OtherData, other_data)
        setattr(self, CTypes.WaveForms, wave_data)
        setattr(self, CTypes.MedianBeats, median_data)
        # #### return stuff
        return self

