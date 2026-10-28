"""
Deprecated location of the DICOM reader.

The reader moved to `ecgprocess.process.process_dicom`. This module only
re-exports `ECGDICOMReader` from there so existing imports keep working, and
warns on import. It will be removed in v2.0.0.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import warnings
from ecgprocess.constants import (
    WriteNames as written,
)
from ecgprocess.process.process_dicom import (
    ECGDICOMReader,
)

__all__ = ['ECGDICOMReader']

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# deprecation
warnings.warn(
    written.DEPRECATED.format(
        'ecgprocess.process_dicom', written.REMOVAL_VERSION,
        'ecgprocess.process.process_dicom'),
    DeprecationWarning, stacklevel=2)
