'''
The general utils module
'''
import os
import shutil
import tarfile
import numpy as np
import warnings
from typing import Any, Callable, Optional, Type, Generator
from ecgprocess.errors import (
    is_type,
)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def replace_with_tar(old_dir:str, new_tar:str, mode:str='w:gz') -> None:
    '''
    Moves the `old_dir` to a `tar` file, removing the `old_dir`.
    
    Parameters
    ----------
    old_dir: `str`
        The path to the old directory.
    new_tar: `str`
        The path to the new tar file.
    mode: `str`, default `w:gz`
        The tarfile.open mode.
    
    Notes
    -----
    The function does not return anything
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
    path : `str`,
        The path to the tar file.
    mode : `str`, default `r:gz`
        The tarfile open mode.
    
    Returns
    -------
    list
        A list of filenames.
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
def assign_empty_default(arguments:list[Any], empty_object:Callable[[],Any],
                         ) -> list[Any]:
    '''
    Takes a list of `arguments`, checks if these are `NoneType` and if so
    assigns them 'empty_object'.
    
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
    update_dict : `dict`
        A dictionary with key - value pairs that should be combined with any
        of the supplied kwargs.
    kwargs : `Any`
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
class ManagedProperty(object):
    """
    A generic property factory defining setters and getters, with optional
    type validation.
    
    Properties are read-only by default. Use `set_with_setter` to write a
    value; this temporarily unlocks the property on the specific instance
    using a per-instance lock key stored in the instance's ``__dict__``,
    avoiding the shared-state bug that arises when the lock flag is stored
    on the descriptor object itself (which is shared across all instances).
    
    Parameters
    ----------
    name : `str`
        The name of the setters and getters
    types: `Type`, default `NoneType`
        Either a single type, or a tuple of types to test against.
    
    Methods
    -------
    set_with_setter(instance, value)
        Temporarily unlocks the property on `instance`, sets the value,
        then re-locks it.
    
    Returns
    -------
    property
        A property object with getter and setter.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, name: str, types: tuple[type] | type | None = None):
        """
        Initialize the ManagedProperty.
        """
        self.name = name
        self.types = types
        # per-instance lock key stored in the instance __dict__, not on the
        # descriptor, so concurrent or nested calls on different instances
        # cannot interfere with each other.
        self._lock_key = f"__{name}_locked"
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __get__(self, instance, owner):
        """Getter for the property."""
        if instance is None:
            return self
        return instance.__dict__.get(self.name)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __set__(self, instance, value):
        """Setter for the property — unlocked until set_with_setter is called."""
        if instance.__dict__.get(self._lock_key, False):
            raise AttributeError(f"The property '{self.name}' is read-only.")
        if self.types and not isinstance(value, self.types):
            raise ValueError(
                f"Expected any of {self.types}, got {type(value)} "
                f"for property '{self.name}'."
            )
        instance.__dict__[self.name] = value
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def set_with_setter(self, instance, value):
        """
        Unlock the property on `instance`, set the value, then re-lock it.
        
        Parameters
        ----------
        instance : `object`
            The instance on which the property is being set.
        value : `any`
            The value to assign to the property.
        """
        instance.__dict__[self._lock_key] = False
        try:
            setattr(instance, self.name, value)
        finally:
            instance.__dict__[self._lock_key] = True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def parse_number(string:Any, sep:str=',', dec:str='.',
                 ) -> list[float|int] | Any:
    """
    Check if a string is a numbers.  Maps the string to a list of floats or
    ints.
    
    Parameters
    ----------
    string : `any`
        Strings and list with a `single` entry will be checked if this
        represent numbers, other object will be returned as is.
    sep : `str`, default ','
        The character used to separate values in a string.
    dec : `str`, default '.'
        The character used as a decimal point.
    
    Returns
    -------
    `list` [`int` | `float`] or `any`
        A list of parsed integers or floats or the original input.
    
    Examples
    --------
    >>> gen_utils.parse_number("1;2;3,5", sep=";", dec=",")
    [1, 2, 3.5]
    
    >>> gen_utils.parse_number(["1,2.5,3"])
    [1, 2.5, 3]
    
    >>> gen_utils.parse_number(['1,2.5,3', '2'])
    ['1,2.5,3', '2']
    
    >>> parse_number(123)
    123
    """
    def is_valid_number(number):
        """Checks if a string `number` is a valid float or int"""
        try:
            # Replace decimal indicator with standard '.' for float conversion
            float(number.replace(dec, '.'))
            return True
        except ValueError:
            return False
    # ### Split the string into parts using the separator
    # NOTE wrap in try/except in case input is not a string and does not have
    # string.split
    res = string
    # unlist if the string is nested in a list of length one.
    if isinstance(string, list):
        if len(string) == 1:
            string = string[0]
    try:
        parts = string.split(sep)
        if all(is_valid_number(p) for p in parts):
            # Convert each part to float or int, making sure a float has a '.'
            res= [
                float(p.replace(dec, '.')) if dec in p else int(p) for p in parts
            ]
        else:
            res = string
    except AttributeError:
        pass
    # #### return
    return res

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def string_concat(old:str , new: str, sep:str=', ') -> list[str]:
    '''
    Concatenates two strings, checking if the `old` string might be `NaN`.
    
    Parameters
    ----------
    old : `str` or `np.nan`,
        The original string.
    new : `str`
        A new string.
    sep : `str`, default `, `
        The string separator.
        
    Returns
    -------
    str :
        A concatenated string
    
    Notes
    -----
    In general NaN is considered a float and missing string information is
    better reflected by `NoneType`. Nevertheless one does find strings which
    are set to `NaN` which is what this function deals with.
    '''
    # #### check input.
    # np.nan is a float, so testing for float
    is_type(old, (str, float, type(None)))
    is_type(new, str)
    # #### checking for nan
    try:
        if np.isnan(old):
            res = new
        else:
            # will be run when old is a float
            res = f"{old}{sep}{new}"
    except TypeError:
        res = f"{old}{sep}{new}"
    # #### return
    return res

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def chunk_list(lst:list[Any], size:int) -> Generator[list[Any], None, None]:
    """
    Splits a given list into chunks of a specified size.
    
    Parameters
    ----------
    lst : `list` [`any`]
        A list of arbitrary length.
    size : `int`
        The size of the chunks, should be larger than 0.
    
    Yields
    ------
    list
        A chunk of the input list of length ``size``. The final chunk
        may be shorter if there aren't enough elements left.
    
    Examples
    --------
    >>> data = list(range(10))
    >>> gen = chunk_list(data, 3)
    >>> next(gen)
    [0, 1, 2]
    """
    is_type(lst, list)
    is_type(size, int)
    if size < 1:
        raise ValueError('`size` should be larger than 0.')
    # #### The algorithm
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def update_dict_with_warning(d1:dict, d2:dict, verbose:bool=True) -> dict:
    """
    Dictionary update while raising a warning for key duplication.
    
    Parameters
    ----------
    d1 : `dict`
        The dictionary with `old` data.
    d2 : `dict`
        The dictionary with `new` data.
    verbose : `bool`, default `True`
        Whether to print a warning when there are duplicated keys with
        distinct values.
    
    Notes
    -----
    The value from d2 overwrites the value from d1 in the final result. The
    warning will only be raised when the values are distinct.
    """
    # Find keys that appear in both dictionaries
    if verbose == True:
        duplicates = d1.keys() & d2.keys()
        # Only raise a warning if the values are distinct
        for key in duplicates:
            if d1[key] != d2[key]:
                warnings.warn(
                    (f"Duplicate key '{key}' found. Old value: {d1[key]}, "
                     f"new value: {d2[key]} (retained)."),
                    UserWarning
                )
    # Overwrite d1 with d2’s key-value pairs
    d1.update(d2)
    return d1
