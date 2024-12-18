# Configuration files to process ECG data

It is should fairly straightforward to extract signal data 
from XML or DICOM files. 
These files often include an abundance of metadata which 
may also be important to consider, either in the analysis or in
the processing. 
The process modules in ECGProcess leverage user-defined 
configuration files to extract the ECG waveform, medianbeats, 
and metadata in one go. 

## Configuration file format

The configuration files are straightforwardly organised, containing
at least one of the following headers, wrapped in `[ ]`: WaveForms,
MedianBeats, MetaData, OtherData . 

Below each header the attribute names (the name the data will be
assigned to) should be placed on the left hand side, with the right
hand side matching the name of the source ECG file. 
The LHS and RHS should be separated by one or multiple tabs. 

The config file parsers will skip lines starting with a `#`, including
any number of leading whites spaces (i.e. spaces or tabs). 

### WaveForms and MedianBeats

The signal configuration structure should follow the below:

```{bash}
[WaveForms]
I					StripData.WaveformData_0.#text
II					StripData.WaveformData_1.#text
III					StripData.WaveformData_2.#text
aVR					StripData.WaveformData_3.#text
aVL					StripData.WaveformData_4.#text
aVF					StripData.WaveformData_5.#text
V1					StripData.WaveformData_6.#text
V2					StripData.WaveformData_7.#text
V3					StripData.WaveformData_8.#text
V4					StripData.WaveformData_9.#text
V5					StripData.WaveformData_10.#text
V6					StripData.WaveformData_11.#text
[MedianBeats]
I					RestingECGMeasurements.MedianSamples.WaveformData_0.#text
II					RestingECGMeasurements.MedianSamples.WaveformData_1.#text
III					RestingECGMeasurements.MedianSamples.WaveformData_2.#text
aVR					RestingECGMeasurements.MedianSamples.WaveformData_3.#text
aVL					RestingECGMeasurements.MedianSamples.WaveformData_4.#text
aVF					RestingECGMeasurements.MedianSamples.WaveformData_5.#text
V1					RestingECGMeasurements.MedianSamples.WaveformData_6.#text
V2					RestingECGMeasurements.MedianSamples.WaveformData_7.#text
V3					RestingECGMeasurements.MedianSamples.WaveformData_8.#text
V4					RestingECGMeasurements.MedianSamples.WaveformData_9.#text
V5					RestingECGMeasurements.MedianSamples.WaveformData_10.#text
V6					RestingECGMeasurements.MedianSamples.WaveformData_11.#text
```

Here the RHS will depend on the specific file that is being processed. 
The LHS names are privileged, meaning that the processing methods will ignore
any other words or characters that do not exactly match the provided example. 

_Note_: you can completely omit the header, or only specify a subset of lead 
names.  The processing methods will simply assign `None` values to missing
lead names. 

### MetaData and OtherData

Metadata data can essentially contain any other type of data aside from the 
signal arrays.
There are some privileged attribute names here as well, please consult 
`ecgprocess.constant.CoreData.MetaData` for these. 
In principle omitting some, or all of the privileged attributes names, does
not prevent the processing function from working.
Some specific arguments (i.e. such as signal 
resampling) might however fail if the metadata dues not contain sufficient 
information such as the sampling frequency when asking to re-sample the 
signal data. 

The `OtherData` is currently provided as a place holder which behaves as 
`MetaData` but does not consider any names privileged. 
It is essentially included here for future consideration of data which might
not fit the other headers. 
Currently this header can therefore be safely ignored. 

### File variable names

ECG data is typically provided in (semi) nested form through XMLs or DICOMs. 
To process these files the `process_xml` and `process_dicom` modules map the
file content to flat dictionaries object without any nesting. 
As such the variable names represent a concatenation of the source file 
variable names. 
Each process class instance has a `tags` attribute which lists the 
dictionary keys which can be used to populate the RHS of the config files. 

The current directory also includes a few example `.cnf` files to get 
you started. 



