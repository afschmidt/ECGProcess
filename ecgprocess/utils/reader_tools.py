"""
Tools to help read and process ECG files.

Functions and classes are predominantly aimed to map ECG files to native
python objects such as dictionary and systematically process these. Functions
specifically focussed on ECG signals, such as calculating the limb leads,
are collected in `ecgprocess.utils.ecg_tools`.
"""

import re
import pydicom
import warnings
import xmltodict
import numpy as np
from lxml import etree
from pathlib import Path
from typing import (
    Optional, Self, Any, Literal, Type,
)
from ecgprocess.utils.general import(
    parse_number,
)
from ecgprocess.constants import (
    CoreData as Core,
    UtilsReaderNames as RNames,
)
from ecgprocess.errors import (
    is_type,
    MissingTagError,
    Error_MSG,
)
from ecgprocess.constants import UtilsGeneralNames as UGNames
from ecgprocess.errors import XMLValidationError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
WARN1 = "XML file is valid (ignoring XML elements not in the supplied XSD)."
CTypes = Core.DataTypes
CProc = Core.ProcessingData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Base class with slots
class BaseReader:
    '''
    An ECGDICOMReader base class implementing the more efficient __slots__ for
    the waveform arrays, while still retaining __dict__ dynamic attribute
    creation.
    '''
    __slots__ = (CTypes.WaveForms, CTypes.MedianBeats,
                 CTypes.MetaData, CTypes.OtherData, CProc.RAW)
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, waveforms=None, medianbeats=None, metadata=None,
                 otherdata=None, raw=None):
        '''
        Initialises slots entries to `None`.
        '''
        setattr(self, CTypes.WaveForms, waveforms)
        setattr(self, CTypes.MedianBeats,medianbeats)
        setattr(self, CTypes.MetaData,metadata)
        setattr(self, CTypes.OtherData, otherdata)
        setattr(self, CProc.RAW,raw)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def validate_xml(xml_path:str|Path, xsd_path:str|Path, strict:bool=True,
                 verbose:bool=True,
                 ) -> etree._ElementTree:
    """
    Validates an XML file against an XSD schema.
    
    Parameters
    ----------
    xml_path : `str` or `Path`
        Path to the XML file.
    xsd_path : `str` or `Path`
        Path to the XSD file.
    strict : `bool`, default `True`
        If False, ignores elements in the XML that are not in the XSD.
        
    Returns
    -------
    etree._ElementTree
        The parsed XML document.
    
    Raises
    ------
    XMLValidationError
        Raised if the XSD and XML are incompatible.
    """
    # #### Check input
    is_type(strict, bool)
    is_type(verbose, bool)
    is_type(xml_path, (str, Path))
    is_type(xsd_path, (str, Path))
    # #### Load the XSD schema
    with open(xsd_path, 'rb') as xsd:
        schema_root = etree.XML(xsd.read())
    schema = etree.XMLSchema(schema_root)
    # #### Parse the XML file
    with open(xml_path, 'rb') as xml:
        xml_doc = etree.parse(xml)
    # #### Compare XML against XSD
    is_valid = schema.validate(xml_doc)
    # #### Do we want to raise errors when XML elements are absent in the XSD
    if not is_valid and not strict:
        # if strict is False remove error relating to missing XSD elements
        errors = [err.message for err in schema.error_log]
        filtered_errs = [err for err in schema.error_log if\
                           not UGNames.LXML_ERROR in err.message]
        # check if there are any other type of errors
        is_valid = len(filtered_errs) == 0
        if is_valid:
            # Where there any errors to begin with
            if verbose == True and len(schema.error_log) > 0:
                warnings.warn(WARN1)
        else:
            errors = [err.message for err in filtered_errs]
            raise XMLValidationError(errors)
    elif is_valid == False:
        errors = [err.message for err in schema.error_log]
        raise XMLValidationError(errors)
    # return xml_doc
    return xml_doc

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def xml_to_dict(xml_doc:etree._ElementTree, encoding:str='utf-8',
                ) -> dict[str, Any]:
    """
    Converts an lxml ElementTree document to a dictionary.
    
    Parameters
    ----------
    xml_doc : `etree._ElementTree`
        A validated XML document.
    encoding : `str`, default `utf-8`
        
    Returns
    -------
    dict [`str`, `any`]
        A dictionary representation of the XML data.
    """
    is_type(encoding,str)
    is_type(xml_doc, etree._ElementTree)
    # convert to string
    xml_str = etree.tostring(xml_doc, encoding=encoding)
    # parste to dict
    xml_dict = xmltodict.parse(xml_str)
    # returning stuf.
    return xml_dict

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def dicom_to_dict(ds: pydicom.dataset.Dataset) -> dict[str, Any]:
    """
    Turn a pydicom Dataset into a dict with keys derived from the Element names.
    
    Parameters
    ----------
    ds : `pydicom.dataset.Dataset`
        The DICOM dataset to convert.
    
    Returns
    -------
    dict [`str`, `any`]
        A dictionary representation of the dataset.
    """
    output = {}
    for elem in ds:
        # SQ: sequences should be dealt with through recursion
        # Each sequence element contains a list of sub-elements
        # (nested datasets), which may themselves have multiple elements.
        if elem.VR != "SQ":
            output[elem.name] = elem.value
        else:
            output[elem.name] = [dicom_to_dict(item) for item in elem]
    # Extract waveform data if available
    if hasattr(ds, RNames.DICOM_WAVE_ARRAY):
        # Attempt to extract waveform data if the method exists
        waveform_data = {}
        # Extract the waveform data
        try:
            waveform_data["ECG_Leads"] = ds.waveform_array(0).T.tolist()
        except (IndexError, AttributeError):
            pass
        # Extract median beats
        try:
            waveform_data["Median_Beats"] = ds.waveform_array(1).T.tolist()
        except (IndexError, AttributeError):
            pass
        if waveform_data:
            output["WaveformData"] = waveform_data
    # return
    return output

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def flatten_dict(d:dict[str, Any], parent_prefix:str='', sep:str='.',
                 skip_root:bool=True,
                 ) -> dict[str, Any]:
    """
    Recursively flatten a nested dictionary, optionally skipping the root
    element.
    
    Parameters
    ----------
    d : dict
        The dictionary to flatten.
    parent_prefix : str, default ''
        The base string added as a prefix to all keys during recursion.
        Useful for maintaining context or indicating a higher-level structure.
    sep : str, default '.'
        The key separator
    skip_root : bool, default True
        If True, skips the first level (root) key.
    
    Returns
    -------
    dict
        A flattened dictionary where nested keys are concatenated into a single
        key.
    
    Examples
    --------
    >>> nested_dict = {
    ...     'a': {
    ...         'b': 1,
    ...         'c': {
    ...             'd': 2
    ...         }
    ...     }
    ... }
    >>> flatten_dict(nested_dict)
    {'b': 1, 'c.d': 2}
    
    >>> flatten_dict(nested_dict, skip_root=False)
    {'a.b': 1, 'a.c.d': 2}
    
    >>> flatten_dict(nested_dict, sep='_', skip_root=False)
    {'a_b': 1, 'a_c_d': 2}
    """
    # check input
    is_type(d, dict)
    is_type(parent_prefix, str)
    is_type(sep, str)
    is_type(skip_root, bool)
    # initiate empty results
    res = []
    # If skipping the root, adjust d to be the first nested dictionary level
    if skip_root and isinstance(d, dict) and len(d) == 1:
        _, d = next(iter(d.items()))
    # loop over the remaining keys and values
    for k, v in d.items():
        new_key = f"{parent_prefix}{sep}{k}" if parent_prefix else k
        # if v is dict, unpack
        if isinstance(v, dict):
            res.extend(flatten_dict(v, new_key, sep=sep, skip_root=False).items())
        # if v is list, unpack
        elif isinstance(v, list):
            for i, item in enumerate(v):
                # flatten lists
                if item is not None and isinstance(item, dict):
                    res.extend(flatten_dict(item, f"{new_key}_{i}",
                                            sep=sep, skip_root=False).\
                                 items())
                # otherwise add non-dict and None types
                else:
                    res.append((f"{new_key}_{i}", item))
        # otherwise simply assign
        else:
            res.append((new_key, v))
    return dict(res)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_ecg_data(data_dict:dict[str, Any],
                 config:dict[str, str],
                 parse_numeric:bool=True,
                 as_array:bool=False,
                 bits:np.dtype | None =None,
                 skip_empty:bool=True,
                 **kwargs:Optional[Any],
                 ) -> tuple[dict[str, Any], list[str]]:
    '''
    Extracts metadata or signal data from a `data_dict` based on a supplied
    `config` dictionary.
    
    Parameters
    ----------
    data_dict : `dict` [`str`, `any`]
        A dictionary with keys and values matching the config object
    config : `dict` [`str`, `str`]
        a dictionary where the values match some keys in `data_dict` and the
        keys represent the names these will be stored to.
    parse_numeric : `bool`, default `True`
        Will check if a numbers are accidentally presented as strings and parse
        these to numbers.
    as_array : `bool`, default `False`
        Whether data should be mapped to `np.array` using a direct map:
        `np.array(., dtype=bits)`.
    bits : `np.dtype`, default `None`
        np.array bits passed to numpy.array dtype.
    skip_empty : `bool`, default `True`
        Whether to skip config values not matching data_dict keys.
    **kwargs,
        keyword arguments to `parse_number`.
    
    Returns
    -------
    dict
        A dictionary with the extracted signal data as numpy.ndarray.
    list
        A list with `config` values which did not match `data_dict` keys.
    
    '''
    # #### check input
    is_type(data_dict, dict)
    is_type(config, dict)
    is_type(skip_empty, bool)
    is_type(as_array, bool)
    is_type(parse_numeric, bool)
    # #### initialise object
    results_dict = {}
    results_missing = []
    # #### extract signal data
    for t, s in config.items():
        if s in data_dict:
            # Check if numerics are accidentally strings.
            if parse_numeric:
                parsed_string = parse_number(data_dict[s], **kwargs)
                results_dict[t] = parsed_string
                if isinstance(parsed_string, list):
                    if len(parsed_string) == 1:
                        results_dict[t] = parsed_string[0]
            else:
                results_dict[t] = data_dict[s]
            # Do we want to extract signals and store these in a numpy array..
            if as_array == True:
                try:
                    results_dict[t] = np.array(results_dict[t], dtype=bits)
                except ValueError:
                    pass
        elif skip_empty == False and not s is None:
            # Should an Error be returned
            raise MissingTagError(s)
        else:
            # assign None and append missing metadata
            results_dict[t] = None
            results_missing.append(s)
    # return
    return results_dict, results_missing

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def subset_dict(data:dict[str, Any], pattern:dict[str, str],
                substitute:tuple[str,str]|None=(r'_[0-9]{1,2}\.*', ' '),
                character_trim:int=0,
                verbose:bool=True, skip_empty:bool=True,
                ) -> dict[str, Any]:
    """
    Creates a subset of a dictionary by grouping keys based on a matching
    `pattern`. Each key in the output dictionary is derived from the original
    dictionary key, modified by removing the mathing key taken from `pattern`
    and optionally applying a regular expression substitution. The output key
    is further updated by adding a suffix based on the value derived from the
    pattern value matching key in `data`.
    
    Parameters
    ---------
    data : `dict` [`str`, `any`]
        The dictionary to be subsetted and transformed.
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
    verbose : `bool`, default `True`
        Whether warnings should be issued.
    
    Returns
    -------
    dict [`str`, `any`]
        A dictionary with keys grouped and transformed based on the `pattern`
        and `substitute`. The keys are prefixed with values derived from `data`.
    
    Examples
    --------
    >>> data = {
    ...     "Sequence_0.Referenced Waveform Channels_0": "Channel 1",
    ...     "Sequence_0.Referenced Waveform Channels_1": "Channel 2",
    ...     "Sequence_0.Annotation Group Number": 1,
    ...     "Sequence_0.Unformatted Text Value": "Event A",
    ...     "Sequence_8.Measurement Units Code Sequence_0.Code Value": "bpm",
    ...     "Sequence_8.Measurement Units Code Sequence_0.Code Meaning": "Heart Rate",
    ...     "Sequence_15.Measurement Units Code Sequence_0.Code Meaning": "Temperature",
    ...     "Sequence_15.Referenced Waveform Channels_1": "Channel 10",
    ...     "Sequence_15.Numeric Value": 36.7,
    ...     "Other Annotation Sequence_1.Some Value": "Other Data",
    ...     "Other Annotation Sequence_1.Code Meaning": "Other Code Meaning",
    ... }
    >>> pattern = {
    ...     "Sequence_15": "Code Meaning",
    ...     "Sequence_8": "Code Meaning",
    ...     "Sequence_16": "Code Meaning",
    ...     "Sequence_11": "Code Meaning",
    ...     "Other Annotation Sequence_1": "Code Meaning",
    ... }
    >>> subset_dict(data, pattern)
    {'Temperature (Referenced Waveform Channels)': 'Channel 10',
     'Temperature (Numeric Value)': 36.7,
     'Heart Rate (Measurement Units Code SequenceCode Value)': 'bpm',
     'Other Code Meaning (Some Value)': 'Other Data'}
    """
    # #### confirm input
    is_type(data, dict)
    is_type(pattern, dict)
    is_type(substitute, (type(None), tuple))
    if not substitute is None:
        if len(substitute) != 2:
            raise ValueError("`substitute` should be a `Nonetype` or a tuple "
                             "with exactly two entries.")
    # #### empty default
    # regex=True
    grouped = {}
    unmatched_keys = set(pattern.keys())
    # #### loop
    for d_name, g_name in pattern.items():
        # fist get all data entries where the key starts with `d_name`
        prefix = None
        sub_dict = {}
        for k, v in data.items():
            mtch = k.startswith(d_name)
            if mtch:
                # remove from unmatched
                unmatched_keys.discard(d_name)
                # Subset the non-matching string
                d_name_len = len(d_name)
                str_remainder = k[d_name_len + character_trim:]
                # Do we want a cleaner string
                str_remainder_clean = str_remainder
                if not substitute is None:
                    m, r = substitute
                    str_remainder_clean = re.sub(m, r, str_remainder).strip()
                # Check g_name is in str_remainder
                if g_name in str_remainder:
                    if prefix is not None:
                        raise ValueError(
                            f"For pattern {d_name}, `prefix`: {prefix} is "
                            f"already set, cannot assign new value: {v} "
                            f"please ensure `{g_name}` is unique.")
                    prefix = v
                else:
                    sub_dict[str_remainder_clean] = v
        # next confirm prefix is not None, and add the prefix
        if len(sub_dict) > 0:
            if prefix is None:
                if skip_empty:
                    continue
                else:
                    raise ValueError(f"`{g_name}` was not found in data.")
            grouped.update(
                {f"{prefix} ({key})": val for key, val in sub_dict.items()}
            )
            del sub_dict
    # do we want to return un-matching keys
    if verbose and unmatched_keys:
            warnings.warn("The following keys did not match any pattern: "
                          f"{', '.join(unmatched_keys)}")
    # return
    return grouped


