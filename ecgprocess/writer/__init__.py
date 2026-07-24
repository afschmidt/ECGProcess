"""
Output writers for ECG data.

This package introduces ECG writing callables which can be used with the
`tabular` module to bulk write metadata and/or signal data.

Writers subclass register themselves in the module-level `WRITERS` registry via
the `register_writer` decorator, allowing for user supplied callables which
are fully interoperable with `ECGTable` from `tabular`. User-supplied
writer classes can be checked against the `BaseWriter` requirements before a
batch run with the `WriterValidator` pre-flight class.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# the writer framework: import first so the concrete writers below can
# register themselves against a populated WRITERS/register_writer
from ecgprocess.writer.writer_base import (
    WriteContext,
    BaseWriter,
    register_writer,
    resolve_writer,
    WriterValidator,
    WRITERS,
)
# the concrete/abstract writers, in their former in-file order; each
# import runs that module's @register_writer decorators
from ecgprocess.writer.writer_table import (
    TableWriter,
    signal_dicts_to_long_table,
)
from ecgprocess.writer.writer_numpy import (
    NumpyWriter,
    NpzWriter,
    NpyWriter,
)
from ecgprocess.writer.writer_tfrecord import (
    TFRecordWriter,
)
from ecgprocess.writer.writer_figure import (
    FigureWriter,
)
from ecgprocess.writer.writer_pixel import (
    PixelWriter,
)
from ecgprocess.writer.writer_wfdb import (
    WFDBWriter,
)

__all__ = [
    'WriteContext',
    'BaseWriter',
    'register_writer',
    'resolve_writer',
    'WriterValidator',
    'WRITERS',
    'TableWriter',
    'NumpyWriter',
    'NpzWriter',
    'NpyWriter',
    'TFRecordWriter',
    'FigureWriter',
    'PixelWriter',
    'WFDBWriter',
    'signal_dicts_to_long_table',
]
