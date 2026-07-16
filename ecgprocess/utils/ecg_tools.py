'''
Collecting established tools for ECG derivation or cleaning.
'''

import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
)
from scipy import signal
from ecgprocess.errors import (
    is_type,
)
from typing import Any
import warnings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CLeads = Core.Leads
_STANDARD_LEADS: tuple[str, ...] = (
    'I', 'II', 'III', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'aVF', 'aVL', 'aVR'
)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def resampling_500hz(signals:dict[str, np.array],
                     duration: int | float | None=None,
                     ) -> dict[str, np.array]:
    """
    Re-sample an ECG signal to 500 hz.
    
    Parameters
    ----------
    signals : `dict` [`str`, np.array]
        A dictionary with the lead names as string keys and the signals
        as a 1D np.array.
    duration : `int` or `float`
        The duration of the signal in seconds, calculated as the fraction
        of the number of samples by the sampling frequency. The number of
        samples needed for a 500 hz signal is: duration times 500. Applies
        to waveforms and median beats alike; a median beat is typically
        1.2 seconds (1.2 times 500 = 600 samples) but this is not assumed.
    
    Raises
    ------
    ValueError
        If `duration` is `NoneType`.
    """
    is_type(signals, dict)
    is_type(duration, (type(None), int, float))
    # #### get number of samples
    if duration is None:
        raise ValueError('`duration` should not be `NoneType`.')
    num_samples = int(duration * 500)
    # #### resample
    new_dict = {}
    for l, sig in signals.items():
        new_dict[l] = signal.resample(sig, num_samples)
    # return
    return new_dict

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_limb_leads(signals:dict[str, np.array],
                   lead_I:str=CLeads.I,
                   lead_II:str=CLeads.II,
                      ) -> dict[str, np.array]:
    """
    Calculate the derived limb leads (III, aVR, aVL, aVF) from leads I and II.
    
    Parameters
    ----------
    signals : `dict` [`str`, np.array]
        A dictionary with the lead names as string keys and the signals
        as a 1D np.array.
    lead_I : `str`, default 'I'
        The key name for lead I in `signals`
    lead_II : `str`, default 'II'
        The key name for lead II in `signals`
    
    Returns
    -------
    dict
        A dictionary including limb lead signals.
    
    Notes
    -----
    please see this
    `url <https://ecgwaves.com/topic/ekg-ecg-leads-electrodes-systems-limb-chest-precordial/>`_
     for the relevant explanation about the relationships between leads I and II
    and the limb leads.
    """
    # #### check input and set constants
    is_type(signals, dict)
    is_type(lead_I, str)
    is_type(lead_II, str)
    missing_src = [l for l in (lead_I, lead_II) if signals.get(l) is None]
    if missing_src:
        raise KeyError(
            f'Source leads {missing_src} are not available in `signals`.'
        )
    # making sure we do not affect the original parsed signals
    signals = dict(signals)
    # #### get limb leads
    if signals.get(CLeads.III) is None:
        signals[CLeads.III] = np.subtract(signals[CLeads.II],
                                              signals[CLeads.I])
    if signals.get(CLeads.aVR) is None:
        signals[CLeads.aVR] = np.add(signals[CLeads.I],
                                        signals[CLeads.II]) * (-0.5)
    if signals.get(CLeads.aVL) is None:
        signals[CLeads.aVL] = np.subtract(signals[CLeads.I],
                                   0.5 * signals[CLeads.II])
    if signals.get(CLeads.aVF) is None:
        signals[CLeads.aVF] = np.subtract(signals[CLeads.II],
                                   0.5 * signals[CLeads.I])
    # return
    return signals

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_dicts_to_numpy_array(
    signals: list[dict[str, np.ndarray]],
    leads: list[str] | tuple[str, ...] | None = _STANDARD_LEADS,
    padding: bool = True,
) -> np.ndarray:
    """
    Convert a list of ECG signal dictionaries to a 3D NumPy array suitable
    for deep learning.
    
    Parameters
    ----------
    signals : `list` [`dict` [`str`, `np.ndarray`]]
        List where each dictionary represents an ECG sample with lead names
        as keys and numpy arrays as values.
    leads : `list` [`str`] or `tuple` [`str`, ...] or `None`, \
default ``_STANDARD_LEADS``
        Lead names to include and their order. Defaults to the standard
        12-lead set defined in ``_STANDARD_LEADS`` (an immutable tuple).
        Pass `None` to collect all unique leads found across samples in
        sorted order.
    padding : `bool`, default `True`
        Whether to pad shorter signals to the length of the longest signal.
        If `False`, all signals must have the same length. Default is `True`.
    
    Returns
    -------
    np.ndarray
        3D NumPy array with shape `(num_samples, num_leads, signal_length)`
        containing the ECG data.
    
    Raises
    ------
    ValueError
        If `ecg_data` is empty.
        If any sample is missing leads specified in `leads`.
        If `padding` is `False` and signals have varying lengths.
    
    Notes
    -----
    The numpy array column matches the order of the supplied leads.
    """
    # check input
    is_type(signals, list)
    if not signals:
        raise ValueError("The signals list is empty.")
    # Determine the list of leads
    if leads is None:
        # Collect all unique leads across samples
        unique_leads: set[str] = set()
        for sample in signals:
            unique_leads.update(sample.keys())
        leads = sorted(unique_leads)
    else:
        # Ensure leads is a sequence of strings
        if not isinstance(leads, (list, tuple)) or not all(
            isinstance(lead, str) for lead in leads
        ):
            raise TypeError("`leads` must be a list or tuple of strings.")
        leads = list(leads)
    # set the samples and lead numbers
    num_samples = len(signals)
    num_leads = len(leads)
    # do we want to pad the signals if needed.
    if padding:
        # Find the maximum length among all leads in all samples
        signal_length = max(
            len(sample.get(lead, [])) for sample in signals for lead in leads
        )
    else:
        # Only present (non-empty) leads constrain the length; absent leads
        # are left as NaN, so a subset of leads (even a single lead) is
        # allowed as long as every present lead shares one length.
        present_lengths = {
            len(sample.get(lead, []))
            for sample in signals for lead in leads
        }
        present_lengths.discard(0)
        if len(present_lengths) > 1:
            raise ValueError(
                "All present signals must have the same length when "
                "padding is False."
            )
        signal_length = present_lengths.pop() if present_lengths else 0
    # Initialize the array with NaNs
    data_array = np.full(
        (num_samples, num_leads, signal_length), np.nan, dtype=np.float32
    )
    for i, sample in enumerate(signals):
        for j, lead in enumerate(leads):
            lead_data = sample.get(lead, np.array([]))
            # Validate that lead_data is a np.array
            if not isinstance(lead_data, np.ndarray):
                raise TypeError(
                    f"Lead '{lead}' in sample {i} is not a NumPy array."
                )
            current_length = len(lead_data)
            if current_length == 0:
                # If lead data is missing or empty, leave it as NaN
                continue
            elif padding:
                if current_length > signal_length:
                    # Truncate the signal if it's longer than signal_length
                    warnings.warn('Signal is longer than the max length '
                                  'this is unexpected, please check input.')
                    data_array[i, j, :] = lead_data[:signal_length]
                else:
                    # Pad the signal with NaNs if it's shorter than
                    # signal_length
                    data_array[i, j, :current_length] = lead_data
            else:
                if current_length != signal_length:
                    raise ValueError(
                        f"Signal length for lead '{lead}' in sample {i} "
                        f"({current_length}) does not match signal_length "
                        f"({signal_length})."
                    )
                data_array[i, j, :] = lead_data
    # return
    return data_array

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_calibration(signal:np.ndarray,
                       correctionfactor: float,
                       baseline: float,
                       ) -> np.ndarray:
    """
    Adjusts the ECG signal by subtracting the channel baseline from the signal,
    followed by multiplying the adjusted signal by the channel correction
    factor.
    
    Parameters
    ----------
    signal : `np.ndarray`
        The lead-specific ECG signal.
    correctionfactor : `float`
        The channel correction factor.
    baseline : `float`
        The channel baseline.
    
    Returns
    -------
    np.ndarray
        The recalibrated signal.
    """
    is_type(signal, np.ndarray)
    is_type(correctionfactor, float)
    is_type(baseline, float)
    # algorithm
    new_signal = (signal - baseline) * correctionfactor
    # return
    return new_signal

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def signal_resolution(signal:np.ndarray,
                      resolution_current: float,
                      resolution_target: float,
                       ) -> np.ndarray:
    """
    Adjust the amplitude scale of an ECG signal to match a desired resolution.
    
    Parameters
    ----------
    signal : `np.ndarray`
        The lead-specific ECG signal.
    resolution_current : `float`
        The current resolution.
    resolution_target : `float`
        The target resolution.
    
    Returns
    -------
    np.ndarray
        The rescaled signal.
    
    Example
    -------
    >>> import numpy as np
    >>> ecg_signal = np.array([10, 20, 30, 40, 50])
    >>> current_res = 2.0  # each digital unit equals 2 μV
    >>> new_signal = adjust_resolution(
    ...     ecg_signal,
    ...     resolution_current=current_res,
    ...     resolution_target=5
    ... )
    >>> print(new_signal)
    [ 25.  50.  75. 100. 125.]
    """
    is_type(signal, np.ndarray)
    is_type(resolution_current, float)
    is_type(resolution_target, float)
    # algorithm
    new_signal = signal * resolution_target/resolution_current
    # return
    return new_signal

