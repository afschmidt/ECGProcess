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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CLeads = Core.Leads

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# NOTE 1: add tests
# actually in ms.
def calc_ventricular_rate(duration:float, samples:int|float, rr_interval:float,
                          ) -> float:
    r"""
    Calculate the ventricular (i.e. heart) rate from the RR-interval.
    
    Parameters
    ----------
    duration : float
        The duration (in milliseconds: ms) of the ECG measurement.
    samples : int or float
        The number of ECG samples.
    rr_interval : float
        The RR-interval represents the time (in ms) between two successive
        R-waves.
    
    Returns
    -------
    vrate : `float`
        The estimated ventricular rate.
    
    Notes
    -----
    The ventricular rate is calculated using the following formula:
    
    .. :math::
    
        \text{vrate} = \frac{60.0}{\text{duration}} \times
                       \frac{\text{samples}}{\text{rr_interval}}
    
    The formula is used to determine the ventricular rate (heart rate) from
    the ECG data.
    """
    # check input
    is_type(duration, (int, float))
    is_type(samples, (int, float))
    is_type(rr_interval, (int, float))
    # actual calculations
    vrate = 60.0 / duration *samples / rr_interval
    return vrate


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# NOTE 2 add tests.
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
        based on the fraction of number of samples by the sampling frequency.
        For raw wavefomrs duration determines the number of samples needed to
        get a 500hz sample: duration times 500.
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
        raise KeyError('leads I and II are not available in `signals`: '
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
