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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CLeads = Core.Leads

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def resampling_500hz(signals:dict[str, np.array],
                     duration: int | float | None=None,
                     median:bool=False) -> dict[str, np.array]:
    """
    Re-sample an ECG signal to 500 hz.
    
    Parameters
    ----------
    signals : `dict` [`str`, np.array]
        A dictionary with the lead names as string keys and the signals
        as a 1D np.array.
    duration : `int` or `float`
        The represents the duration of the ECG in seconds, which is calculated
        based on the fraction of number of samples by the sampling frequency
        in seconds.  For raw wavefomrs duration determines the number of
        samples needed to get a 500hz sample: duration times 500.
    median : `bool`, default `False`
        Set to true to resample a median beat ECG to 500hz. The duration of a
        median beat signal is 1.2 seconds, hence the sampling rate is fixed at:
        1.2 times 500 = 600.
    
    """
    is_type(signals, dict)
    is_type(duration, (type(None), int, float))
    is_type(median, bool)
    # #### get sampling rate
    samp_rate = 600
    if median == False:
        if duration is None:
            raise ValueError('`duration` should not be `NoneType` when `median` '
                             'is `False`.')
        samp_rate = duration * 500
    # #### resample
    new_dict = {}
    for l, sig in signals.items():
        new_dict[l] = signal.resample(sig, samp_rate)
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
     for the relevant explantion about the relationships between leads I and II
    and the limb leads.
    """
    # #### check input and set constants
    is_type(signals, dict)
    is_type(lead_I, str)
    is_type(lead_II, str)
    if not {lead_I, lead_II}.issubset(signals):
        raise KeyError('leads I and/or II are not available in `signals`: '
                       f'{signals.keys()}')
    # #### get limb leads
    if not CLeads.III in signals:
        signals[CLeads.III] = np.subtract(signals[CLeads.II],
                                              signals[CLeads.I])
    if not CLeads.aVR in signals:
        signals[CLeads.aVR] = np.add(signals[CLeads.I],
                                        signals[CLeads.II]) * (-0.5)
    if not CLeads.aVL in signals:
        signals[CLeads.aVL] = np.subtract(signals[CLeads.I],
                                   0.5 * signals[CLeads.II])
    if not CLeads.aVF in signals:
        signals[CLeads.aVF] = np.subtract(signals[CLeads.II],
                                   0.5 * signals[CLeads.I])
    # return
    return signals

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# TODO write pytest
def signal_dicts_to_numpy_array(
    signals: list[dict[str, np.ndarray]],
    leads: list[str] | None = ['I', 'II', 'III', 'V1', 'V2', 'V3', 'V4',
                               'V5', 'V6', 'aVF', 'aVL', 'aVR'],
    padding: bool = True,
) -> np.ndarray:
    """
    Convert a list of ECG signal dictionaries to a 3D NumPy array suitable
    for deep learning.
    
    Parameters
    ----------
    signals : `list` [`dict` [`str`, `np.ndarray`]]
        List where each dictionary represents an ECG sample with lead names
        as keys and NumPy arrays as values.
    leads : `list` [`str`] or `None`
        List of lead names to include and their order. If `None`, all unique
        leads across samples are used in sorted order.
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
        unique_leads = set()
        for sample in signals:
            unique_leads.update(sample.keys())
        leads = sorted(unique_leads)
    else:
        # Ensure leads is a list of strings
        if not isinstance(leads, list) or not all(
            isinstance(lead, str) for lead in leads
        ):
            raise TypeError("`leads` must be a list of strings.")
    # set the samples and lead numbers
    num_samples = len(signals)
    num_leads = len(leads)
    # do we want to padd the signals if needed.
    if padding:
        # Find the maximum length among all leads in all samples
        signal_length = max(
            len(sample.get(lead, [])) for sample in signals for lead in leads
        )
    else:
        # Ensure all signals have the same length
        lengths = [
            len(sample.get(lead, [])) for sample in signals for lead in leads
        ]
        unique_lengths = set(lengths)
        if len(unique_lengths) != 1:
            raise ValueError(
                "All signals must have the same length when padding is False."
            )
        signal_length = unique_lengths.pop()
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
                                  'this is unexpeted, please check input.')
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
