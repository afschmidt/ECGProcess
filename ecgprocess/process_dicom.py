'''
A module to extract, metadata, median beats and raw waveforms from ECGs DICOM
wrapping pydicom.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import pathlib
import pydicom
import warnings
import numpy as np
import ecgprocess.utils.reader_tools as reader_utils
from ecgprocess.process_xml import ECGXMLReader
from dataclasses import dataclass, field
from typing import (
    Self, Dict, Any, Optional
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    _check_readable,
)
from ecgprocess.utils.general import(
    parse_number,
)
from ecgprocess.constants import (
    ProcessXMLNames as PXMLNam,
    ProcessDicomNames as PDNames,
    CoreData as Core,
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
    dicom_tags = ManagedProperty(PDNames.DICOM_TAGS, list)
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
        getattr(type(self), PDNames.DICOM_TAGS).set_with_setter(
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
        pattern : `dict` [`str`, `str`]
            A dictionary where each key is a prefix to match against the keys of
            `data`, and each value defines the suffix to search within the matching
            keys in `data`. The value found in `data` corresponding to this suffix
            is used as the prefix for the resulting dictionary keys.
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


