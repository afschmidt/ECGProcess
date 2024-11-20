from dataclasses import dataclass, field
from typing import Optional, Any
from ecgprocess.constants import (
    CoreData as CDNames,
    UtilsConfigData as ConfigNames,
)
from ecgprocess.errors import (
    is_type,
    Error_MSG,
)

"""
Classes describing the XML/DICOM tags/attributes which should be extracted from
the source files. The attributes are seperated by required and immutable
WaveForms, MedianBeats, and MetaData, as well as optional OtherData classes.

Includes functionallity to update the extraction instances based on a flat
config file.
"""

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class RequiredData(object):
    '''
    The core metadata dictionary, where the key values cannot not be changed
    because these are expected used by downstream programs. The values can
    however be user defined.
    
    Methods
    -------
    update_values(**kwargs)
        Update the values of existing dictionary keys.
    to_dict()
        Returns the current dictionary.
    keys()
        Returns the dictionary keys.
    
    Notes
    -----
    The values are initialised to `NoneType` these should be set to values
    relevant for the relevant XML/DICOM tags/attributes.
    
    Examples
    --------
    >>> required = RequiredData()
    >>> print(*required.keys(), sep='\n')
    unique identifier
    sampling frequency (original)
    sampling number (waveforms)
    sampling number (medianbeats)
    acquisition date
    study date
    channel number
    units (waveforms)
    units (medianbeats)
    '''
    # Defaults, using default_factory and lambda to make sure default do not
    # presist between instances.
    data: dict[str, str] = field(default_factory=lambda: {
        CDNames.MD_UID : None,
        CDNames.MD_SF  : None,
        CDNames.MD_SN  : None,
        CDNames.MD_SNM : None,
        CDNames.MD_AT  : None,
        CDNames.MD_SD  : None,
        CDNames.MD_CN  : None,
        CDNames.MD_WU  : None,
        CDNames.MD_MU  : None,
    })
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def update_values(self, **kwargs:Optional[Any]) -> None:
        """
        Update the values of existing immutable keys.
        
        Parameters
        ----------
        **kwargs : `dict` [`str`, `str`]
            Key-value pairs where the key is a required data field and the
            value is the updated DICOM/XML tag.
        
        Raises
        ------
        KeyError
            If a key in `kwargs` is not a valid required data field.
        """
        CLASS_NAME = type(self).__name__
        for key, val in kwargs.items():
            if key not in self.data:
                raise KeyError(f"Key '{key}' is not a valid attribute for "
                               f"{CLASS_NAME}.")
            self.data[key] = val
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def keys(self) -> list[str]:
        """
        Returns the required keys.
        """
        return list(self.data.keys())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def to_dict(self) -> dict[str, str]:
        """
        Returns the required data as a dictionary.
        """
        return self.data

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class OtherData(RequiredData):
    """
    A class to map internal attribute names to DICOM/XML tags and collect data
    based on optional attributes.
    
    Parameters
    ----------
    data : `dict` [`str`, `str`], default `{}`
        A dictionary mapping internal attribute names to external tags
        (DICOM/XML) based on the key, value pairs.
    
    Methods
    -------
    to_dict()
        Collects data into a dictionary based only on optional attributes.
    keys()
        Returns the dictionary keys.
        
    """
    # overwrite __data from RequiredData
    data: Optional[dict[str, str]] = field(default_factory=dict)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # make sure update_values is not implemented.
    def update_values(self, **kwargs:Optional[Any]) -> None:
        """
        Disable the update_values functionality in this subclass.
        """
        CLASS_NAME = type(self).__name__
        raise NotImplementedError(f"`update_values` is not available in "
                                  f"{CLASS_NAME}.")

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class DataMap(object):
    """
    A class to manage and map metadata, waveforms, and median beats,
    and optionally, other data attributes.
    
    Attributes
    ----------
    WaveForms : `str`
        A tag or identifier for waveform data.
    MedianBeats : `str`
        A tag or identifier for median beats data.
    MetaData : `dict` [`str`, `str`]
        A dictionary containing metadata attributes and their values.
    OtherData : `dict` [`str`, `str`], default `NoneType`
        An optional dictionary for additional data mappings.
    
    Methods
    -------
    get_attributes()
        Returns the names of attributes with non-None values.
    keys(attr_name)
        Returns the keys of the specified dictionary ('MetaData' or
        'OtherData'), or both if no specific dictionary is specified.
    items(attr_name)
        Returns the key-value pairs of the specified dictionary ('MetaData' or
        'OtherData'), or both if no specific dictionary is specified.
    
    Examples
    --------
    >>> data_map = DataMap()
    >>> data_map.get_attributes()
    ['WaveForms', 'MedianBeats', 'MetaData']
    """
    WaveForms: str = field(default=CDNames.WaveForms)
    MedianBeats: str = field(default=CDNames.MedianBeats)
    MetaData: dict = field(default_factory=lambda: RequiredData().to_dict())
    OtherData: dict | None = None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_attributes(self) -> list[str]:
        """
        Returns the names of attributes with non-None values.
        
        Returns
        -------
        `list` [`str`]
            A list of attribute names where the value is not None.
        """
        return [at for at, val in self.__dict__.items() if val is not None]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def keys(self, attr_name: str | None = None,) -> list[str]:
        """
        Return the keys for MetaData, OtherData, or both dictionaries.
        
        Parameters
        ----------
        attr_name : `str`, default `NoneType`
            Specify 'MetaData' or 'OtherData' to limit the result to that
            dictionary.  If None, keys for both dictionaries are returned.
        
        Returns
        -------
        `list` [`str`]
            A list with dictionary keys.
        """
        # #### check input
        is_type(attr_name, (type(None), str))
        VALIDATE_ATTR = [ConfigNames.METADATA, ConfigNames.OTHERDATA]
        if not attr_name in VALIDATE_ATTR and not attr_name is None:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('attr_name', ', '.join(VALIDATE_ATTR)))
        # find keys
        attributes = VALIDATE_ATTR if attr_name is None else [attr_name]
        result = []
        for attr in attributes:
            attribute = getattr(self, attr)
            try:
                result = result + list(attribute.keys())
            except AttributeError:
                pass
        return result
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def items(self, attr_name: str|None = None) -> dict[str, str]:
        """
        Return the key-value pairs for MetaData, OtherData, or both
        dictionaries.
        
        Parameters
        ----------
        attr_name : `str`, default `NoneType`
            Specify 'MetaData' or 'OtherData' to limit the result to that
            dictionary.  If None, items for both dictionaries are returned.
        
        Returns
        -------
        `dict` [`str`, `str`]
            A dictionary where keys are attribute names and values are the
            key-value pairs of the dictionary.
        """
        # #### check input
        is_type(attr_name, (type(None), str))
        VALIDATE_ATTR = [ConfigNames.METADATA, ConfigNames.OTHERDATA]
        if not attr_name in VALIDATE_ATTR and not attr_name is None:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('attr_name', ', '.join(VALIDATE_ATTR)))
        # find keys
        attributes = VALIDATE_ATTR if attr_name is None else [attr_name]
        result = {}
        for attr in attributes:
            attribute = getattr(self, attr, None)
            try:
                result.update(attribute.items())
            except (AttributeError, TypeError):
                pass
        return result

