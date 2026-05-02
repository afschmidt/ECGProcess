# Changelog

### Unreleased

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

