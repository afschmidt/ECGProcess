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
augmented with used supplied engineering functions, to for example allow 
for signal resaumpling or derivation of augmented leads.  Processed data 
can be exported as pandas DataFrames, NumPy arrays, or TensorFlow 
``tf.data.Dataset`` objects, supporting both in-memory and chunked on-disk 
workflows.

Additionally, the module provides a flexible plotting API build on top of 
matplotlib. This can be used for research illustrations as well as to 
mimic clinical ECG prints. These can be written to disk as illustrations 
or as numpy arrays (e.g. relevant for imaging based machine learning). 

Installation
----------------------------
At present, the repository is undergoing development and no packages exist yet
on PyPy or in Conda.
Therefore it is recommended that it is installed in either of the two ways
listed below.
First, clone this repository and then cd to the root of the repository.

.. code-block:: console

    git clone git@gitlab.com:SchmidtAF/ECGProcess.git
    cd ECGProcess

Next install the dependencies using conda:

.. code-block:: console

    # From the root of the repository
    conda env create --file ./resources/conda/envs/conda_create.yaml

And pip install the package. 

.. code-block:: console

    python -m pip install .

Documentation
=============

.. toctree::
   :maxdepth: 1
   :caption: Quickstart

   processing_signal_data
   configuration_files

.. toctree::
   :maxdepth: 1
   :caption: Examples
   
   examples/recipe/process_xml.nblink
   examples/recipe/process_dicom.nblink
   examples/recipe/tabular.nblink
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