# # Example Usage:

# # Define OtherData configuration
# other_data = OtherData(optional_attributes={
#     "TechnicianName": "TechnicianNameTag",
#     "DeviceModel": "DeviceModelTag"
# })

# # Create the ExtractionConfig instance
# config = ExtractionConfig(OtherData=other_data)

# # Update WaveForms and MedianBeats to custom values
# config.update(WaveForms="custom_waveforms_tag", MedianBeats="custom_median_beats_tag")

# # Update MetaData values
# config.MetaData.update_values(PatientName="CustomPatientTag")

# # Simulate source data for OtherData extraction
# source_data = {
#     "0010,0010": "John Doe",          # Patient Name
#     "0010,0020": "12345",             # Patient ID
#     "0008,0020": "2024-11-19",        # Study Date
#     "TechnicianNameTag": "Jane Smith",
#     "DeviceModelTag": "ECG-X100"
# }

# # Extract data using MetaData and OtherData
# meta_dict = config.MetaData.to_dict()
# other_dict = config.OtherData.to_dict(source_data) if config.OtherData else {}

# # Output results
# print("WaveForms:", config.WaveForms)  # Output: custom_waveforms_tag
# print("MedianBeats:", config.MedianBeats)  # Output: custom_median_beats_tag
# print("MetaData Extracted:", meta_dict)
# # Output: {'PatientName': 'CustomPatientTag', 'PatientID': '0010,0020', 'StudyDate': '0008,0020'}
# print("OtherData Extracted:", other_dict)
# # Output: {'TechnicianName': 'Jane Smith', 'DeviceModel': 'ECG-X100'}
# @dataclass
# class ExtractionBase:
#     table1: str = "default_value1"
#     table2: str = "default_value2"
#     table3: str = "default_value3"

#     def update(self, **kwargs):
#         for key, value in kwargs.items():
#             # Add or update attributes dynamically
#             setattr(self, key, value)

# # Create a subclass where default values can be set again
# @dataclass
# class ExtractionConfig(ExtractionBase):
#     table1: str = "new_default_value1"
#     table2: str = "new_default_value2"
#     # Optionally add new attributes if needed
#     table4: str = "additional_default_value"


