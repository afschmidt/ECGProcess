===================
Processing ECG data
===================

To process ECG data ECGprocess leverages three key components 

* A configuration file which maps file content to class attributes
  acting as an API. Please see the next section for a full discussion 
  on these files. 

* A reader class which uses the configuration file to extract the 
  data from the ECG file and groups these into: MetaData, 
  WaveForms, and MedianBeats. Reader classes will be file type 
  specific (e.g. XML, DICOM) and depending on the file type 
  can optionally include validation steps (e.g. using XML 
  schema's).

  All reader classes are be able to perform 
  rudimentary data augmentation steps such as re-sampling 
  the ECG signal and calculating the peripheral leads if 
  these were omitted for the source file. 

* By encoding the API in the reader class the `ECGTable` class 
  can process any type of ECG data (as long as there is a 
  reader class for) and load multiple files into pandas table, 
  or write these to disk (as tsv tables, npz array, or binary 
  tfrecords). 

  The ECGTable class is specifically designed to 
  jointly process metadata, as well as waveform and medianbeat
  signals allowing for on the fly QC/filtering as well as downstream
  multimodal analyses. To perform on the fly QC/filtering the ECGTable
  class included engineering parameters which take callable/function 
  objects which are applied to the reader class data attributes. 
  This can be used to perform additional data cleaning such as 
  signal calibration, low/high-pass filtering, or informal
  file validation based on version/manufacturer tags. The built-in
  ``LeadMapper`` callable (``ecgprocess.utils.engineering_tools``) handles
  lead-order normalisation for devices that write channels in a non-standard
  sequence.

Please consult the following section on setting up a configuration file, 
as well as the example Jupyter notebooks. 
  
