"""
Process, standardise, and export electrocardiogram (ECG) data.

ECGProcess provides a unified interface for extracting waveform signals,
median beats, and metadata from heterogeneous ECG file formats, including
XML and DICOM, and mapping them to formats suitable for downstream quality
control, statistical analysis, or machine learning pipelines.

Data processing is driven by three units: file type specific readers
(`ECGXMLReader`, `ECGDICOMReader`) guided by a user supplied configuration
file; the `ECGTable` batch processor, which loops over the ECG files in a
directory and applies optional engineering callables such as resampling or
limb lead derivation; and writer callables from the `writer` subpackage,
which determine the output format. Users can supply their own reader,
engineer, and writer callables to extend `ECGTable`.

A matplotlib-based plotting API is included for research illustrations and
clinical-style ECG prints.

Logging is emitted under the `'ecgprocess'` logger name. No handler is
attached by default, so messages are discarded unless the calling
application configures one.
"""

import logging

from ._version import __version__
from .constants import PrivilegedNames

# Silence "No handlers could be found" noise for callers that don't
# configure logging themselves.
logging.getLogger('ecgprocess').addHandler(logging.NullHandler())

__all__ = ['PrivilegedNames', '__version__']
