'''
The general utils module
'''
import tarfile
import shutil
import os

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
        tar.add(old_dir, arcname=os.path.basename(old_dir))
    # Verify the archive was created successfully
    if not os.path.exists(new_tar):
        raise FileNotFoundError('Failed to create tar.gz archive.')
    # Delete the original directory
    shutil.rmtree(old_dir)


