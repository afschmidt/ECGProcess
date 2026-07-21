import re
import warnings
from dataclasses import dataclass, field
from typing import Optional, Any, Self, Literal
from ecgprocess.constants import (
    CoreData as Core,
    UtilsConfigData as ConfigNames,
)
from ecgprocess.errors import (
    InputValidationError,
    is_type,
    Error_MSG,
    NotCalledError,
    _check_is_file,
)
from ecgprocess.utils.general import ManagedProperty

"""
Classes to handle and parse configuration files describing how the XML/DICOM
tags should be assigned to dataclass attributes.
"""

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# constants
CTypes = Core.DataTypes
CLeads = Core.Leads
CMeta  = Core.MetaData

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class PrivilegedData(object):
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
    >>> required = PrivilegedData()
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
    # persist between instances.
    # NOTE using a single _ instead of __ to prevent name mangling.
    _data: dict[str, str] = field(default_factory=lambda: {
        CMeta.UID     : None,
        CMeta.NLEADS  : None,
        CMeta.RES_U_W : None,
        CMeta.RES_U_M : None,
        CMeta.RES_W   : None,
        CMeta.RES_M   : None,
        CMeta.SF      : None,
        CMeta.SF_U    : None,
        CMeta.SN_W    : None,
        CMeta.SN_M    : None,
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
class OtherData(PrivilegedData):
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
    # overwrite _data from PrivilegedData
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
    WaveForms : `dict` [`str`, `str`]
        A config dict mapping ECG leads.
    MedianBeats : `dict` [`str`, `str`]
        A config dict mapping ECG leads.
    MetaData : `dict` [`str`, `str`]
        A dictionary containing metadata attributes and their values.
    OtherData : `dict` [`str`, `str`], default `NoneType`
        An optional dictionary for additional data mappings.
    extra_leads : `tuple` [`str`], default `()`
        Additional lead names to accept in WaveForms/MedianBeats
        sections beyond the standard 12.
    
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
    >>> data_map_with_extra = DataMap(extra_leads=('V7', 'V3R'))
    >>> 'V7' in data_map_with_extra.WaveForms
    True
    
    Notes
    -----
    The class is intended to work in conjunction with a config file processed
    using `ConfigParser.map(DataMap)`. DataMap ensures any privileged
    attributes omitted from the config are added and set to None, and prevents
    the config file to be altered after processing. Extra lead names can be
    specified to extend the standard 12-lead set.
    """
    # setting attributes
    WaveForms: dict = field(default_factory=lambda: PrivilegedData(
        _data=DataMap.get_leads()).to_dict())
    MedianBeats: dict = field(default_factory=lambda: PrivilegedData(
        _data=DataMap.get_leads()).to_dict())
    MetaData: dict = field(default_factory=lambda: PrivilegedData().to_dict())
    OtherData: dict | None = None
    extra_leads: tuple[str, ...] = field(default_factory=tuple)
    _VALIDATE_ATTR = (
        ConfigNames.WaveForms, ConfigNames.MedianBeats,
        ConfigNames.MetaData, ConfigNames.OtherData
    )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def get_leads():
        """Initialising the leads names to None"""
        return {lead: None for lead in CLeads.values()}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        """Validating inputs."""
        is_type(self.WaveForms, dict, 'WaveForms')
        is_type(self.MedianBeats, dict, 'MedianBeats')
        is_type(self.MetaData, dict, 'MetaData')
        is_type(self.OtherData, (type(None), dict), 'OtherData')
        is_type(self.extra_leads, (tuple, list), 'extra_leads')
        # #### validate extra_leads content
        standard_leads = set(self.get_leads().keys())
        extra_set = set()
        for lead in self.extra_leads:
            is_type(lead, str, 'extra_leads element')
            if lead in standard_leads:
                raise InputValidationError(
                    Error_MSG.EXTRA_LEAD_RESERVED.format(lead))
            if lead in extra_set:
                raise InputValidationError(
                    Error_MSG.EXTRA_LEAD_DUPLICATE.format(lead))
            extra_set.add(lead)
        # #### merge extra leads into WaveForms and MedianBeats
        for lead in self.extra_leads:
            self.WaveForms[lead] = None
            self.MedianBeats[lead] = None
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
            res = list(self._VALIDATE_ATTR)
        else:
            res = [at for at in self._VALIDATE_ATTR
                   if getattr(self, at) is not None]
        return res
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def keys(self, attr_name: str | None = None,) -> list[str]:
        """
        Return the keys for WaveForms, MedianBeats, MetaData, OtherData, or
        all dictionaries.
        
        Parameters
        ----------
        attr_name : `str`, default `NoneType`
            Specify attribute name to limit the result to that dictionary. If
            None, keys for all dictionaries are returned, without attempting
            to unique these.
        
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
    def items(self, attr_name: str|None = None) -> dict[str, dict[str, str]]:
        """
        Return the key-value pairs forWaveForms, MedianBeats, MetaData,
        OtherData, or all dictionaries.
        
        Parameters
        ----------
        attr_name : `str`, default `NoneType`
            Specify the type of attribute to limit the result to that
            dictionary.  If None, items for all dictionaries are returned.
        
        Returns
        -------
        `dict` [`str`, `dict`  [`str`, `str`]
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
        result = {attr:{} for attr in attributes}
        for attr in attributes:
            attr_sub = getattr(self, attr, None)
            try:
                result[attr].update(attr_sub.items())
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
    
    Notes
    -----
    Required call sequence::
    
        parser = ConfigParser(path)()   # parse the file
        parser.map(mapper)              # map sections to a DataMap
        parser.get_section(name)        # retrieve a section
    
    Calling `get_section()` before `map()` raises `NotCalledError`.
    """
    # properties
    path = ManagedProperty(ConfigNames.path)
    _data = ManagedProperty(ConfigNames.data, dict)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, path:str):
        '''
        Initialize the ConfigParser instance.
        '''
        # making sure the setter is only used during _init_
        getattr(type(self),ConfigNames.path).set_with_setter(self, path)
        getattr(type(self),ConfigNames.data).set_with_setter(self, {})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __eq__(self, other):
        """
        Determine how instances are compared.
        """
        if len(getattr(self, ConfigNames.data)) == 0:
            if self.path == other.path and self._data == other._data:
                return True
        elif hasattr(self, ConfigNames.MAPPER) and\
            hasattr(other, ConfigNames.MAPPER):
            if getattr(self, ConfigNames.MAPPER) ==\
                    getattr(other, ConfigNames.MAPPER):
                return True
        elif  self._data == other._data:
            return True
        return False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(self) -> Self:
        """
        Parse the configuration file.
        
        This method reads the configuration file specified during
        initialization, validates its structure, and stores the data in a
        dictionary. It supports sections with key-value pairs.
        
        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        IsADirectoryError
            If the configuration path exists but is not a regular file.
        ValueError
            If a parsed line does not contain a tab delimiter.
        InputValidationError
            If a value-key pair is duplicated within the same section.
        """
        current = None
        path = getattr(self, ConfigNames.path)
        _check_is_file(path)
        with open(path, "r", encoding="utf-8") as file:
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
                    # confirm this is not already in data - fine if it is,
                    # no need to create a new key and subdict.
                    # can just add new entries.
                    if current not in getattr(self, ConfigNames.data):
                        getattr(self, ConfigNames.data)[current] = {}
                # skip if there is a comment
                elif re.match(r"^\s*#", line):
                    continue
                elif current and line:
                    # Process the line
                    if "\t" in line:
                        # Split into key-value pairs
                        k, v = re.split(r'\t+', line, maxsplit=1)
                        # include a strip to make sure spaces are trimmed
                        if not k.strip() in\
                                getattr(self, ConfigNames.data)[current]:
                            getattr(self, ConfigNames.data)[current][k.strip()]=\
                                v.strip()
                        else:
                            raise InputValidationError(
                                f"`{k.strip()}` has already been set: "
                                f"{getattr(self, ConfigNames.data)[current]}. "
                                "Please ensure a single unique name has been "
                                "supplied for each variable."
                            )
                    else:
                        raise ValueError("Missing tab delimiter.")
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def map(self, mapper:DataMap) -> None:
        """
        Maps the parsed data to a supplied `DataMap` instance.
        
        Attributes
        ----------
        mapper : `DataMap`
            An instance of the `DataMap` class, which is expected to have
            attributes corresponding to the parsed data sections (e.g., headers
            or types). These attributes will be updated with the data parsed by
            this class. Can optionally include `extra_leads` to extend the
            standard 12-lead set.
        
        Notes
        -----
        The method does not return anything and simply creates the `mapper`
        attribute.
        """
        WRONG = ('Attribute `{}` is outside the allowed key set for `{}`.'
                 'Please update your configuration file to only list allowed '
                 'attribute names, or specify additional lead names in '
                 'mapper.extra_leads. For example, consult the mapper object.')
        # ### make sure the instance was called
        if len(getattr(self, ConfigNames.data)) == 0:
            raise NotCalledError
        # ### check input
        missing = [a for a in getattr(self, ConfigNames.data).keys() if\
                   not hasattr(mapper, a)]
        if len(missing) > 0:
            raise AttributeError(
                f"The following parsed data types are not defined as "
                f"attributes in the provided mapper instance: "
                f"{', '.join(missing)}. Please ensure the mapper has "
                f"corresponding attributes for all required data types."
            )
        # ### class instances
        # setting up the signal data with extra_leads
        standard_leads = mapper.get_leads()
        extra_leads_dict = {l: None for l in mapper.extra_leads}
        combined_leads = {**standard_leads, **extra_leads_dict}
        wave_data = PrivilegedData(_data=combined_leads.copy())
        median_data = PrivilegedData(_data=combined_leads.copy())
        lead_keys = combined_leads.keys()
        # setting up the meta/other data
        meta_data_req = PrivilegedData()
        req_keys = meta_data_req.keys()
        meta_data_other = OtherData()
        other_data = OtherData()
        for key, d in getattr(self, ConfigNames.data).items():
            for k, v in d.items():
                if key == ConfigNames.MedianBeats:
                    if k in lead_keys:
                        median_data.update_values(**{k:v})
                    else:
                        raise KeyError(WRONG.format(k, key))
                elif key == ConfigNames.WaveForms:
                    if k in lead_keys:
                        wave_data.update_values(**{k:v})
                    else:
                        raise KeyError(WRONG.format(k, key))
                elif key == ConfigNames.MetaData:
                    # identify the required keys
                    if k in req_keys:
                        meta_data_req.update_values(**{k:v})
                    else:
                        meta_data_other.update_values(**{k:v})
                else:
                    # the non-meta data
                    other_data.update_values(**{k:v})
        # #### set attributes
        # set meta-data and other data
        setattr(mapper, ConfigNames.OtherData, other_data.to_dict())
        setattr(mapper, ConfigNames.WaveForms, wave_data.to_dict())
        setattr(mapper, ConfigNames.MedianBeats, median_data.to_dict())
        setattr(mapper, ConfigNames.MetaData,
                {**meta_data_req.to_dict(),
                 **meta_data_other.to_dict()}
                )
        setattr(self, ConfigNames.MAPPER, mapper)
        # # return stuff
        # return mapper
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_section(self,
                    section_name:Literal['MetaData', 'WaveForms', 'MedianBeats',
                                         'OtherData'],
                    declared_only:bool=False,
                    ) -> dict[str, str]:
        """
        Retrieve the parsed data for a specific section of the configuration
        file.
        
        Parameters
        ----------
        section_name : {'MetaData', 'WaveForms', 'MedianBeats', 'OtherData'}
            Name of the section to retrieve.
        declared_only : `bool`, default `False`
            Whether to return the default 12 lead template with a `None`
            mapping for every lead the config does not declare, or instead
            only return the config declared mappings.
        
        Returns
        -------
        section : `dict` [`str`, `str`]
            A dictionary of key-value pairs for the requested section.
        
        Raises
        ------
        NotCalledError
            If `map()` has not been called before this method.
        ValueError
            If `section_name` is not one of the allowed section names.
        KeyError
            If the requested section has no data.
        """
        is_type(section_name, str)
        is_type(declared_only, bool)
        SECTION_NAME = [ConfigNames.OtherData, ConfigNames.WaveForms,
            ConfigNames.MedianBeats, ConfigNames.MetaData]
        # confirm the choice is correct
        if not section_name in SECTION_NAME:
            raise ValueError(Error_MSG.CHOICE_PARM.\
                             format('section_name', ', '.join(SECTION_NAME)))
        # confirm mapper has been run
        if not hasattr(self, ConfigNames.MAPPER):
            raise NotCalledError('`map()` must be called before `get_section()`.')
        # get the correct attribute
        res = getattr(getattr(self, ConfigNames.MAPPER), section_name)
        if res is None:
            raise KeyError(f"key {section_name} is not available.")
        # Return declared config keys/leads only.
        # NOTE remember to add a pytest for this
        if declared_only:
            res = {key: value for key, value in res.items()
                   if value is not None}
        return res
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self):
        """String representation of the parsed data."""
        result = [f"{self.__class__.__name__}"]
        if not getattr(self, ConfigNames.data):
            j = ""
            result.append(f"path={getattr(self,ConfigNames.path)}")
        else:
            j = "\n"
            # Determine the maximum key length for alignment
            max_key_length = max(
                (len(key) for _, attr in getattr(self, ConfigNames.data).items()
                 for key in attr.keys()), default=0)
            for section, attributes in getattr(self, ConfigNames.data).items():
                result.append(f"[{section}]")
                for key, value in attributes.items():
                        # Align values by padding keys
                        result.append(f"\t{key:<{max_key_length}}    {value}")
                result.append("")
        return j.join(result)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self):
        """Developer-friendly representation of the parsed data."""
        result = [f"{self.__class__.__name__}("]
        if not getattr(self, ConfigNames.data):
            j = ""
            result.append(f"path={getattr(self, ConfigNames.path)}")
        else:
            j = "\n"
        # Determine the maximum key length for alignment
        max_key_length = max(
            (len(key) for _, attr in getattr(self, ConfigNames.data).items()
             for key in attr.keys()), default=0)
        for section, attributes in getattr(self, ConfigNames.data).items():
            result.append(f"  [{section}]")
            for key, value in attributes.items():
                # Align values by padding keys
                result.append(f"\t{key:<{max_key_length}}    {value}")
        result.append(")")
        return j.join(result)
