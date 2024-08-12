'''
Collecting established tools for ECG derivation or cleaning.
'''

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from ecgprocess.errors import (
    is_type,
)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# NOTE 1: add tests
# NOTE 2: needs to extract the time unit of the ECG to ensure these are
# actually in ms.
def calc_ventricular_rate(duration:float, samples:int|float, rr_interval:float,
                          ) -> float:
    """
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
    float
        The estimated ventricular rate.
    
    Notes
    -----
    The ventricular rate is calculated using the following formula:
    
    .. math::
    
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

