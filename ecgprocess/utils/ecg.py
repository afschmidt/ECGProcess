'''
Collecting established tools for ECG derivation or cleaning.
'''


def calc_ventricular_rate(duration:float, samples:int|float, rr_interval:float,
                          ) -> float:
    '''
    Calculate the ventricular (i.e. heart) rate from the RR-interval.

    Parameters
    ----------
    duration : float
    samples : int or float
    rr_interval : float
    
    Returns
    -------
    vrate: float
        The estimated ventricular rate.
    
    Notes
    -----
    The ventricular rate is calculated using the following formula:

    .. math::

        \begin{aligned}
        \text{vrate} &= \frac{60.0}{\text{duration}} \times \\
        &\frac{\text{samples}}{\text{rr\_interval}}
        \end{aligned}

    The formula is used to determine the ventricular rate (heart rate) from the
    ECG data.
    '''
    # check input
    # TODO
    # actual calculations
    vrate = 60.0 / duration *samples / rr_interval
    return vrate

