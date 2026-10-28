"""
A module for extracting metadata, median beats, and raw waveforms from ECG
XML files, allowing for XML validation.

This module provides an API through a reader class, which maps ECG data from
XML files to class attributes. These attributes can be programmatically accessed
and further processed by downstream ECGprocess modules or external programs
leveraging the API.
"""

import pathlib
import ecgprocess.utils.reader_tools as reader_utils
from lxml import etree
from ecgprocess.process.process_base import(
    BaseReader,
)
from dataclasses import dataclass, field
from typing import (
    Optional, Self, Any,
)
from ecgprocess.utils.general import(
    ManagedProperty,
)
from ecgprocess.errors import (
    is_type,
    _check_readable,
)
from ecgprocess.constants import (
    ProcessXMLNames as PXMLNam,
    CoreData as Core,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CProc = Core.ProcessingData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGXMLReader(BaseReader):
    """
    Processes an XML file containing ECG data and extracts the metadata,
    median beats, and raw waveforms.
    
    Parameters
    ----------
    augment_leads : `bool`, default `False`
        Whether the augmented leads should be calculated if these are not
        already available in the source file.
    resample_500 : `bool`, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz. Note this
        will internally calculate the ECG duration in seconds. For the
        duration to be in seconds the sampling frequency/rate should be in
        seconds not milliseconds.
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample_500 : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
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
        schema : `str`, default `NoneType`
            A path to an XML schema which will be used to validate the XML file
            against.
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
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes including the
            extracted XML data.
        
        Raises
        ------
        XMLValidationError
            If the XML file is not valid based on the supplied schema.
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
        # ### store keys and data
        getattr(type(self), CProc.RAW).set_with_setter(self, xml_dict)
        getattr(type(self), CProc.TAGS).set_with_setter(
            self, list(xml_dict.keys()))
        # ### return
        return self

