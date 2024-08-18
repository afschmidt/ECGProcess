'''
The general utils module
'''
import os
import shutil
import tarfile
from typing import Any, List, Type, Union, Tuple, Callable, Optional, Dict
from ecgprocess.errors import (
    is_type,
)

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
def list_tar(path:str, mode:str='r:gz') -> List[str]:
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def getattr_case_insensitive(obj:object, attr_name:str) -> Any:
    '''
    A case insensitive version of getattr. Use this when extracting data from
    a dataclass instance which may have not been sufficiently standardised.
    '''
    # Get all attributes of the object
    all_attrs = dir(obj)
    # Find the attribute with a case-insensitive match
    for attr in all_attrs:
        if attr.lower() == attr_name.lower():
            return getattr(obj, attr)
    # Raise an AttributeError if no match is found
    raise AttributeError(f"'{type(obj).__name__}' object has no attribute "
                         f"'{attr_name}'")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def assign_empty_default(arguments:List[Any], empty_object:Callable[[],Any],
                         ) -> List[Any]:
    '''
    Takes a list of `arguments`, checks if these are `NoneType` and if so
    asigns them 'empty_object'.
    
    This function helps deal with the pitfall of assigning an empty mutable
    object as a default function argument, which would persist through multiple
    function calls, leading to unexpected/undesired behaviours.
    
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
    '''
    # check input
    is_type(arguments, list, 'arguments')
    is_type(empty_object, type, 'empty_object')
    # loop over arguments
    new_args = [empty_object() if arg is None else arg for arg in arguments]
    # return
    return new_args

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _update_kwargs(update_dict:Dict[Any, Any], **kwargs:Optional[Any],
            ) -> Dict[Any, Any]:
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

