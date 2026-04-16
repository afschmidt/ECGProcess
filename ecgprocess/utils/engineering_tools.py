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

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import re
import sys
import logging
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
    # the algorithm: check each expected field independently so the error
    # message identifies which field failed. expected_* may be a single
    # string or a list of strings; normalise to a list so membership tests
    # work in both cases.
    def _check(field_label: str, got: Any, expected: Any) -> None:
        expected_list = expected if isinstance(expected, list) else [expected]
        if got not in expected_list:
            raise FileValidationError(
                f"{field_label} `{got}` failed to validate; "
                f"expected one of {expected_list}."
            )
    _check("Version", metadata[version], expected_version)
    _check("Manufacturer", metadata[manufact], expected_manufacturer)
    _check("Model", metadata[model_name], expected_model)
    # if all correct simply return metadata
    return metadata

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_correction(
    signals:dict[str, np.ndarray], baseline_name:str='wave_channel_baseline_',
    correctionfactor_name:str='wave_channel_correctionfactor_',
    verbose:bool=False,
    **kwargs) -> dict[str, np.ndarray]:
    """
    Adjusts the signals by subtracting the channel baseline multiplied
    by the channel correction factor.  These parameters must be provided in
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
    signals = dict(signals)
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
    Standardise the resolution signal by adjusting the amplitude scale by the
    ratio of the source and target solution.
    
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
    
    Notes
    -----
    The function will apply a scaling factor of
    source_resolution/target_resolution to ensure the returned signal has the
    desired target uV.
    """
    # constants - these values should be in meta_dict
    sens = resolution_name
    # the algorithm
    is_type(verbose, bool)
    if not TabNames.META_DICT in kwargs:
        raise KeyError(f"`{TabNames.META_DICT}` should be included as kwargs")
    else:
        meta_dict = kwargs[TabNames.META_DICT]
    signals = dict(signals)
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
            raise KeyError(f"`{key_name}` not found in `{TabNames.META_DICT}`.")
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

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class LeadMapper(object):
    """
    Normalise ECG lead ordering when a device writes channels out of sequence.
    
    Some DICOM devices store channels in a non-standard order (e.g. Lead II
    data in channel-0 slot). ``LeadMapper`` reads ``signal name X`` entries
    from ``meta_dict``, builds an actual-label-to-key mapping, then reassigns
    each canonical key in ``signals`` to the correct array.
    
    Parameters
    ----------
    accepted_mappings : `dict` [`str`, `list` [`str`]]
        Maps each canonical lead key (e.g. ``'I'``) to a list of device
        label strings that are acceptable for that lead
        (e.g. ``['I', 'Lead I', 'Lead I (Einthoven)']``).
    
    Attributes
    ----------
    accepted_mappings : `dict` [`str`, `list` [`str`]]
        The accepted lead label mappings supplied at initialisation.
    
    Methods
    -------
    __call__(signals, verbose, **kwargs)
        Reassign signal arrays to their canonical lead keys.
    
    Raises
    ------
    TypeError
        If ``accepted_mappings`` is not a ``dict``, or if any value is
        not a ``list``.
    
    Notes
    -----
    The callable works for both ``engineer_wave`` and ``engineer_median``
    call sites in ``tabular.py`` since both share the same signature
    ``(signals, meta_dict=meta_temp)``.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, accepted_mappings: dict[str, list[str]]) -> None:
        """Initialise LeadMapper."""
        is_type(accepted_mappings, dict)
        for key, val in accepted_mappings.items():
            if not isinstance(val, list):
                raise TypeError(
                    f"accepted_mappings values must be lists; "
                    f"key '{key}' has type {type(val)}"
                )
        self.accepted_mappings = accepted_mappings
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(
        self,
        signals: dict[str, np.ndarray],
        verbose: bool = False,
        **kwargs,
    ) -> dict[str, np.ndarray]:
        """
        Reassign signal arrays to their canonical lead keys.
        
        Parameters
        ----------
        signals : `dict` [`str`, `np.ndarray`]
            Dict mapping canonical key names to waveform arrays, as parsed
            by the config parser (keys correct, values potentially in wrong
            channel order).
        verbose : `bool`, default `False`
            If ``True``, log accepted and actual mappings at DEBUG level.
        **kwargs
            Must include ``meta_dict`` (keyed by ``TabNames.META_DICT``),
            a dict containing ``'signal name N'`` entries that map channel
            indices to device lead labels.
        
        Returns
        -------
        mapped_signals : `dict` [`str`, `np.ndarray`]
            Shallow copy of ``signals`` with arrays reassigned to the correct
            canonical keys.
        
        Raises
        ------
        KeyError
            If ``TabNames.META_DICT`` is absent from ``kwargs``, or if no
            device label matches a required canonical key.
        """
        # check input
        is_type(signals, dict)
        is_type(verbose, bool)
        # set up logger
        _log = logging.getLogger(__name__)
        if TabNames.META_DICT not in kwargs:
            raise KeyError(
                f"`{TabNames.META_DICT}` should be included as kwargs"
            )
        # map data
        meta_dict = kwargs[TabNames.META_DICT]
        mapped_signals = dict(signals)
        signal_keys = list(mapped_signals.keys())
         # Map each canonical slot key to the device label the device wrote
         # there; e.g. {'I': 'Lead II'} means channel 0 holds 'Lead II' data.
        actual_mappings = {
            signal_keys[int(re.sub(r"^signal name\s*", "", k))]: v
            for k, v in meta_dict.items()
            if k.startswith('signal name')
        }
        if verbose:
            _log.debug('Accepted lead mappings: %s', self.accepted_mappings)
            _log.debug('Actual lead mappings: %s', actual_mappings)
        # Now apply the mappings
        for accepted_key, accepted_vals in self.accepted_mappings.items():
            match = False
            for actual_key, actual_val in actual_mappings.items():
                if actual_val in accepted_vals:
                    if verbose:
                        _log.debug(
                            "Mapping '%s' (%s) <- actual '%s' (%s)",
                            accepted_key, accepted_vals, actual_key, actual_val,
                        )
                    mapped_signals[accepted_key] = signals[actual_key]
                    match = True
                    break
            if not match:
                raise KeyError(
                    f"No device label found for canonical key '{accepted_key}' "
                    f"(accepted: {accepted_vals})"
                )
        return mapped_signals
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        CLASS_NAME = type(self).__name__
        return f"{CLASS_NAME}(accepted_mappings={self.accepted_mappings!r})"
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self) -> str:
        """Return human-readable string representation."""
        CLASS_NAME = type(self).__name__
        leads = list(self.accepted_mappings.keys())
        return f"{CLASS_NAME} with {len(leads)} canonical leads: {leads}"
