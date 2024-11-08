'''
The general utils module
'''
import os
import shutil
import tarfile
import warnings
import xmltodict
from lxml import etree
from pathlib import Path
from typing import Any, Callable, Optional
from ecgprocess.errors import (
    is_type,
)
from ecgprocess.constants import UtilsGeneralNames as UGNames
from ecgprocess.errors import XMLValidationError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
WARN1 = "XML file is valid (ignoring XML elements not in the supplied XSD)."

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def replace_with_tar(old_dir:str, new_tar:str, mode:str='w:gz'):
    '''
    Moves the `old_dir` and its files an moves this to `tar` file, removing
    the `old_dir`.
    
    Parameters
    ----------
    old_dir: str
        The path to the old directory.
    new_tar: str
        The path to the new tar file.
    mode: str, default `w:gz`
        The tarfile.open mode.
    
    Returns
    -------
    None
    '''
    # Create the tar.gz archive
    with tarfile.open(new_tar, mode) as tar:
        # Iterate through the files in the old directory
        for root, _, files in os.walk(old_dir):
            for file in files:
                # Create the full path to the file
                file_path = os.path.join(root, file)
                # Add the file to the tar archive with only the filename
                tar.add(file_path, arcname=file)
    # Verify the archive was created successfully
    if not os.path.exists(new_tar):
        raise FileNotFoundError('Failed to create tar.gz archive.')
    # Delete the original directory
    shutil.rmtree(old_dir)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def list_tar(path:str, mode:str='r:gz') -> list[str]:
    '''
    Extract the content of a tar file and return this as a list
    
    Parameters
    ----------
    path : str,
        The path to the tar file.
    mode : str, default `r:gz`
        The tarfile open mode.
    
    Returns
    -------
    files : list [`str`]
    '''
    # make sure we use a read mode
    if mode.startswith('r:') == False:
        raise ValueError('`mode` should start with `r:`')
    # get list
    with tarfile.open(path, mode) as tar:
        # List all contents in the .tar.gz file
        files = []
        for member in tar.getmembers():
            files.append(member.name)
    # return
    return files

# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# def getattr_case_insensitive(obj:object, attr_name:str) -> Any:
#     '''
#     A case insensitive version of getattr. Use this when extracting data from
#     a dataclass instance which may have not been sufficiently standardised.
#     '''
#     # Get all attributes of the object
#     all_attrs = dir(obj)
#     # Find the attribute with a case-insensitive match
#     for attr in all_attrs:
#         if attr.lower() == attr_name.lower():
#             return getattr(obj, attr)
#     # Raise an AttributeError if no match is found
#     raise AttributeError(f"'{type(obj).__name__}' object has no attribute "
#                          f"'{attr_name}'")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def assign_empty_default(arguments:list[Any], empty_object:Callable[[],Any],
                         ) -> list[Any]:
    '''
    Takes a list of `arguments`, checks if these are `NoneType` and if so
    asigns them 'empty_object'.
    
    Parameters
    ----------
    arguments: list of arguments
        A list of arguments which may be set to `NoneType`.
    empty_object: Callable that returns a mutable object
        Examples include a `list` or a `dict`.
    
    Returns
    -------
    new_arguments: list
        List with `NoneType` replaced by empty mutable object.
    
    Examples
    --------
    >>> assign_empty_default(['hi', None, 'hello'], empty_object=list)
    ['hi', [], 'hello']
    
    Notes
    -----
    This function helps deal with the pitfall of assigning an empty mutable
    object as a default function argument, which would persist through multiple
    function calls, leading to unexpected/undesired behaviours.
    '''
    # check input
    is_type(arguments, list)
    is_type(empty_object, type)
    # loop over arguments
    new_args = [empty_object() if arg is None else arg for arg in arguments]
    # return
    return new_args

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _update_kwargs(update_dict:dict[Any, Any], **kwargs:Optional[Any],
            ) -> dict[Any, Any]:
    '''
    This function will take any number of `kwargs` and add them to an
    `update_dict`. If there are any duplicate values in the `kwargs` and the
    `update_dict`, the entries in the `update_dict` will take precedence.
    
    Parameters
    ----------
    update_dict : dict
        A dictionary with key - value pairs that should be combined with any
        of the supplied kwargs.
    kwargs : Any
        Arbitrary keyword arguments.
    
    Returns
    -------
    dict:
        A dictionary with the update_dict and kwargs combined, where duplicate
        entries from update_dict overwrite those in kwargs.
    
    Examples
    --------
        The function is particularly useful to overwrite `kwargs` that are
        supplied to a nested function say
        
        >>> _update_kwargs(update_dict={'c': 'black'}, c='red',
                         alpha = 0.5)
        >>> {'c': 'black', 'alpha': 0.5}
    '''
    new_dict = {**kwargs, **update_dict}
    # returns
    return new_dict

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
        xml : `etree._ElementTree`
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
    res : `dict` [`str`, `any`]
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
# d = nested_dict_fixture
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


