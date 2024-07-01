'''
A module to extract median beats and raw waveforms from DICOM ECGs.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import numpy as np
import pandas as pd
import pathlib
from pydicom import dcmread
from pydicom.waveforms import multiplex_array
from datetime import datetime
from scipy import signal
from typing import Any, List, Type, Union, Tuple, Callable
from ECGProcess.errors import (
    is_type,
    MissingDICOMTagError,
)

path = '/home/amand/google_drive/Research/ECGProcess/ECGProcess/example_data/example_datasets/example-DICOM.dcm'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

class ECGDICOMReader(object):
    """
    Takes an ECG DICOM file and extracts metadata, median beats (if available)
    and raw waveforms.

    Attributes
    ----------
    augment_leads: bool, default `False`
        Whether the augmented leads are available in the DICOM, if not
        these are calculated.
    resample: bool, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    """
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __init__(self, augment_leads:bool=False, resample_500:bool=True):
        """
        Initialises a new instance of `ECGDICOMReader`.
        
        Parameters
        ----------
        augment_leads: bool, default `False`
            Whether the augmented leads are available in the DICOM, if not
            these are calculated.
        resample: bool, default `True`
            Whether to resample the ECG to a frequency of 500 Hertz.
        """
        # test input
        is_type(augment_leads, bool, 'augment_leads')
        is_type(resample_500, bool, 'resample_500')
        # assign
        self.augment_leads = augment_leads
        self.resample_500 = resample_500
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __str__(self):
        return ("ECGDICOMReader instance with "
                 "augment_leads={self.augment_leads}, "
                 "resample_500={self.resample_500}."
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __repr__(self):
        return ("ECGDICOMReader(augment_leads={self.augment_leads}, "
                "resample_500={self.resample_500})"
                )
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, skip_empty:bool=True, verbose:bool=False,
                 ):
        """
        Read a `.dcm` DICOM file and extracts metadata, raw waveforms, and
        median beats.
        
        see `constants.DICOMTags` for the `METATDATA`, `WAVE_FORMS`, and
        `MEADIAN_BEATS` tags looked for.
        
        Parameters
        ----------
        path: str
            The path to the .dcm file.
        skip_empty: bool, default `True`
            Whether empty tags should be skipped or throw an error.
        verbose: bool, default `False`
            Prints missing tags if skip_empty is set to `True`.
        """
        is_type(path, (pathlib.PosixPath, str), 'path')
        is_type(skip_empty, bool, 'skip_empty')
        is_type(verbose, bool, 'verbose')
        # with closes automatically if an error is raised
with open(path, 'rb') as dicom:
    # reads standard dicom content
    self.ECG=dcmread(dicom)

