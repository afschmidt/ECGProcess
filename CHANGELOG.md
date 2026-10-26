# Changelog

### Unreleased

#### Added

* Lead names other than the standard 12 are accepted in the WaveForms
  and MedianBeats sections when `extra_leads` is true on `DataMap`.
* Reserved lead and metadata field names are listed by
  `PrivilegedNames` (`from ecgprocess import PrivilegedNames`).
* Duration and the sampling frequency after processing are recorded
  separately for waveforms and for median beats.
* One signal source is measured and resampled by `_signal_duration`
  and `_resample_source` in `process_xml`.
* New output formats plug in through `ecgprocess.writer`, which holds
  the `WRITERS` registry, the dispatch path, a base class, and the
  context object handed to each write.
* A registry name, a writer object, or a plain function can be passed
  as `writer` to `ECGTable.write_ecg`.
* One array file per signal source is saved by `NpyWriter`.
* One ECG image per record is saved by `FigureWriter`, with the axis
  spines hidden.
* Stacked signal rasters are saved by `PixelWriter`, one array per
  chunk.
* Metadata is drawn onto a figure from a template string by
  `ECGDrawing.annotate`.
* Signal dictionaries are turned into a long table by
  `signal_dicts_to_long_table`.
* Output filenames shared across writers are fixed in `FileNames`.
* TensorFlow and wfdb are optional extras: they import when a writer
  needs them, and tests skip when the packages are not installed.
* The checklist for a `BaseWriter` is printed by
  `WriterValidator.describe`, and a failed check quotes that writer's
  `write` signature.
* The documentation adds a custom-writer guide and a notebook that
  walks through a validation failure.
* A PhysioNet WFDB record is written by `WFDBWriter`, with a choice of
  signal source and which metadata to store.
* Every metadata key is copied into the WFDB comments when
  `meta_fields='all'`.
* A record is skipped when some of its leads were not extracted, if
  `ignore_missing_leads` is true on `ECGTable`.
* A missing optional dependency, or a writer that fails validation,
  raises an error that names what went wrong.
* Only successful extracts count toward `chunk` when `chunk_strict` is
  true on `ECGTable.write_ecg`, and further files are read to fill the
  batch.
* ECG can be written to XML (one file per input ECG) using templates
  for metadata, waveforms, and median beats. 
  See `XMLWriter` (`writer='xml'`), with an optional
  schema check compiled once for that writer.
* Schema files and written documents are parsed with entity resolution
  and network access turned off.
* An invalid schema file stops the write before any record is
  processed, a document that is not well-formed XML is skipped, and
  template keys must be legal XML names.
* Example XML writer paths come from `list_xml_writer_paths`, and the
  docs add a writer catalogue plus an XML writer page.
* Before the first batch, `ECGTable.write_ecg` calls `BaseWriter.reset`,
  which `TableWriter` uses to write its header again on a reused writer.

#### Changed

* Each field a writer receives is documented on `WriteContext`,
  including that failures are recorded by appending to `failed_records`.
* Median-beat resampling takes its length from that beat's duration,
  and waveform resampling is switched separately from median beats.
* Padded-duration metadata uses the sampling frequency taken after
  processing.
* File output runs through `ecgprocess.writer`, and `ECGTable.write_ecg`
  picks the writer from the registry.
* TensorFlow is an optional dependency, imported inside
  `TFRecordWriter` only when that writer runs.
* Each waveform and median beat is stored as a serialised tensor by
  `TFRecordWriter`, so `tf.io.parse_tensor` can restore the original
  shape and dtype.
* `xmltodict` must be version 1.0.3 or newer .
* Reader configuration examples moved to `resources/config/reader`, and
  the XML writer template lives in `resources/config/writer`.
* GitLab CI runs the tests on Python 3.11, 3.12, and 3.13 for every
  branch, with Docker tags `py311`, `py312`, and `py313`.
* The CI debug scripts take their settings from `.gitlab-ci.yml` and
  check that Docker is available before starting a matrix run.

#### Deprecated

* The `file_type` argument of `ECGTable.write_ecg` is deprecated in
  favour of `writer` and the legacy `'numpy'`
  value is renamed `'npz'`.

#### Fixed

* Waveform and median-beat rows stay in record order in
  `signal_dicts_to_long_table`, with `row_order` of `'sample'` or
  `'lead'` on `TableWriter` and through `kwargs_long_table` on
  `ECGTable.get_table`.
* An archive is built outside `old_dir` and then moved into place by
  `replace_with_tar`, which raises `ValueError` when `new_tar` lies
  inside `old_dir` and `FileExistsError` when the destination directory
  is missing.
