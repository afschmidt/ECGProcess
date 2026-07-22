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

Data processing is driven by three ingredients:

* A file type sepcific ``processing`` callable combined with a 
  a fixed, user supplied, configuration file mapping file entries 
  to python dictionary key names. 
* The core ``ECGTable`` instance take a ``processing`` instance and 
  loops over all ECG files available in a directory, applying optional 
  file specific standardisations using user supplied engineering 
  callables. 
* A ``writer`` callable which slots into ``ECGTable`` and tells it 
  what type of file to write to, allowing for optional file specific
  opperations. 

The processing pipeline is highly flexible and users are 
encouraged to create their own ``processing``, ``engineering``, and/or
``writer`` applications which can be used to extent and alter ``ECGTable``
functionally.

Additionally, the module provides a flexible plotting API built on top of
matplotlib. This can be used for research illustrations as well as to 
mimic clinical ECG prints. These can be written to disk as illustrations 
or as numpy arrays using ``ECGTable``. 

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
   privileged_names
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
