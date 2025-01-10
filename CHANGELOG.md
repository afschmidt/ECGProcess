# Changelog

## v1.0.0a - 10-12-2024

### Fixed

- Bug fixes to FixedDICOMReader - the older ECGDICOMReader. 
- Document improvements/errors. 

### Added

- A tabular module containing the ECGTable class. This class is a file type agnostic class mapping ECG data to table or files. 
- A reader classes for XML and DICOM files, see the various process_\*.py files. 
- Extensive utils modules. 
- Example configuration files for XML and DICOMs.
- Example XML schema, for XML validation.
- Added TensorFlow as dependency.

### Changed

- process_dicom has been refactored. The previous ECGDICOMReader class has been renamed to FixedDICOMReader which was slightly optimised. 
  The new ECGDICOMReader is now in-line with the process_xml ECGXMLReader class. 
- Changed the base docker environment to allow for tensorflow. 

### Deprecated

- FixedDICOMReader, will be deprecated in futre. 

### Removed

- ECGDICOMTable has been removed, please use `ECGTable` instead. 

## v0.2.2 - 20-12-2024

### Fixed

- Fixed ECGDICOMTable bug when the metadata is empy. 
- Bug fix for ECGDICOMReader to handle NoneType ECG measurments.

### Added

- Added kwargs to ECGDICOMTable for the reader and writing functions. 
- ECGDICOMReader extract free text and pacemaker spike information. 
- Improved pytest coverage. 

### Changed

_Noting_

### Deprecated

_Nothing_

### Removed

_Nothing_

## v0.2.1 - 22-10-2024

### Fixed

- Multiple documentation improvements. 
- Compression now accepts a NoneType argument. 

### Added

- Added a get_metadata method. 
- Siloed off code to create the private methods \_get_waveform_annotation and \_write_internal.
- Added a write_pdf method.

### Changed

- The leads in the ECG plotting functions can now all start from the same time moment, instead of consecutive leads starting when from the time the previous lead stopped. 

### Deprecated

_Nothing_

### Removed

_Nothing_

## v0.2.0 - 18-08-2024

### Fixed

_Nothing_

### Added

- The module plot_ecgs.py facilitating mapping tabular ECG signals to images, and images back to numerical arrays. 
- Added docs, pytest, and examples for plot_ecgs.py

### Changed

_Nothing_

### Deprecated

_Nothing_

### Removed

_Nothing_

