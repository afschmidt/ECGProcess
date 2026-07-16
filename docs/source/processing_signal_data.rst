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

  All reader classes are able to perform
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

Please consult the :ref:`setting up a configuration file <configuration>`,
section as well as the example Jupyter notebooks.

Signal processing
-----------------

The reader classes apply two optional processing steps, in order, once
the configured data has been extracted:

* ``resample_500`` (``bool``, default ``True``) — resamples the
  waveform and median beat signals to 500 Hz using
  :func:`scipy.signal.resample`. Each source is resampled to
  ``duration × 500`` samples, its duration derived as ``sampling number
  / sampling frequency (original)`` — using ``sampling number
  (waveforms)`` for waveforms and ``sampling number (medianbeats)`` for
  median beats. A median beat is conventionally 1.2 s, giving the
  familiar 600 samples, but the duration is read from the metadata
  rather than assumed.

  The two sources are gated independently:

  - the file is already at 500 Hz — no resampling is needed and the
    arrays are left untouched;
  - a source's duration cannot be derived (an absent sampling number) —
    a warning is issued and that source alone is left at its original
    rate;
  - ``sampling frequency (original)`` is absent — a ``KeyError`` is
    raised, as no resampling can be defined without it.

  The readers record the rate of each stored source in the metadata,
  under ``sampling frequency (processed, waveforms)``
  (:attr:`~ecgprocess.constants.CoreData.ProcessingData.SF_NEW_W`) and
  ``sampling frequency (processed, medianbeats)``
  (:attr:`~ecgprocess.constants.CoreData.ProcessingData.SF_NEW_M`): 500
  when that source is known to be at the target rate (whether or not a
  resample was needed), and ``None`` otherwise, in which case it remains
  at the original frequency. The derived durations are recorded
  alongside as ``duration (waveforms, sec)`` and ``duration
  (medianbeats, sec)``. Downstream consumers treat the processed
  frequency as the authoritative rate of the stored arrays, falling back
  to ``sampling frequency (original)`` — e.g. the ``duration padded
  (sec)`` column written by the fixed-length option below.

* ``augment_leads`` (``bool``, default ``False``) — derives the
  remaining limb leads (III, aVR, aVL, aVF) from leads I and II,
  filling only those absent from the source file; leads present in the
  source are never overwritten. Both leads I and II must be present,
  otherwise a ``KeyError`` is raised.

Fixed-length signals
--------------------

``ECGTable`` accepts three opt-in parameters that fix the per-record
sample count of the ``WaveForms`` and ``MedianBeats`` signals before
the engineering callables run:

* ``signal_length_w`` (``int`` or ``None``, default ``None``) — target
  sample count for waveforms.
* ``signal_length_m`` (``int`` or ``None``, default ``None``) — target
  sample count for median beats.
* ``pad_value`` (``int`` or ``float``, default ``0.0``) — fill value
  used when right-padding shorter signals; the original array dtype is
  preserved.

When set, each lead in the corresponding signal dict is right-padded
with ``pad_value`` or right-truncated to the target length. Three
metadata columns are written to every output regardless of opt-in so
the output schema remains stable across runs:
``sampling number padded (waveforms)``,
``sampling number padded (medianbeats)``, and
``duration padded (sec)``.

Engineering callables
---------------------

``ECGTable`` exposes three callable hooks for on-the-fly curation:

* ``engineer_meta`` — receives the metadata dict for each record and
  returns a transformed version.
* ``engineer_wave`` / ``engineer_median`` — receive the waveform or
  median beat signal dict and return a transformed version. Both also
  receive a ``meta_dict`` keyword argument containing the current
  record's metadata, enabling sample-frequency-aware operations.

A collection of ready-to-use callables is provided in
:mod:`ecgprocess.utils.engineering_tools`:

* :class:`~ecgprocess.utils.engineering_tools.LeadMapper` — normalises
  lead order for devices that write channels in a non-standard sequence.
* :class:`~ecgprocess.utils.engineering_tools.WaveformMapper` — remaps
  waveform keys to a canonical naming scheme.
* :func:`~ecgprocess.utils.engineering_tools.metadata_checkversion` —
  validates device version, manufacturer, and model against expected
  values.
* :func:`~ecgprocess.utils.engineering_tools.signal_correction` —
  applies gain and baseline correction.
* :func:`~ecgprocess.utils.engineering_tools.signal_standardise_res` —
  resamples signals to a target resolution.

Users can supply any callable that conforms to the signature above in
place of or alongside these built-in functions.
