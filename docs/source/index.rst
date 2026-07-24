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

ECGProcess is a Python library for processing, standardising, and exporting
electrocardiogram (ECG) data.
It provides a unified interface for extracting waveform signals and metadata 
from heterogeneous ECG file formats, including XML and DICOM, and mapping them to
formats suitable for downstream quality control, statistical analysis, or 
machine learning pipelines.

Data processing is driven by three units:

* A file type specific **processing** units combined with a
  fixed, user supplied, configuration file mapping file entries
  to python dictionary key names.
* The table units, ``ECGTable``, which takes **processing** instance and
  loops over all ECG files available in a directory, applying optional
  standardisations using user supplied **engineering** callables.
* A **writer** callable which slots into ``ECGTable`` and tells it
  what type of file to write, allowing for optional file specific
  operations.

Together these units implement a highly customisable processing pipeline.
Users are encouraged to create their own **processing**, **engineering**, and/or
**writer** applications which can be used to extent and alter ``ECGTable``
functionally.

The module provides a plotting API built on top of matplotlib. 
This can be used for research illustrations as well as to mimic
clinical ECG prints.
These can also be batch-written to disk as illustrations or as 
numpy arrays using ``ECGTable``. 

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

A typical session reads ECG file with a file type specific reader (processor),
guided by a configuration file that says which parts of the file to
extract. The reader extracts waveform signals, median beats, and
metadata, which ``ECGTable`` can batch across many files, optionally
applying engineering steps such as resampling or lead correction,
before handing the result to a writer of your choosing.

The Quickstart pages below follow that same order: the configuration file format
first (the input format every reader depends on), 
then the reserved/privileged names to
then how a reader and ``ECGTable`` process it,
avoid, and finally how to build a custom writer.

.. toctree::
   :maxdepth: 1
   :caption: Quickstart

   configuration_files
   privileged_names
   processing_signal_data
   custom_writers

.. toctree::
   :maxdepth: 1
   :caption: Examples
   
   examples/recipe/process_xml.nblink
   examples/recipe/process_dicom.nblink
   examples/recipe/tabular.nblink
   examples/recipe/writer.nblink
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
