=================
Writers catalogue
=================

``ECGTable.write_ecg`` ships seven built-in output formats, selected
through the ``writer`` argument's registry key.
This page gives a one-paragraph summary of each; see :doc:`custom_writers` for how to
build your own, and :doc:`examples/recipe/writer` for a worked example
of every writer below.

Flat tables
-----------

``TableWriter`` (``writer='table'``) writes each extracted source to a
tab-delimited, optionally gzip-compressed file: metadata.tsv.gz,
waveforms.tsv.gz, and medianbeats.tsv.gz.
The signal files are long-format, so records of differing length need no padding. Covered
in depth in the :doc:`examples/recipe/tabular` recipe.

NumPy arrays
------------

``NumpyWriter`` is the abstract base for two registered writers that
bundle sources into NumPy arrays: ``NpzWriter`` (``writer='npz'``)
stacks every source into a single bundled ecg_data.npz archive, while
``NpyWriter`` (``writer='npy'``) writes one .npy file per source
(metadata.npy, waveforms.npy, medianbeats.npy).
Both drop non-numeric metadata columns to a header_metadata.txt sidecar
and require a fixed signal length (``signal_length_w`` /
``signal_length_m`` on ``ECGTable``).

TensorFlow records
------------------

``TFRecordWriter`` (``writer='tensorflow'``) serialises the stacked
arrays into a single binary tfrecord file, the native input format
for ``tf.data`` pipelines.
Waveforms and median beats are each stored as one ``tf.io.serialize_tensor``
binary string, which keeps the original ``(n_records, n_leads, n_samples)``
shape and dtype attached to the data; decode a source with
``tf.io.parse_tensor(value, out_type=tf.float32)``, naming the dtype the
array was written in.
Metadata stays a flattened numeric array with column names in a
header_metadata.txt sidecar, the same convention used by the NumPy writers.
TensorFlow is an optional dependency (``pip install ecgprocess[tensorflow]``),
lazily imported at write time.

Rendered figures
----------------

``FigureWriter`` (``writer='figure'``) renders one ECG image per
record through an ``ECGDrawing`` and saves it as one image file per
UID.
It renders exactly one signal source per call. See :doc:`examples/recipe/plot_ecgs`
for the underlying drawing API.

Stacked pixel arrays
--------------------

``PixelWriter`` (``writer='pixel'``), a ``FigureWriter`` subclass,
renders the same figures but rasterises and stacks them into a single
tensor saved as figures.npy, with optional file-aligned metadata.tsv.

WFDB/PhysioNet
--------------

``WFDBWriter`` (``writer='wfdb'``) writes one PhysioNet WFDB record
per ECG UID: a multiplexed, format-16 (int16) signal file paired with
a header file carrying user-selected metadata as comment lines.
A WFDB record is single-source: it cannot combine waveforms and median beats in one file.
The ``wfdb`` package is an optional dependency.

XML export
----------

``XMLWriter`` (``writer='xml'``) writes one XML document per ECG UID
from a user-supplied template, with optional XSD validation before
each write. 
An XML may draw on metadata, waveforms, and median beats all at once.
See :doc:`xml_writer` for the template format and validation behavior in full.
