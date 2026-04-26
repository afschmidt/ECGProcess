from __future__ import annotations

import numpy as np
import pytest
from matplotlib.collections import LineCollection
from ecgprocess.constants import CoreData
from ecgprocess.errors import InputValidationError, NotCalledError
from ecgprocess.plot_ecgs import ECGDrawing, ECGStyle

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
    reader.MetaData = {CoreData.MetaData.SF: 500.0}
    return reader


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_reader_with_nan(mock_reader):
    '''mock_reader with a NaN injected into lead I.'''
    mock_reader.WaveForms['I'][0] = np.nan
    return mock_reader


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGStyle:
    '''Tests for ECGStyle NamedTuple defaults and calibration.'''
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
    def test_clip_on_defaults_false(self) -> None:
        '''clip_on_patch and clip_on_trace both default to False.'''
        s = ECGStyle()
        assert s.clip_on_patch is False
        assert s.clip_on_trace is False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_grid_linewidth_defaults(self) -> None:
        '''minor_grid_linewidth defaults to 0.2 pt; major to 0.3 pt.'''
        s = ECGStyle()
        assert s.minor_grid_linewidth == 0.2
        assert s.major_grid_linewidth == 0.3
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
class TestECGDrawingSignalExtraction:
    '''Tests for ECGDrawing.__call__ source selection and signal validation.'''
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
class TestECGDrawingBuildFigure:
    '''Tests for ECGDrawing._build_figure: mapper, GridSpec, and lead warnings.'''
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


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingRenderLeads:
    '''Tests for ECGDrawing._render_leads: traces, limits, grid, and validation.'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_trace_and_limits(self, mock_reader) -> None:
        '''Trace is plotted; x_lim auto-computes from n_samples/fs; y_lim
        matches style.'''
        style = ECGStyle()
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, style=style)
        ax = drawing.axes['I']
        assert len(ax.get_lines()) >= 1
        assert ax.get_xlim()[0] == pytest.approx(0.0)
        assert ax.get_xlim()[1] == pytest.approx(1250 / 500.0)
        assert ax.get_ylim() == pytest.approx(style.y_lim)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_background_and_grid(self, mock_reader) -> None:
        '''Axes patch is visible; four LineCollections drawn for the grid.'''
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        ax = drawing.axes['I']
        assert ax.patch.get_visible() is True
        lcs = [c for c in ax.collections if isinstance(c, LineCollection)]
        assert len(lcs) == 4
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_sampling_rate_override_adjusts_xlim(self, mock_reader) -> None:
        '''sampling_rate= overrides MetaData value; x_lim upper reflects
        new rate.'''
        drawing = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER, sampling_rate=250.0,
        )
        assert drawing.axes['I'].get_xlim()[1] == pytest.approx(1250 / 250.0)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validation_errors(self, mock_reader) -> None:
        '''Invalid show_axes, mixed kwargs, and absent fs all raise
        InputValidationError.'''
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, show_axes='z')
        with pytest.raises(InputValidationError):
            ECGDrawing()(
                mock_reader, mapper=_SIMPLE_MAPPER,
                kwargs_plot={'I': {'lw': 1}, 'II': 0.5},
            )
        class _NoFs:
            WaveForms = {'I': np.zeros(10)}
            MedianBeats = None
            MetaData = {}
        with pytest.raises(InputValidationError):
            ECGDrawing()(_NoFs(), mapper={'I': (0, slice(0, 1))})


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingCalPulse:
    '''Tests for ECGDrawing calibration pulse (show_cal_pulse).'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_extends_xlim(self, mock_reader) -> None:
        '''show_cal_pulse=True extends x upper limit by 0.4 s (200 samples
        at 500 Hz).'''
        without = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        x_hi_without = without.axes['I'].get_xlim()[1]
        with_ = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER, show_cal_pulse=True,
        )
        x_hi_with = with_.axes['I'].get_xlim()[1]
        assert x_hi_with == pytest.approx(x_hi_without + 0.4)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_line_extends_xlim(self, mock_reader) -> None:
        '''show_cal_pulse=True with style "line" extends x upper limit by
        0.1 + 3/fs + 0.1 s (pre + 3-sample spike + post).'''
        without = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        x_hi_without = without.axes['I'].get_xlim()[1]
        with_ = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER,
            show_cal_pulse=True, cal_pulse_style='line',
        )
        x_hi_with = with_.axes['I'].get_xlim()[1]
        expected_extra = 0.1 + 3 / 500.0 + 0.1
        assert x_hi_with == pytest.approx(x_hi_without + expected_extra)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_invalid_style_raises(self, mock_reader) -> None:
        '''InputValidationError raised for an unknown cal_pulse_style.'''
        with pytest.raises(InputValidationError):
            ECGDrawing()(
                mock_reader, mapper=_SIMPLE_MAPPER,
                show_cal_pulse=True, cal_pulse_style='triangle',
            )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_does_not_mutate_signals(self, mock_reader) -> None:
        '''Caller WaveForms arrays are unchanged after show_cal_pulse=True.'''
        original_len = len(mock_reader.WaveForms['I'])
        ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, show_cal_pulse=True)
        assert len(mock_reader.WaveForms['I']) == original_len


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingLeadLabels:
    '''Tests for ECGDrawing lead label annotations (show_lead_labels).'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_labels_present_when_enabled(self, mock_reader) -> None:
        '''Each lead panel has exactly one text annotation with the lead name.'''
        drawing = ECGDrawing()(
            mock_reader, mapper=_12LEAD_MAPPER, show_lead_labels=True,
        )
        for lead, ax in drawing.axes.items():
            texts = [t.get_text() for t in ax.texts]
            assert lead in texts
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_kwargs_label_forwarded(self, mock_reader) -> None:
        '''Custom kwargs_label override the default text style.'''
        drawing = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER,
            show_lead_labels=True,
            kwargs_label={'fontsize': 12, 'color': 'red'},
        )
        txt = drawing.axes['I'].texts[0]
        assert txt.get_fontsize() == 12
        assert txt.get_color() == 'red'


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingToNumpy:
    '''Tests for ECGDrawing.to_numpy.'''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_not_called_raises(self) -> None:
        '''NotCalledError raised when to_numpy is called before __call__.'''
        with pytest.raises(NotCalledError):
            ECGDrawing().to_numpy()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_shape_and_dtype(self, mock_reader) -> None:
        '''to_numpy returns a (height, width, 4) uint8 RGBA array.'''
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        arr = drawing.to_numpy(close=False)
        assert arr.ndim == 3
        assert arr.shape[2] == 4
        assert arr.dtype == np.uint8
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_close_clears_figure(self, mock_reader) -> None:
        '''close=True sets figure to None after extraction.'''
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        drawing.to_numpy(close=True)
        assert drawing.figure is None
