'''
The general utils module
'''
import os
import shutil
import tarfile
from typing import List, Any

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
    raise AttributeError(f"'{type(obj).__name__}' object has no attribute '{attr_name}'")
