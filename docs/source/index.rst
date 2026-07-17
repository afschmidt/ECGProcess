.. ECGProcess documentation master file, created by
   sphinx-quickstart on Fri Jul  5 09:36:55 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. figure:: _static/ECGProcessSchematic.png
   :align: center
   :width: 800px
   :class: project-logo

----------------------------

ECGProcess
==========

ECGProcess is a Python library for reading, processing, and exporting
electrocardiogram (ECG) data. It provides a unified interface for
extracting waveform signals and clinical metadata from heterogeneous ECG
file formats, including XML and DICOM, and mapping them to
formats suitable for downstream quality control, statistical analysis, or 
machine learning pipelines.

Data extraction is driven by user-supplied tab-delimited configuration
files that define which signals and metadata fields to retrieve, without
requiring changes to library code. The processing pipeline can be readily 
augmented with user supplied engineering functions, to for example allow
for signal resampling or derivation of augmented leads.  Processed data
can be exported through a registry of pluggable writers, both in-memory
and in chunked on-disk workflows:

* pandas ``DataFrame`` objects for in-memory analysis;
* tab-delimited tables (``.tsv``);
* bundled (``.npz``) or per-array (``.npy``) NumPy files;
* rendered figure images (PNG, PDF, SVG);
* stacked pixel tensors for imaging-based machine learning;
* TensorFlow ``tf.data.Dataset`` objects (``tfrecord``), an optional
  extra installed with ``pip install ecgprocess[tensorflow]``.

Users can also register their own writers to add new output formats.

Additionally, the module provides a flexible plotting API built on top of
matplotlib. This can be used for research illustrations as well as to 
mimic clinical ECG prints. These can be written to disk as illustrations 
or as numpy arrays (e.g. relevant for imaging based machine learning). 

Installation
----------------------------

To install the package from PyPI, run:

.. code-block:: console

    pip install ecgprocess

or instead using conda:

.. code-block:: console

    conda install afschmidt::ecgprocess

Documentation
=============

.. toctree::
   :maxdepth: 1
   :caption: Quickstart

   processing_signal_data
   configuration_files
   custom_writers

.. toctree::
   :maxdepth: 1
   :caption: Examples
   
   examples/recipe/process_xml.nblink
   examples/recipe/process_dicom.nblink
   examples/recipe/tabular.nblink
   examples/recipe/writer.nblink
   examples/recipe/validate_writer.nblink
   examples/recipe/plot_ecgs.nblink
   examples/recipe/utils/engineering_tools.nblink

.. toctree::
   :maxdepth: 1
   :caption: Additional documentation

   api

.. toctree::
   :maxdepth: 1
   :caption: Project admin

   contributing
   raising_issues

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
