"""
A module containing a collection of function or classes which can be used
as engineering functions in the Tabular module.

The listed programs are meant to provide an idea of potentially relevant
solutions. Users can use these functions out of the box, adapt them, or
simply write their own custom code.

When writing your own engineering solution remember that the first argument
will take the metadata, waveforms, or metadata. The waveforms and metadata
functions should have a kwargs argument which will be used internally by
Tabular to pass meta_dict (the metadata of the file being processed) to the
function environment making it available to alter the signal data.
"""

#NOTE
# write pytests.

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import sys
import numpy as np
from typing import (
    Callable, Self, Optional, Any, Literal,
)
from ecgprocess.errors import (
    FileValidationError,
    is_type,
)
from ecgprocess.utils.ecg_tools import(
    signal_dicts_to_numpy_array,
    signal_calibration,
    signal_resolution,
)
from ecgprocess.constants import (
    TabularNames as TabNames,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def metadata_checkversion(
    metadata:dict[str, Any],
    expected_version = ['1.02 SP03', 'MUSE_9.0.9.18167'],
    expected_manufacturer = 'GE Healthcare',
    expected_model = 'MV360',
    version_name:str = "Softwave version",
    manufacturer_name:str = "Manufacturer",
    model_name = "Model name",
    verbose:bool=False, **kwargs,
) -> dict[str, Any]:
    """
    Validates the DICOM file against the specified software version,
    manufacturer, and model. If any of these do not match, a
    FileValidationError is raised.
    
    Parameters
    ----------
    metadata : `dict` [`str`, `any`]
        A dictionary containing the metadata for a DICOM file. It must include:
          - "Softwave version": The software version associated with the file.
          - "Manufacturer": The manufacturer of the device.
          - "Model name": The model name of the device.
    expected_version : `str` or `list` [`str`], default ['1.02 SP03', 'MUSE_9.0.9.18167']
        The software version.
    expected_manufacturer : `str` or `list` [`str`], default 'GE Healthcare'
        The manufacturer.
    expected_model : `str` or `list` [`str`],  'MV360'
        The model.
    version_name : `str`
        The key name for version in meta_dict.
    manufacturer_name : `str`
        The key name for manufacturer in meta_dict.
    moel_name : `str`
        The key name for version in meta_dict.
    
    Returns
    -------
    dict [`str`, `any`]
        The input `metadata` dictionary if validation is successful.
    
    Raises
    ------
    FileValidationError
        If the DICOM metadata's software version, manufacturer, or model
        does not match the respective expected values.
    
    Notes
    -----
    Depending on the `ignore_invalid` parameter of `Tabular` the failed
    filenames will be added to the `invalid_list` attribute.
    """
    is_type(manufacturer_name, str)
    is_type(version_name, str)
    is_type(model_name, str)
    # TODO
    # add a test to confirm these keys are in meta_dict and raise a KeyError
    # otherwise.
    # NOTE
    # just keeping this so kwargs are used and the linter does not complain.
    if verbose:
        print(**kwargs, file=sys.stdout)
    # constant
    version = version_name
    manufact = manufacturer_name
    model_name = model_name
    # the algorithm
    if expected_version != metadata[version] or\
        expected_manufacturer != metadata[manufact] or\
        expected_model != metadata[model_name]:
        raise FileValidationError(
            f"The version `{metadata[version]}`, manufacturer "
            f"`{metadata[manufact]}` or model `{metadata[model_name]}` failed "
            "to validate."
        )
    # if all corect simply return metadata
    return metadata

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_correction(
    signals:dict[str, np.ndarray], baseline_name:str='wave_channel_baseline_',
    correctionfactor_name:str='wave_channel_correctionfactor_',
    verbose:bool=False,
    **kwargs) -> dict[str, np.ndarray]:
    """
    Adjusts the signals by subtracting the channel baseline multiplied
    by the channel correcttion factor.  These parameters must be provided in
    `kwargs[TabNames.META_DICT]`.
    
    Parameters
    ----------
    signals : `dict` [`str`, `np.ndarray`]
        A dictionary mapping channel names (strings) to waveform arrays.
    baseline_name : str
        The dictionary key name for the channel baseline. Will internally add
        a numeric suffix ranging from 0 to 11 (inclusive).
    correctionfactor_name : str
        The dictionary key name for the channel correctionfactor. Will
        internally add a numeric suffix ranging from 0 to 11 (inclusive).
    verbose : `bool`, default False
        If True, prints additional debug information about the correction
        process.
    **kwargs
        Additional keyword arguments, which must include a dictionary under
        the key `TabNames.META_DICT`. This dictionary should contain:
        - wave_channel_correctionfactor_i : float
            Correction factor for channel i.
        - wave_channel_baseline_i : float
            Baseline offset for channel i.
    
    Returns
    -------
    dict [`str`, `np.ndarray`]
        The input signals dictionary with corrected signals.
    
    Raises
    ------
    KeyError
        If `TabNames.META_DICT` is not found in **kwargs.
    """
    # constants - these values should be in meta_dict
    corr = correctionfactor_name
    base = baseline_name
    # TODO
    # add a check/raise error for the presence or absence of these keys in
    # meta_dict.
    # the algorithm
    is_type(verbose, bool)
    if not TabNames.META_DICT in kwargs:
        raise KeyError(f"`{TabNames.META_DICT}` should be included as kwargs")
    else:
        meta_dict = kwargs[TabNames.META_DICT]
    for i, (k, v) in enumerate(signals.items()):
        # skip of None
        if v is None:
            signals[k] = v
            continue
        # confirming this is a np.array
        is_type(v, np.ndarray)
        if verbose:
            print(f'Applying baseline: {meta_dict[base+str(i)]} and factor: '
                  f'{meta_dict[corr+str(i)]} corrections to lead: {k}.',
                  file=sys.stdout
                  )
        signals[k] = signal_calibration(
            v, correctionfactor=meta_dict[corr+str(i)],
            baseline=meta_dict[base+str(i)],
        )
    return signals

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_standardise_res(
    signals:dict[str, np.ndarray], resolution_name:str = 'wave_channel_sens_',
    target_resolution:float = 5., verbose:bool=False, **kwargs,
) -> dict[str, np.ndarray]:
    """
    Standardised the resolution signal.
    
    Parameters
    ----------
    signals : `dict` [`str`, `np.ndarray`]
        A dictionary mapping channel names (strings) to waveform arrays.
    resolution_name : str
        The dictionary key name for the channel sensitivity/resolution. Will
        internally add a numeric suffix ranging from 0 to 11 (inclusive).
    target_resolution : `float`, default 5
        The target resolution.
    verbose : `bool`, default False
        If True, prints additional debug information about the correction
        process.
    **kwargs
        Additional keyword arguments, which must include a dictionary under
        the key `TabNames.META_DICT`. This dictionary should contain:
        - wave_channel_sens : float
            The wave channel sensitivity/resolution for channel i.
    
    Returns
    -------
    dict [`str`, `np.ndarray`]
        The input signals dictionary with corrected signals.
    
    Raises
    ------
    KeyError
        If `TabNames.META_DICT` is not found in **kwargs.
        If resolution_name+str(i) is not found in `TabNames.META_DICT`.
    """
    # constants - these values should be in meta_dict
    sens = resolution_name
    # the algorithm
    is_type(verbose, bool)
    if not TabNames.META_DICT in kwargs:
        raise KeyError(f"`{TabNames.META_DICT}` should be included as kwargs")
    else:
        meta_dict = kwargs[TabNames.META_DICT]
    for i, (k, v) in enumerate(signals.items()):
        # skip of None
        if v is None:
            signals[k] = v
            continue
        # confirming this is a np.array
        is_type(v, np.ndarray)
        # check key is in dict
        key_name = sens+str(i)
        if not key_name in meta_dict:
            raise KeyError(f"`{key_name}` not found in `{TabNames.Meta_DICT}`.")
        if verbose:
            if target_resolution/meta_dict[key_name] != 1.0:
                print(f'Rescaling lead `{k}` by factor '
                      f'`{target_resolution/meta_dict[key_name]}`.',
                      file=sys.stdout
                      )
        signals[k] = signal_resolution(
            v, resolution_current=meta_dict[key_name],
            resolution_target=target_resolution,
        )
    return signals

