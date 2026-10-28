"""
Reader classes for mapping ECG files to a common representation.

This package holds the shared `BaseReader` base class and the file type
specific readers built on it: `ECGXMLReader` for XML files and
`ECGDICOMReader` for DICOM files.
"""

from ecgprocess.process.process_base import (
    BaseReader,
)
from ecgprocess.process.process_xml import (
    ECGXMLReader,
)
from ecgprocess.process.process_dicom import (
    ECGDICOMReader,
)

__all__ = [
    'BaseReader',
    'ECGXMLReader',
    'ECGDICOMReader',
]
