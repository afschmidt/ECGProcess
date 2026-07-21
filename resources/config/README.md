# Configuration files to process ECG data

It typically is fairly straightforward to extract signal data 
from XML or DICOM files. 
These files however often additionally include an abundance of metadata 
which may also be important to consider, either in downstream analysis or in
processing of the signal data. 
The process modules in ECGProcess leverage user-defined 
configuration files to extract the ECG waveform, medianbeats, 
and metadata in one go. 

## Configuration file format

The configuration files are straightforwardly organised, containing
at least one of the following headers, wrapped between `[ ]`: WaveForms,
MedianBeats, MetaData, OtherData . 

Below each header the attribute names (the name these data will be
assigned to) should be placed on the left hand side (LHS), with the
right hand side (RHS) matching the name of the source ECG file. 
The LHS and RHS should be separated by one or multiple tabs. 

The config file parsers will skip lines starting with a `#`, including
any number of leading spaces or tabs. 

### WaveForms and MedianBeats

The signal configuration structure should follow the below:

```bash
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

### Custom and extra lead names

By default, WaveForms and MedianBeats sections accept only the standard 12
lead names: `I`, `II`, `III`, `aVR`, `aVL`, `aVF`, `V1–V6`.

**Fewer leads** — declare a subset of these 12 names; the remainder will be
`None`. For example, configure only `I`, `II`, and `V1–V6` if your data has
only 8 recorded leads, and the derived limb leads (`III`, `aVR`, `aVL`,
`aVF`) can be computed by post-processing when needed.

**Additional/non-standard leads** — if your data includes extra leads beyond
the standard 12 (e.g., `V7`, `V8`, `V9` for orthogonal vectors, or `V3R`,
`V4R` for right-sided precordials), pass `extra_leads` to the `DataMap`
instance before mapping the config file:

```python
from ecgprocess.utils.config_tools import ConfigParser, DataMap

# Parse the config file with extra_leads declared
parser = ConfigParser(path='my_config.cnf')()
mapper = DataMap(extra_leads=('V7', 'V8', 'V3R'))
parser.map(mapper=mapper)
```

The config file's LHS names may now reference the extra leads:

```bash
[WaveForms]
I                       StripData.WaveformData_0.#text
...
V6                      StripData.WaveformData_11.#text
V7                      StripData.WaveformData_12.#text
V8                      StripData.WaveformData_13.#text
V3R                     StripData.WaveformData_14.#text
```

Validation will reject duplicate names within `extra_leads` and names that
collide with the standard 12 lead set.

### MetaData and OtherData

Metadata data can essentially contain any other type of data aside from the 
signal arrays.
There are some privileged attribute names here as well, please consult 
`ecgprocess.constants.CoreData.MetaData` for these.
In principle omitting some, or all of the privileged attributes names, does
not prevent the processing function from working.
Some specific arguments (i.e. such as signal resampling) might however fail 
if the metadata dues not contain sufficient information such as the
sampling frequency when asking to re-sample the signal data. 

Aside from the configured names, the readers inject a few processing
fields into `MetaData` (see `ecgprocess.constants.CoreData.ProcessingData`):
the derived `duration (waveforms, sec)` and `duration (medianbeats, sec)`,
and the per-source `sampling frequency (processed, waveforms)` and
`sampling frequency (processed, medianbeats)`. The latter two are the
authoritative rate of the stored signal arrays: they hold the resampling
target once that source has reached it, and `None` while it has not. 

The `OtherData` is currently provided as a placeholder which behaves as 
`MetaData` but does not consider any names privileged. 
It is essentially included here for future consideration of data which might
not fit the other headers. 
Currently the `OtherData` header can therefore be safely ignored. 

### File variable names

ECG data is typically provided in (semi) nested form through XMLs or DICOMs. 
To process these files the `process_xml` and `process_dicom` modules map the
file content to flat dictionaries object without any nesting. 
As such the variable names represent a concatenation of the source file 
variable names. 
Each process class instance (e.g. from `process_xml.py` or `process_dicom.py`)
has a `tags` attribute which lists the dictionary keys which can be used to
populate the RHS of the config files. 

### Combining string collected across multiple tags

Both XML and DICOM files typically collect free text, for example including things like 
diagnoses or conclusions. 
Internally these strings are broken down into chunks and assigned multiple tags. 
While these tags often have very similar names e.g., `conclusion_1, conclusion_2` 
the number of tags is essentially unlimited.
This unknown number of tags is difficult to capture in a rigid configuration file. 
To handle this the reader classes will recognise configuration entries prefixed with the 
`[STARTSWITH]` keyword, and will concatenate the content of all the matching tags 
inserting a `[DELIM]` keyword between the original text chunks. 

The [config](https://gitlab.com/SchmidtAF/ECGProcess/-/tree/master/resources/config?ref_type=heads) 
directory also includes a few example `.cnf` files to get you started. 