* A failed metadata read with `ignore_data=True` and
  `confirm_meta=False` stores empty metadata for that record in
  `ECGTable._loop_table`.
* Skipping a record in `ECGTable._loop_table` drops that record's key,
  and a failed metadata read is entered once in the "no data" list.
* A `chunk` that is not a positive number is rejected by
  `ECGTable.write_ecg`, which also requires `parsed_config` and logs
  the payload from the default identity callables when `verbose=True`.
* An integer number is accepted as well as a float by `signal_calibration`
  and `signal_resolution`, and the `signal_resolution` example calls
  `signal_resolution`.
* When the interpreter provides no stack frame, as on PyPy,
  `get_param_name` returns `None`.
* The calibration pulse overwrites the opening samples of each selected
  lead, so the trace keeps its original length.
* `make install-dev` installs the editable package with the `[dev]`
  extras.

#### Removed

* The `median` argument of `resampling_500hz` is removed, because each
  source already supplies its own duration.
* The shared `duration (sec)` and `sampling frequency (processed)`
  columns are removed and replaced by the per-source columns.
* Private write helpers on `ECGTable` (`_write_numpy`, `_write_tfr`,
  `_write_header`, `_write_file_names`, and `_get_long_table`) moved
  into `ecgprocess.writer`.
* The write-type constant `TabNames.WRITE_TYPE` is removed and replaced
  by the writer registry and `FileNames`.

### 1.1.0 - 2026-05-02

#### Added

* `signal_length_w`, `signal_length_m`, and `pad_value` parameters
  on `ECGTable.__init__` for an opt-in fixed-length pad/truncate of
  per-record `WaveForms` and `MedianBeats` signals before the
  engineer callables run
* `ECGTable._pad_or_truncate` private method implementing the
  right-pad / right-truncate per-lead logic with dtype preservation
* `SN_W_PADDED`, `SN_M_PADDED`, and `DURATION_PADDED` metadata
  columns on every `ECGTable` output (set to `None` when the user
  did not opt in for that slot); a logger warning is emitted when
  the original sampling frequency disagrees with the assumed 500 Hz
* `ECGDrawing.tile_x_axis(xlims=None)` to tile each column's x-axis
  to an equal 1/n_cols slice of the signal duration, mimicking
  continuous ECG paper; optional per-lead ``xlims`` dict overrides
  the auto-computed window for individual leads
* `cal_leads` parameter on `ECGDrawing.__call__` to restrict the
  calibration pulse to a specified subset of leads
* `show_lead_labels` and `kwargs_label` parameters on
  `ECGDrawing.__call__` for optional per-panel lead name annotations
* `PlotNames` constants class in `constants.py`
  (MILLIVOLT, MICROVOLT, LEAD_VOLTAGES, START_POS_FIRST)
* `LeadMapper` callable in `engineering_tools` for lead-order
  normalisation
* `engineering_tools` example notebook covering
  `metadata_checkversion`, `signal_correction`,
  `signal_standardise_res`, and `LeadMapper`
* `ecgprocess.utils.engineering_tools` documented in the API
  reference; `LeadMapper` referenced in the engineer-callable
  section of the Processing ECG data guide
* Tests for missing required keys and debug logging in
  `test_engineering_tools.py`

#### Changed

* `warnings.warn` calls in `tabular.py` replaced with `logging`
  via a module-level `_log = logging.getLogger(__name__)` logger;
  `warnings` import removed
* `test_warnings` replaced by `test_call_logging` using `caplog`
  to assert against the `ecgprocess.tabular` logger
* `_write_numpy` and `_write_tfr` now call
  `signal_dicts_to_numpy_array` with `padding=False`; writers fail
  loudly when records disagree in length, deferring fixed-length
  layout to the new `signal_length_w` / `signal_length_m` opt-in
* Calibration pulse parameters in `ECGDrawing.__call__` unified
  into a single `cal_pulse` parameter
  (`'square'` | `'line'` | `None`)
* `ECGDrawing` rendering pipeline completed in `plot_ecgs.py`:
  `_render_leads` (traces, ECG paper grid, background, tick
  visibility), `to_numpy`, and module-level `_resolve_lead_kwargs`;
  `ECGStyle.clip_on` split into `clip_on_patch` and `clip_on_trace`;
  sampling frequency parameter renamed to `sampling_rate`
* `ECGStyle` converted from `@dataclass` to `typing.NamedTuple` so
  style instances are immutable and hashable
* `ECGStyle` colour fields renamed to en-GB spelling
  (`background_colour`, `major_grid_colour`, `minor_grid_colour`,
  `trace_colour`); default `trace_linewidth` from 0.5 to 0.4
