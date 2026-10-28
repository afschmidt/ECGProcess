"""
The processing framework: `BaseReader`.
"""

import warnings
import numpy as np
import ecgprocess.utils.reader_tools as reader_utils
import ecgprocess.utils.ecg_tools as ecg_utils
from typing import (
    Optional, Self, Any,
)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)
from ecgprocess.errors import (
    is_type,
    Warn_MSG,
    Error_MSG,
)
from ecgprocess.constants import (
    CoreData as Core,
)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CProc = Core.ProcessingData
CLeads = Core.Leads
CMeta = Core.MetaData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Base class
class BaseReader:
    '''
    A base class for ECG readers, holding the four data categories and a
    generic `extract` method which maps the raw parsed tags to these
    categories based on a configuration file.
    '''
    # #### defaults, subclasses may override these
    _as_array:bool = True
    augment_leads:bool = False
    resample_500:bool = True
    verbose:bool = False
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, waveforms=None, medianbeats=None, metadata=None,
                 otherdata=None, raw=None):
        '''
        Initialises the data attributes to `None`.
        '''
        setattr(self, CTypes.WaveForms, waveforms)
        setattr(self, CTypes.MedianBeats,medianbeats)
        setattr(self, CTypes.MetaData,metadata)
        setattr(self, CTypes.OtherData, otherdata)
        setattr(self, CProc.RAW,raw)
    # /////////////////////////////////////////////////////////////////////////
    def extract(self, config:ConfigParser, bits:np.dtype | None=None,
                skip_empty:bool=True, parse_numeric:bool=True,
                **kwargs:Optional[Any]) -> Self:
        '''
        Processes the raw ECG data and assign these to class attributes
        performing resampling and lead augmentation if requested.
        
        Parameters
        ----------
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the
            source file content to class attributes. Specifically this should
            include dictionary attributes `MetaData`, `WaveForms`,
            `MedianBeats`, `OtherData`. The `MetaData` includes some
            privileged keys including essential information to describe an
            ECG instance, as well as non-privileged information. The
            difference between `OtherData` and `MetaData` is the way it is
            processed by other functions or methods with the `OtherData`
            processed without strong checks on its content. `WaveForms` and
            `MedianBeats` simply include the lead mappings. Please refer to
            the `constants.CoreData` class for the specifics
        bits : `np.dtype`, default `None`
            np.array bits passed to numpy.array dtype.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        parse_numeric : bool, default `True`
            Whether to check for numeric data accidentally recorded as string
            and try to parse these to int or float depending on the presence
            of a decimal separator.
        **kwargs
            The keyword arguments for reader_tools.get_ecg_data.
            For the waveforms and medianbeats as_array and bits are hard coded
            so these will raise an error if supplied as kwargs.
        
        Attributes
        ----------
        MetaData : `dict` [`str`, `any`]
            ECG metadata.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianBeats : `dict` [`str`, `np.array`]
            The lead specific ECG median beats.
        OtherData : `dict` [`str`, `any`]
            Other data.
        
        Returns
        -------
        self : `BaseReader` instance
            Returns the class instance with updated attributes including the
            extracted data.
        
        Raises
        ------
        KeyError
            If resampling is requested without the original sampling
            frequency, or lead augmentation without leads I and II.
        '''
        is_type(config, ConfigParser)
        is_type(skip_empty, bool)
        is_type(parse_numeric, bool)
        # update kwargs
        kwargs = {**{'parse_numeric': parse_numeric,
                     'skip_empty': skip_empty,
                     }, **kwargs}
        # #### get the configs
        md_cnf = config.get_section(CTypes.MetaData)
        wf_cnf = config.get_section(CTypes.WaveForms)
        mb_cnf = config.get_section(CTypes.MedianBeats)
        od_cnf = config.get_section(CTypes.OtherData)
        # #### extract metadata
        meta_data, meta_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=md_cnf,
                **kwargs,
            )
        # #### extract waveforms
        wave_data, wave_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=wf_cnf,
                as_array=self._as_array,
                bits=bits,
                **kwargs,
            )
        # #### extract median beats
        median_data, median_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=mb_cnf,
                as_array=self._as_array,
                bits=bits,
                **kwargs,
            )
        # #### extract other data
        other_data, other_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=od_cnf,
                **kwargs,
            )
        # #### resample to 500hz
        # first calculate the per-source durations
        sf_org = meta_data.get(CMeta.SF)
        meta_data[CProc.Duration_W] = _signal_duration(
            meta_data.get(CMeta.SN_W), sf_org)
        meta_data[CProc.Duration_M] = _signal_duration(
            meta_data.get(CMeta.SN_M), sf_org)
        # only run when the parameter is True and SF is present
        meta_data[CProc.SF_NEW_W] = None
        meta_data[CProc.SF_NEW_M] = None
        if getattr(self, CProc.RESAMPLE):
            # confirm SF is present
            if sf_org is None:
                raise KeyError(f'`{CMeta.SF}` is necessary to resample '
                               'the ECG signal.')
            if int(sf_org) == 500:
                # already at target, record but skip resampling
                meta_data[CProc.SF_NEW_W] = 500
                meta_data[CProc.SF_NEW_M] = 500
            else:
                # each source is gated on its own duration, so a missing
                # sampling number for one does not block the other
                wave_data, meta_data[CProc.SF_NEW_W] = _resample_source(
                    wave_data, meta_data[CProc.Duration_W], 'waveform',
                    skip_empty)
                median_data, meta_data[CProc.SF_NEW_M] = _resample_source(
                    median_data, meta_data[CProc.Duration_M], 'median beat',
                    skip_empty)
        # ### See if we need to get the augmented leads
        # leads that can be derived from I and II
        _aug = {CLeads.III, CLeads.aVR, CLeads.aVL, CLeads.aVF}
        if getattr(self, CProc.AUG_LEADS):
            # augment each dataset when any derived lead is absent;
            # get_limb_leads raises KeyError if source leads I/II are missing
            if any(wave_data.get(l) is None for l in _aug):
                wave_data = ecg_utils.get_limb_leads(wave_data)
            if any(median_data.get(l) is None for l in _aug):
                median_data = ecg_utils.get_limb_leads(median_data)
        # ### do we print missing tags
        if self.verbose:
            missing_tags = [tag for tag in (
                meta_missing + wave_missing + median_missing + other_missing
            ) if tag is not None]
            if len(missing_tags)>0:
                warnings.warn(Warn_MSG.MISSING_TAG.format(missing_tags))
        # #### assign stuff to attributes
        setattr(self, CTypes.MetaData, meta_data)
        setattr(self, CTypes.OtherData, other_data)
        setattr(self, CTypes.WaveForms, wave_data)
        setattr(self, CTypes.MedianBeats, median_data)
        # #### return stuff
        return self

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# helpers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _signal_duration(sampling_number: int | float | None,
                     sampling_freq: int | float | None,
                     ) -> float | None:
    """
    Derive a signal duration in seconds from the sampling metadata.
    
    Parameters
    ----------
    sampling_number : `int`, `float`, or `NoneType`
        The number of samples of the signal source.
    sampling_freq : `int`, `float`, or `NoneType`
        The original sampling frequency.
    
    Returns
    -------
    duration : `float` or `NoneType`
        The duration in seconds, or `NoneType` when either input is
        absent (the privileged metadata keys are optional).
    """
    try:
        return sampling_number / sampling_freq
    except TypeError:
        return None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _resample_source(signals: dict[str, np.array],
                     duration: int | float | None,
                     signal_name: str,
                     skip_empty: bool,
                     ) -> tuple[dict[str, np.array], int | None]:
    """
    Resample a single signal source to 500 hz.
    
    Parameters
    ----------
    signals : `dict` [`str`, `np.array`]
        The lead signals of one source (waveforms or median beats).
    duration : `int`, `float`, or `NoneType`
        The duration of this source in seconds; `NoneType` when it could
        not be derived, in which case the source is left untouched.
    signal_name : `str`
        The source name used in the warning and error messages.
    skip_empty : `bool`
        Whether a source without any data is skipped or raises.
    
    Returns
    -------
    signals : `dict` [`str`, `np.array`]
        The resampled signals, or the originals when not resampled.
    sf_new : `int` or `NoneType`
        500 when the source is at the target, `NoneType` otherwise.
    
    Raises
    ------
    AttributeError
        If the source holds no data while `skip_empty` is False.
    """
    if duration is None:
        warnings.warn(Warn_MSG.RESAMPLE_NO_DURATION.format(signal_name))
        return signals, None
    if all(v is None for v in signals.values()):
        if not skip_empty:
            raise AttributeError(Error_MSG.MISSING_SIGNAL.format(signal_name))
        return signals, 500
    return ecg_utils.resampling_500hz(signals, duration=duration), 500

