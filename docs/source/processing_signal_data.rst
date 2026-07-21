===================
Processing ECG data
===================

To process ECG data ECGprocess leverages three key components 

* A configuration file which maps file content to class attributes
  acting as an API. Please see the next section for a full discussion 
  on these files. 

* A reader class which uses the configuration file to extract the 
  data from the ECG file and groups these into: MetaData, 
  WaveForms, and MedianBeats. Reader classes are file type 
  specific (e.g. XML, DICOM) and depending on the file type 
  can optionally include validation steps (e.g. using XML 
  schema's).

  All reader classes are able to perform data augmentation steps such as re-sampling 
  the ECG signal and calculating the peripheral leads if 
  these were omitted for the source file. 

* ``ECGTable`` processes any type of ECG data (with a corresponding
  reader class) and can chunk multiple files into a pandas table or writes
  them to disk through a pluggable writer registry. The output format is
  chosen with the ``writer`` argument of ``ECGTable.write_ecg``:

  - ``'table'`` — tab-delimited .tsv tables (the default);
  - ``'npz'`` — a single bundled NumPy .npz archive;
  - ``'npy'`` — one .npy file per data source;
  - ``'tensorflow'`` — binary tfrecord files;
  - ``'wfdb'`` — one WFDB (PhysioNet) record per ECG UID;
  - ``'figure'`` — a rendered ECG image per record (e.g. PNG, PDF, SVG);
  - ``'pixel'`` — stacked pixel tensors for imaging-based machine learning.

  _Note_: tensorflow and wfdb are strictly optional package and will need 
  to be installed separately, e.g. ``pip install ecgprocess[tensorflow]``. 

  The ``writer`` argument also accepts any ``BaseWriter`` subclass or
  callable, allowing new formats without changing library code; see
  :doc:`custom_writers`. The ``validate_writer`` callable in ``writer.py``
  can be used to validate any custom build writer class.  
  _Note_: the ``file_type`` argument is deprecated and will be removed in version
  2.0.0.

  ``ECGTable`` jointly processes metadata, waveforms, and median beats,
  enabling on-the-fly QC/filtering and downstream multimodal analyses.
  Engineering parameters accept callables applied to each record's data 
  which can be used to augment the reader class processing step.
  Possible engineering steps include signal calibration, filtering, or device-based
  validation. 
  The ``LeadMapper`` class standardises lead order for devices writing channels out of 
  sequence which is useful for processing DICOMS or other file types without
  self-documenting tags/attributes. 
  Again the engineering callables can be fully user defined, but a core set is 
  included in `ecgprocess.utils.engineering_tools`.

Regarding the configuration file, please consult the :ref:`setting up a configuration file <configuration>`
section as well as the example Jupyter notebooks.

Signal processing
-----------------

The reader classes apply two optional processing steps, in order, once
the configured data has been extracted:

* ``resample_500`` (``bool``, default ``True``) — resamples the
  waveform and median beat signals to 500 Hz using
  :func:`scipy.signal.resample`. Each is resampled to ``duration × 500``
  samples, where duration is derived from the metadata (sampling number /
  sampling frequency). The WaveForms and MedianBeats are gated independently:

  - already at 500 Hz — no resampling; arrays left untouched;
  - duration cannot be derived (missing sampling number) — a warning is
    issued and the source remains at its original rate;
  - *sampling frequency (original)* missing — a ``KeyError`` is raised.

  The readers record each source's final rate in the metadata. Processed
  rates are stored under *sampling frequency (processed, waveforms)* and
  *sampling frequency (processed, medianbeats)* (500 if resampled or
  already at target, ``None`` otherwise). Derived durations are recorded
  as *duration (waveforms, sec)* and *duration (medianbeats, sec)*.
  Downstream code uses the processed frequency, falling back to
  *sampling frequency (original)* when absent.

* ``augment_leads`` (``bool``, default ``False``) — derives the
  remaining limb leads (III, aVR, aVL, aVF) from leads I and II,
  filling only those absent from the source; present leads are never
  overwritten. Both leads I and II must be present, otherwise a
  ``KeyError`` is raised.

Fixed-length signals
--------------------

``ECGTable`` accepts three opt-in parameters that fix the per-record
sample count of ``WaveForms`` and ``MedianBeats`` signals before the
engineering callables run:

* ``signal_length_w`` (``int`` or ``None``, default ``None``) — the target
  sample count for waveforms.
* ``signal_length_m`` (``int`` or ``None``, default ``None``) — the target
  sample count for median beats.
* ``pad_value`` (``int`` or ``float``, default ``0.0``) — the fill value
  when right-padding; _note_: the original array dtype is preserved.

When set, each lead is right-padded with ``pad_value`` or right-truncated
to the target length. 
Three metadata values are always recorded regardless of opt-in, keeping 
the output schema stable:
*sampling number padded (waveforms)*,
*sampling number padded (medianbeats)*, and
*duration padded (sec)*.

_Note_ these are also privileged variable names and should not be overwritten. 

Engineering callables
---------------------

``ECGTable`` exposes three callable hooks for on-the-fly curation:

* ``engineer_meta`` — receives the metadata dict for each record and
  returns a transformed version.
* ``engineer_wave`` / ``engineer_median`` — receive the signal dict and
  return a transformed version. Both receive a ``meta_dict`` keyword
  argument with the current record's metadata, enabling
  frequency-aware operations.

Ready-to-use callables in ``ecgprocess.utils.engineering_tools``:

* ``LeadMapper`` — normalises lead order for devices that write channels
  out of sequence.
* ``metadata_checkversion`` — validates device version, manufacturer,
  and model.
* ``signal_correction`` — applies gain and baseline correction.
* ``signal_standardise_res`` — rescales signal amplitude to a target
  resolution (e.g. converts 10 μV/sample to 5 μV/sample by multiplying
  each sample by 2).

Users can supply any callable matching the signature above in place of or
alongside these built-ins.
For example the augmented leads calculation and 
resampling functions are available from ``ecgprocess.utilts.ecg_tools`` 
and could be stacked in a single engineering callable. 