* `_resolve_lead_kwargs` now distinguishes flat (uniform) kwargs
  from per-lead kwargs so duplicated parameters no longer raise in
  `ECGDrawing`
* `plot_ecgs.py` rewritten: broken `TabularNames` imports replaced
  with `PlotNames`; `ECGDrawing` methods stubbed pending Stages 3-5
  implementation
* `verbose` flag and `print()` calls replaced with `_log.debug()`
  in `signal_correction`, `signal_standardise_res`,
  `metadata_checkversion`, and `LeadMapper`; module-level logger
  replaces per-call `getLogger`
* `LeadMapper.__init__` now raises `InputValidationError` (via
  `is_type`) consistently instead of `TypeError` for invalid value
  types
* `docs/source/index.rst` rewritten as a project landing page with
  the project schematic, scope summary, and installation snippet

#### Removed

* Unused `DICOMTags` dataclass from `constants.py` (orphaned after
  `FixedDICOMReader` removal)
* `docs/source/getting_started.rst`; its README include is
  superseded by the rewritten `index.rst`

### 1.0.1 - 2026-04-16

#### Added

* Tests for `signal_calibration` and `signal_resolution` in `test_ecg_tools.py`
* Tests for `metadata_checkversion` in `test_engineering_tools.py`
* Tests for augment-leads behaviour (`KeyError` on missing source leads; 
 correct derivation of III, aVR, aVL, aVF) in `test_process_xml.py`
* Tests for `get_limb_leads` None-value source lead and 
 `signal_dicts_to_numpy_array` in `test_ecg_tools.py`
* Test for `get_ecg_data` STARTSWITH miss key presence in `test_reader_tools.py`

#### Fixed

* `get_ecg_data`: STARTSWITH miss now always writes `None` to `results_dict` 
before the `skip_empty` guard
* `get_limb_leads`: keys present with `None` values are now treated as absent; 
 error message names the specific missing source leads
* `signal_correction` and `signal_standardise_res`: operate on a local dict 
 copy to prevent caller mutation
* `process_xml`: empty-waveform detection replaced `len(wave_missing)==12` with 
`all(v is None)`; augment-leads guard now checks per derived lead rather than 
any missing lead

#### Changed

* `signal_dicts_to_numpy_array`: `_STANDARD_LEADS` extracted as an immutable 
module-level constant; `leads` parameter now accepts `list` or `tuple`

### 1.0.0 - 2026-04-15

#### Added

* `Makefile` with common dev targets
* Git hooks (`commit-msg`, `pre-commit`) with setup script and codespell 
 ignore-words list
* `resources/build/inc_version.sh` version bump helper script and accompanying 
 README
* Python 3.13 classifier and support in `pyproject.toml`

#### Changed

* `bump2version` config migrated from `.bumpversion.cfg` to `pyproject.toml`; 
now also updates `CHANGELOG.md`
* `pyproject.toml` aligned with scaffold template: dynamic deps via 
 `requirements.txt`/`requirements-dev.txt`, SPDX license string, `[tool.ruff]`
 config, Documentation URL
* Split `requirements.txt` into core runtime deps and new 
 `requirements-dev.txt` for dev/test tooling

#### Removed

* `FixedDICOMReader` legacy DICOM reader class. Use `ECGDICOMReader` instead.
* `FixedReaderNames` constants class (served `FixedDICOMReader` only).

## v1.0.0a0 - 10-12-2024

### Fixed

- Bug fixes to FixedDICOMReader - the older ECGDICOMReader. 
- Document improvements/errors. 

### Added

- A tabular module containing the ECGTable class. This class is a file type 
  agnostic class mapping ECG data to table or files. 
- A reader classes for XML and DICOM files, see the various process_\*.py files. 
- Extensive utils modules. 
- Example configuration files for XML and DICOMs.
- Example XML schema, for XML validation.
- Added TensorFlow as dependency.

### Changed

- process_dicom has been refactored. The previous ECGDICOMReader class has been 
  renamed to FixedDICOMReader which was slightly optimised. 
  The new ECGDICOMReader is now in-line with the process_xml ECGXMLReader class. 
- Changed the base docker environment to allow for tensorflow. 

### Deprecated

- FixedDICOMReader, will be deprecated in future. 

### Removed

- ECGDICOMTable has been removed, please use `ECGTable` instead. 

## v0.2.2 - 20-12-2024

### Fixed

- Fixed ECGDICOMTable bug when the metadata is empty. 
- Bug fix for ECGDICOMReader to handle NoneType ECG measurements.

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

