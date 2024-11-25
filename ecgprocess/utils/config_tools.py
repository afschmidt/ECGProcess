from dataclasses import dataclass, field
from typing import Optional, Any, Self
from ecgprocess.constants import (
    CoreData as CDNames,
    UtilsConfigData as ConfigNames,
)
from ecgprocess.errors import (
    InputValidationError,
    is_type,
    Error_MSG,
    NotCalledError,
)

"""
Classes to handle and parse configuration files describing how the XML/DICOM
tags should be assigned to dataclass attributes.
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
    # NOTE using a single _ instead of __ to prevent name mangling.
    _data: dict[str, str] = field(default_factory=lambda: {
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
            if key not in self._data:
                raise KeyError(f"Key '{key}' is not a valid attribute for "
                               f"{CLASS_NAME}.")
            self._data[key] = val
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def keys(self) -> list[str]:
        """
        Returns the required keys.
        """
        return list(self._data.keys())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def to_dict(self) -> dict[str, str]:
        """
        Returns the required data as a dictionary.
        """
        return self._data

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class OtherData(RequiredData):
    """
    A class to map internal attribute names to DICOM/XML tags and collect data
    based on optional attributes.
    
    Methods
    -------
    update_values(**kwargs)
        Update the values of existing dictionary keys.
    to_dict()
        Returns the current dictionary.
    keys()
        Returns the dictionary keys.
    """
    # overwrite _data from RequiredData
    _data: Optional[dict[str, str]] = field(default_factory=dict)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def update_values(self, **kwargs:Optional[Any]) -> None:
        """
        Update the dictionary key and values.
        
        Parameters
        ----------
        **kwargs : `dict` [`str`, `str`]
            Key-value pairs mapping DICOM/XML tags (values) to attribute names
            (keys).
        
        """
        for key, val in kwargs.items():
            self._data[key] = val

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
    get_attributes(all_)
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
    _VALIDATE_ATTR = (ConfigNames.MetaData, ConfigNames.OtherData)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        """Validating inputs."""
        is_type(self.WaveForms, str, 'WaveForms')
        is_type(self.MedianBeats, str, 'MedianBeats')
        is_type(self.MetaData, dict, 'MetaData')
        is_type(self.OtherData, (type(None), dict), 'OtherData')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @property
    def VALIDATE_ATTR(self) -> tuple:
        """
        Exposes _VALIDATE_ATTR as a read-only property.
        """
        return self._VALIDATE_ATTR
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_attributes(self, all_:bool=False) -> list[str]:
        """
        Returns the names of attributes with non-None values.
        
        Attributes
        ---------
        all_ : `bool`, default `False`
            Whether to return all keys irrespective of whether their values are
            equal to None.
        Returns
        -------
        list [`str`]
            A list of attribute names where the value is not None.
        """
        is_type(all_, bool)
        if all_ == True:
            res = list(self.__dict__.keys())
        else:
            res = [at for at, val in self.__dict__.items() if val is not None]
        return res
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
        if not attr_name in self._VALIDATE_ATTR and not attr_name is None:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('attr_name', ', '.join(self._VALIDATE_ATTR)))
        # find keys
        attributes = self._VALIDATE_ATTR if attr_name is None else [attr_name]
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
        if not attr_name in self._VALIDATE_ATTR and not attr_name is None:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('attr_name', ', '.join(self._VALIDATE_ATTR)))
        # find keys
        attributes = self._VALIDATE_ATTR if attr_name is None else [attr_name]
        result = {}
        for attr in attributes:
            attribute = getattr(self, attr, None)
            try:
                result.update(attribute.items())
            except (AttributeError, TypeError):
                pass
        return result

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ConfigParser(object):
    """
    Parses configuration files into structured data and optionally assigns this
    to a user supplied mapper instance.
    
    Parameters
    ----------
    path : str
        Path to the configuration file to be parsed.
    """
    def __init__(self, path:str):
        '''
        Initialize the ConfigParser instance.
        '''
        self._path = path
        self.__data = {}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @property
    def path(self) -> str:
        """
        Exposes _path as a read-only property.
        """
        return self._path
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @property
    def data(self) -> str:
        """
        Exposes _data as a read-only property.
        """
        return self.__data
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self) -> Self:
        """
        Parse the configuration file.
        
        This method reads the configuration file specified during
        initialization, validates its structure, and stores the data in a
        dictionary. It supports sections with key-value pairs or single values.
        """
        current = None
        with open(self._path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    # Start a new section
                    current = line.strip("[]")
                    # check if the attribute type is allowed
                    if hasattr(ConfigNames, current) == False:
                        raise AttributeError(
                            f"Encountered an unknown data type or malformed "
                            f"input: `{current}`. Ensure the file format is "
                            "correct and all sections are properly defined."
                        )
                    # confirm this is not already in __data - fine if it is,
                    # but no need to create a new key and subdict.
                    if current not in self.__data:
                        self.__data[current] = {}
                elif current and line:
                    # Process the line
                    if "\t" in line:
                        # Split into key-value pairs
                        k, v = line.split("\t", 1)
                        self.__data[current][k.strip()] = v.strip()
                    else:
                        # in this case this should be a WaveForm or MedianBeat
                        # attribute
                        if len(self.__data[current]) == 0:
                            self.__data[current][current] = line.strip()
                        else:
                            raise InputValidationError(
                                f"`{current}` has already been set: "
                                f"{self.__data[current][current]}. Please "
                                "ensure a single values has been set for data "
                                "type."
                            )
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def map(self, mapper:DataMap) -> DataMap:
        """
        Maps the parsed data to a supplied `DataMap` instance.
        
        Attributes
        ----------
        mapper : `DataMap`
            An instance of the `DataMap` class, which is expected to have
            attributes corresponding to the parsed data sections (e.g., headers
            or types). These attributes will be updated with the data parsed by
            this class.
        
        Returns
        -------
        DataMap
            The same `DataMap` instance provided as input, but with its attributes
            updated to include the parsed data.
        """
        # ### make sure the instance was called
        if len(self.__data) == 0:
            raise NotCalledError
        # ### check input
        missing = [a for a in self.__data.keys() if not hasattr(mapper, a)]
        if len(missing) > 0:
            raise AttributeError(
                f"The following parsed data types are not defined as "
                f"attributes in the provided mapper instance: "
                f"{', '.join(missing)}. Please ensure the mapper has "
                f"corresponding attributes for all required data types."
            )
        # ### class instances
        meta_data_req = RequiredData()
        req_keys = meta_data_req.keys()
        meta_data_other = OtherData()
        other_data = OtherData()
        for key, d in self.__data.items():
            if key in [ConfigNames.MedianBeats, ConfigNames.WaveForms]:
                try:
                    setattr(mapper, key, list(d.values())[0])
                except IndexError:
                    setattr(mapper, key, None)
                # moving to the next key
                continue
            for k, v in d.items():
                if key == ConfigNames.MetaData:
                    # identify the required keys
                    if k in req_keys:
                        meta_data_req.update_values(**{k:v})
                    else:
                        meta_data_other.update_values(**{k:v})
                else:
                    # the non-meta data
                    other_data.update_values(**{k:v})
            # NOTE this will only be triggered for meta/other data
            if key == ConfigNames.MetaData:
                # set meta-data and other data
                setattr(mapper, key,
                        {**meta_data_req.to_dict(),
                         **meta_data_other.to_dict()}
                        )
            else:
                setattr(mapper, key, other_data.to_dict())
        # return stuff
        return mapper
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_section(self, section_name):
        """
        Retrieve the parsed data for a specific section of the configuration
        file.
        
        Parameters
        ----------
        section_name : `str`
            Name of the section to retrieve.
        
        Returns
        -------
        dict
            A dictionary of key-value pairs for the requested section, or an
            empty dictionary if the section does not exist.
        """
        return self.__data.get(section_name, {})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self):
        """String representation of the parsed data."""
        result = [f"{self.__class__.__name__}"]
        if not self.__data:
            j = ""
            result.append(f"path={self._path}")
        else:
            j = "\n"
            for section, attributes in self.__data.items():
                result.append(f"[{section}]")
                for key, value in attributes.items():
                        result.append(f"  {key}  {value}")
                result.append("")
        return j.join(result)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self):
        """Developer-friendly representation of the parsed data."""
        result = [f"{self.__class__.__name__}("]
        if not self.__data:
            j = ""
            result.append(f"path={self._path}")
        else:
            j = "\n"
            for section, attributes in self.__data.items():
                result.append(f"  [{section}]")
                for key, value in attributes.items():
                    result.append(f"    {key}  {value}")
        result.append(")")
        return j.join(result)
