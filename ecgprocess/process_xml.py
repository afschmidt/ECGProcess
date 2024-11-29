'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''

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
    TODO
    
    Notes
    -----
    The waveforms are stored using `__slots__` to decrease memory usage, which
    is further improved by setting `retain_raw` to `False` - the default
    behaviour.
    """
    # #### properties
    # NOTE add these to the docstring
    xml_tags = prop_fac(PXMLNam.XML_TAGS, once=True)
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
        xml_dict = flatten_dict(xml_to_dict(parsed_xml), **kwargs)
        xml_dict = flatten_dict(xml_to_dict(parsed_xml))
        # ### store keys
        setattr(self, PXMLNam.XML_DICT, xml_dict)
        setattr(self, PXMLNam.XML_TAGS, list(xml_dict.keys()))
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


