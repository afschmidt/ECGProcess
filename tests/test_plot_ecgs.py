from __future__ import annotations

import numpy as np
import pytest
from ecgprocess.errors import InputValidationError
from ecgprocess.plot_ecgs import ECGDrawing, ECGStyle

# Tests added incrementally across Stages 2-6:
# Stage 3: reader wiring and signal validation
# Stage 4: GridSpec layout and mapper registry
# Stage 5: signal rendering and axis formatting
# Stage 6: full suite, edge cases, and cleanup

_LEADS_12 = [
    'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6',
]

_SIMPLE_MAPPER = {'I': (0, slice(0, 1))}

_12LEAD_MAPPER = {
    'I':   (0, slice(0, 1)), 'II':  (0, slice(1, 2)),
    'III': (0, slice(2, 3)), 'aVR': (0, slice(3, 4)),
    'aVL': (1, slice(0, 1)), 'aVF': (1, slice(1, 2)),
    'V1':  (1, slice(2, 3)), 'V2':  (1, slice(3, 4)),
    'V3':  (2, slice(0, 1)), 'V4':  (2, slice(1, 2)),
    'V5':  (2, slice(2, 3)), 'V6':  (2, slice(3, 4)),
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_reader():
    '''Synthetic reader: 12 leads, 500 Hz, 2.5 s, no NaN, no MedianBeats.'''
    class MockReader:
        pass
    rng = np.random.default_rng(42)
    reader = MockReader()
    reader.WaveForms = {
        lead: rng.standard_normal(1250) for lead in _LEADS_12
    }
    reader.MedianBeats = None
    return reader


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_reader_with_nan(mock_reader):
    '''mock_reader with a NaN injected into lead I.'''
    mock_reader.WaveForms['I'][0] = np.nan
    return mock_reader


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Stage 2 — ECGStyle defaults and calibration maths


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestECGStyle:
    '''Tests for ECGStyle NamedTuple defaults.'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_axis_limit_defaults(self) -> None:
        '''y_lim defaults to ±2 mV; x_lim defaults to None (auto).'''
        s = ECGStyle()
        assert s.y_lim == (-2.0, 2.0)
        assert s.x_lim is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_calibration_field_defaults(self) -> None:
        '''paper_speed defaults to 25.0 mm/s; mm_per_mv defaults to 10.0 mm/mV.'''
        s = ECGStyle()
        assert s.paper_speed == 25.0
        assert s.mm_per_mv == 10.0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_calibration_field_override(self) -> None:
        '''paper_speed and mm_per_mv accept custom values.'''
        s = ECGStyle(paper_speed=50.0, mm_per_mv=5.0)
        assert s.paper_speed == 50.0
        assert s.mm_per_mv == 5.0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_clip_on_default_false(self) -> None:
        '''clip_on defaults to False, enabling cross-panel trace rendering.'''
        assert ECGStyle().clip_on is False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_grid_step_maths_at_defaults(self) -> None:
        '''Standard calibration yields 0.04 s minor / 0.20 s major on x;
        0.1 mV minor / 0.5 mV major on y.'''
        s = ECGStyle()
        assert round(1.0 / s.paper_speed, 4) == 0.04
        assert round(5.0 / s.paper_speed, 4) == 0.20
        assert round(1.0 / s.mm_per_mv, 4) == 0.1
        assert round(5.0 / s.mm_per_mv, 4) == 0.5


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Stage 3 — ECGDrawing skeleton and reader wiring


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingStage3:
    '''Tests for ECGDrawing signal extraction and validation (Stage 3).'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_waveforms_source_returns_self(self, mock_reader) -> None:
        '''__call__ returns self when waveforms source is valid.'''
        d = ECGDrawing()
        assert d(mock_reader, mapper=_SIMPLE_MAPPER, source='waveforms') is d
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nan_in_signal_raises(self, mock_reader_with_nan) -> None:
        '''InputValidationError raised when any lead signal contains NaN.'''
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader_with_nan, mapper=_SIMPLE_MAPPER)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_empty_source_raises(self, mock_reader) -> None:
        '''InputValidationError raised when requested source is None.'''
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, source='median')


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Stage 4 — Layout system: GridSpec + mapper


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingStage4:
    '''Tests for ECGDrawing GridSpec layout and mapper handling (Stage 4).'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_mapper_none_raises(self, mock_reader) -> None:
        '''InputValidationError raised when mapper=None.'''
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader, mapper=None)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_gridspec_layout(self, mock_reader) -> None:
        '''Axes keys, nrows, ncols, and colspan all derived from the mapper.'''
        mapper = dict(_12LEAD_MAPPER)
        mapper['rhythm'] = (3, slice(0, 4))
        mock_reader.WaveForms['rhythm'] = mock_reader.WaveForms['II'].copy()
        drawing = ECGDrawing()(mock_reader, mapper=mapper)
        gs = drawing.axes['I'].get_gridspec()
        spec = drawing.axes['rhythm'].get_subplotspec()
        assert set(drawing.axes.keys()) == set(mapper.keys())
        assert gs.nrows == 4
        assert gs.ncols == 4
        assert spec.colspan.start == 0 and spec.colspan.stop == 4
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_lead_blank_and_warns(self, mock_reader, caplog) -> None:
        '''Missing mapper key creates blank axes and logs WARNING.'''
        mapper = {'I': (0, slice(0, 1)), 'MISSING': (0, slice(1, 2))}
        with caplog.at_level('WARNING', logger='ecgprocess.plot_ecgs'):
            drawing = ECGDrawing()(mock_reader, mapper=mapper)
        assert 'MISSING' in drawing.axes
        assert len(drawing.axes['MISSING'].get_lines()) == 0
        assert 'MISSING' in caplog.text
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_unrequested_lead_warns(self, mock_reader, caplog) -> None:
        '''Signal data keys absent from mapper log a WARNING.'''
        with caplog.at_level('WARNING', logger='ecgprocess.plot_ecgs'):
            ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        assert any(lead in caplog.text for lead in ['II', 'III', 'aVR'])
