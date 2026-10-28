"""
Deprecated location of the XML reader.

The reader moved to `ecgprocess.process.process_xml`. This module only
re-exports `ECGXMLReader` from there so existing imports keep working, and
warns on import. It will be removed in v2.0.0.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
import warnings
from ecgprocess.constants import (
    WriteNames as written,
)
from ecgprocess.process.process_xml import (
    ECGXMLReader,
)

__all__ = ['ECGXMLReader']

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# deprecation
warnings.warn(
    written.DEPRECATED.format(
        'ecgprocess.process_xml', written.REMOVAL_VERSION,
        'ecgprocess.process.process_xml'),
    DeprecationWarning, stacklevel=2)
