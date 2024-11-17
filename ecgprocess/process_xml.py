#!/usr/bin/env python3
'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''

from dataclasses import dataclass
from typing import (
    Self, Any, Literal,
)
from ecgprocess.process_dicoms import (
    BaseECGDICOMReader,
)
from ecgprocess.utils.general import(
    validate_xml,
)
from ecgprocess.errors import (
    is_type,
    _check_readable,
    _check_presence,
    Error_MSG,
)

from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The extraction class to process an config file
@dataclass
class ExtractionBase:
    table1: str = "default_value1"
    table2: str = "default_value2"
    table3: str = "default_value3"

    def update(self, **kwargs):
        for key, value in kwargs.items():
            # Add or update attributes dynamically
            setattr(self, key, value)

# Create a subclass where default values can be set again
@dataclass
class ExtractionConfig(ExtractionBase):
    table1: str = "new_default_value1"
    table2: str = "new_default_value2"
    # Optionally add new attributes if needed
    table4: str = "additional_default_value"

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
    
    Methods
    -------
    TODO
    
    Notes
    -----
    The waveforms are stored using `__slots__` to decrease memory usage, which
    is further improved by setting `retain_raw` to `False` - the default
    behaviour.
    """
    # #### parameters, with defaults
    augment_leads: bool=False
    resample_500:bool=True
    retain_raw:bool=False
    # #### check input
    is_type(augment_leads, bool)
    is_type(resample_500, bool)
    # #### Error MSG
    __MSG1=('Please supply either `path` or `xml_tree` but not both.')
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, extractor:ExtractionConfig,
                 validate:Literal['Full', 'Partial', 'Skip']='Full',
                 skip_empty:bool=True, verbose:bool=False,
                 ) -> Self:
        """
        Reads a `.xml` file containing ECG readings and extracts  metadata,
        raw waveforms, and median beats data, with the exact naming based on the
        `extractor` instance.
        
        Parameters
        ----------
        path : `str`
            The path to the .xml file.
        extract : `ExtractionConfig`
            The class instance mapping the parsed XML content to attribute names.
        validate : `str`, default `Full`
            Whether the xml file should be validated based in a supplied `.xsd`
            scheme supplied to the `extract` instance. `Full` will perform a full
            validation. `Partial` will filer out issues with elements in the xml
            file which are omitted in the schema.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose : `bool`, default `False`
            Prints missing tags if skip_empty is set to `True`.
        
        Attributes
        ----------
        GeneralInfo : `list` [`str`]
            A list of extracted attributes.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianWaveforms : `dict` [`str`, `np.array`]
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
        is_type(skip_empty, bool)
        is_type(verbose, bool)
        is_type(extractor, ExtractionConfig)
        is_type(validate, str)
        # assign to self
        self.verbose = verbose
        # #### confirm file is readable
        _check_readable(path)
        # #### validate XML
        VALIDATE_CHOICES = [PDNames.XML_VAL_FULL,
                            PDNames.XML_VAL_PART,
                            PDNames.XML_VAL_SKIP,
                            ]
        if not validate in VALIDATE_CHOICES:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('validate', ', '.join(VALIDATE_CHOICES)))
        # NOTE add the validation step here, need to define extractor first
