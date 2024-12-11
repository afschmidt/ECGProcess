'''
A module to extract, metadata, median beats and raw waveforms from ECGs DICOM
wrapping pydicom.
'''

# NOTE should also rename skip_missing to file_errors usign the same Literals
# but replacing None by Error.


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import pathlib
import pydicom
import warnings
import numpy as np
import ecgprocess.utils.reader_tools as reader_utils
from dataclasses import dataclass, field
from typing import (
    Self, Dict, Any
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    _check_readable,
)
from ecgprocess.constants import (
    ProcessDicomNames as PDNames,
    CoreData as Core,
)
from ecgprocess.utils.reader_tools import(
    BaseReader,
)
from ecgprocess.utils.general import(
    ManagedProperty,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CLeads = Core.Leads
CMeta = Core.MetaData
CProc = Core.ProcessingData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGDICOMReader(BaseReader):
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
    dicom_tags = ManagedProperty(PDNames.DICOM_TAGS, list)
    raw_data = ManagedProperty(CProc.RAW, dict)
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
        dicom_tags : `list` [`str`]
            A list of strings with parsed DICOM tags matching the `raw_data` keys.
        raw_data : `dict` [`str`, `any`]
            The raw parsed DICOM data.
        
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
        # #### validate XML
        ds = pydicom.dcmread(path)
        # map to flatten_dict
        dicom_dict = reader_utils.flatten_dict(
            reader_utils.dicom_to_dict(ds),
            skip_root=False,
            **kwargs,
        )
        # ### store keys and data
        getattr(type(self), CProc.RAW).set_with_setter(self, dicom_dict)
        getattr(type(self), PDNames.DICOM_TAGS).set_with_setter(
            self, list(dicom_dict.keys()))
        # ### return
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
