from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pytest

from matplotlib.collections import LineCollection
from ecgprocess.constants import CoreData, PlotNames
from ecgprocess.errors import InputValidationError, NotCalledError
from ecgprocess.plot_ecgs import (
    ECGDrawing,
    ECGStyle,
    _minor_only_ticks,
    _resolve_lead_kwargs,
)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
_LEADS_12 = [
    'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6',
]

_SIMPLE_MAPPER = {'I': (0, slice(0, 1))}
_MINIMAL_MAPPER = {'I': (0, slice(0, 1)), 'II': (0, slice(1, 2))}

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
def minimal_signals():
    """Minimal two-lead signal dict for direct _build_figure calls."""
    rng = np.random.default_rng(0)
    return {'I': rng.standard_normal(500), 'II': rng.standard_normal(500)}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_reader():
    """Synthetic reader: 12 leads, 500 Hz, 2.5 s, no NaN, no MedianBeats."""
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
    """mock_reader with a NaN injected into lead I."""
    mock_reader.WaveForms['I'][0] = np.nan
    return mock_reader

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def prepared_drawing(minimal_signals):
    """ECGDrawing with step slots populated and axes built, ready for
    direct _render_leads calls."""
    style = ECGStyle()
    drawing = ECGDrawing()
    setattr(drawing, 'minor_step_x', 1.0 / style.paper_speed)
    setattr(drawing, 'major_step_x', 5.0 / style.paper_speed)
    setattr(drawing, 'minor_step_y', 1.0 / style.mm_per_mv)
    setattr(drawing, 'major_step_y', 5.0 / style.mm_per_mv)
    fig, axes = drawing._build_figure(minimal_signals, _MINIMAL_MAPPER, style)
    return drawing, fig, axes, minimal_signals, style

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestMinorOnlyTicks:
    """Tests for _minor_only_ticks."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_minor_only_ticks_default(self) -> None:
        """No returned tick falls on a major grid line (ECG defaults)."""
        ticks = _minor_only_ticks(0.0, 1.0, minor_step=0.04, major_step=0.2)
        # check the correct ticks are returned
        assert all(any(np.isclose(ticks, v)) for v in [0.04, 0.08, 0.12, 0.16])
        # confirm no multiples of 0.2 are returned - these are major ticks
        assert not any(np.isclose(t % 0.2, 0.0, atol=1e-9) for t in ticks)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestResolveLeadKwargs:
    """Tests for _resolve_lead_kwargs."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_per_lead_dict_returns_correct_lead(self) -> None:
        """Per-lead mapping returns the sub-dict for the requested lead."""
        kw = {'I': {'color': 'blue'}, 'II': {'color': 'green'}}
        assert _resolve_lead_kwargs(kw, 'I') == {'color': 'blue'}
        assert _resolve_lead_kwargs({'color': 'green'}, 'I') ==\
            {'color': 'green'}


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGStyle:
    """Tests for ECGStyle NamedTuple defaults and calibration."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_axis_limit_defaults(self) -> None:
        """y_lim defaults to ±2 mV; x_lim defaults to None (auto)."""
        s = ECGStyle()
        assert s.y_lim == (-2.0, 2.0)
        assert s.x_lim is None
        assert s.paper_speed == 25.0
        assert s.mm_per_mv == 10.0
        assert s.minor_grid_linewidth == 0.2
        assert s.major_grid_linewidth == 0.3
        assert round(1.0 / s.paper_speed, 4) == 0.04
        assert round(5.0 / s.paper_speed, 4) == 0.20
        assert round(1.0 / s.mm_per_mv, 4) == 0.1
        assert round(5.0 / s.mm_per_mv, 4) == 0.5
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_calibration_field_override(self) -> None:
        """paper_speed and mm_per_mv accept custom values."""
        s = ECGStyle(paper_speed=50.0, mm_per_mv=0.01, y_lim=(-2000, 2000),
                     trace_colour='white', wspace=5.0,)
        assert s.paper_speed == 50.0
        assert s.mm_per_mv == 0.01
        assert s.y_lim == (-2000, 2000)
        assert s.trace_colour == 'white'
        assert s.wspace == 5.0

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingInit:
    """Tests for ECGDrawing.__init__."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_leads(self) -> None:
        """Test the lead parameter."""
        drawing = ECGDrawing()
        expected = [
            CoreData.Leads.I,   CoreData.Leads.II,  CoreData.Leads.III,
            CoreData.Leads.aVR, CoreData.Leads.aVL, CoreData.Leads.aVF,
            CoreData.Leads.V1,  CoreData.Leads.V2,  CoreData.Leads.V3,
            CoreData.Leads.V4,  CoreData.Leads.V5,  CoreData.Leads.V6,
        ]
        assert getattr(drawing, PlotNames.DEFAULT_LEADS) == expected
        # test slots
        for attr in (
            PlotNames.FIGURE, PlotNames.AXES, PlotNames.LAYOUT_MAPPER,
            PlotNames.STYLE,
            PlotNames.MINOR_STEP_X, PlotNames.MAJOR_STEP_X,
            PlotNames.MINOR_STEP_Y, PlotNames.MAJOR_STEP_Y,
            PlotNames.PAPER_SPEED, PlotNames.MM_PER_MV,
        ):
            assert getattr(drawing, attr) is None
        # custom leads
        custom = ['I', 'II']
        assert getattr(
            ECGDrawing(leads=custom), PlotNames.DEFAULT_LEADS) == custom

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingStr:
    """Tests for ECGDrawing.__str__."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_str_format(self) -> None:
        """__str__ returns class name and leads in expected format."""
        drawing = ECGDrawing(leads=['I', 'II'])
        assert str(drawing) == "ECGDrawing instance with leads=['I', 'II']."

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingRepr:
    """Tests for ECGDrawing.__repr__."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_repr_format(self) -> None:
        """__repr__ returns unambiguous constructor-style string."""
        drawing = ECGDrawing(leads=['I', 'II'])
        assert repr(drawing) == "ECGDrawing(leads=['I', 'II'])"

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingBuildFigureDirect:
    """
    Direct calls to ECGDrawing._build_figure: return types and kwarg
    forwarding.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_returns_figure_and_axes_dict(self, minimal_signals) -> None:
        """_build_figure returns a plt.Figure and a dict of plt.Axes."""
        fig, axes = ECGDrawing()._build_figure(
            minimal_signals, _MINIMAL_MAPPER, ECGStyle(),
        )
        assert isinstance(fig, plt.Figure)
        assert isinstance(axes, dict)
        assert set(axes.keys()) == set(_MINIMAL_MAPPER.keys())
        assert all(isinstance(ax, plt.Axes) for ax in axes.values())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_kwargs_fig_overrides_style(self, minimal_signals) -> None:
        """kwargs_fig takes precedence over style when keys overlap."""
        fig, _ = ECGDrawing()._build_figure(
            minimal_signals, _MINIMAL_MAPPER, ECGStyle(),
            kwargs_fig={'dpi': 200, 'figsize': (5.,5.)},
        )
        assert fig.dpi == 200
        assert all(fig.get_size_inches() == [5.,5.])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_kwargs_gridspec_overrides_style(self, minimal_signals) -> None:
        """kwargs_gridspec takes precedence over style when keys overlap."""
        fig, axes = ECGDrawing()._build_figure(
            minimal_signals, _MINIMAL_MAPPER, ECGStyle(),
            kwargs_gridspec={'hspace': 0.9},
        )
        gs = list(axes.values())[0].get_gridspec()
        assert gs.get_subplot_params().hspace == pytest.approx(0.9)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingRenderLeadsDirect:
    """
    Direct calls to ECGDrawing._render_leads: kwarg forwarding, tick
    visibility, and blank-axes skipping.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _render(self, drawing, axes, signals, style, **kw) -> None:
        """Call _render_leads with safe defaults for unused parameters."""
        defaults = dict(
            show_axes=None, show_lead_labels=False,
            show_cal_pulse=False, cal_pulse_style='square',
            kwargs_plot=None, kwargs_grid=None, kwargs_ticks=None,
            kwargs_background=None, kwargs_label=None,
        )
        defaults.update(kw)
        drawing._render_leads(axes, signals, style, 500.0, **defaults)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_kwargs_forwarding(self, prepared_drawing) -> None:
        """kwargs_plot colour and kwargs_background facecolor both override
        the style defaults."""
        drawing, fig, axes, signals, style = prepared_drawing
        self._render(
            drawing, axes, signals, style,
            kwargs_plot={'color': 'red'},
            kwargs_background={'facecolor': 'yellow'},
        )
        assert axes['I'].get_lines()[0].get_color() == 'red'
        assert axes['I'].patch.get_facecolor() == mcolors.to_rgba('yellow')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_show_axes_x_and_y(self, prepared_drawing) -> None:
        # show_axis = x
        drawing, fig, axes, signals, style = prepared_drawing
        self._render(drawing, axes, signals, style, show_axes='x')
        xp = axes['I'].xaxis.get_tick_params(which='major')
        yp = axes['I'].yaxis.get_tick_params(which='major')
        assert xp['bottom'] is True and xp['labelbottom'] is True
        assert yp['left'] is False and yp['labelleft'] is False
        # show_axis = y
        self._render(drawing, axes, signals, style, show_axes='y')
        xp2 = axes['I'].xaxis.get_tick_params(which='major')
        yp2 = axes['I'].yaxis.get_tick_params(which='major')
        assert yp2['left'] is True and yp2['labelleft'] is True
        assert xp2['bottom'] is False and xp2['labelbottom'] is False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_blank_axes_skipped(self, prepared_drawing) -> None:
        """
        Lead absent from signals leaves its axes with no plotted lines.
        """
        drawing, fig, axes, signals, style = prepared_drawing
        self._render(drawing, axes, {'I': signals['I']}, style)
        assert len(axes['II'].get_lines()) == 0

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingSignalInput:
    """Tests for ECGDrawing.__call__ """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nan_in_signal(self, mock_reader_with_nan) -> None:
        """InputValidationError raised when any lead signal contains NaN."""
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader_with_nan, mapper=_SIMPLE_MAPPER)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_source(self, mock_reader) -> None:
        """InputValidationError raised when requested source is None."""
        with pytest.raises(InputValidationError):
            ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, source='median')

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingLayout:
    """Tests for ECGDrawing.__call__ """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_gridspec_layout(self, mock_reader) -> None:
        """Axes keys, nrows, ncols, and colspan all derived from the mapper."""
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
        """Missing mapper key creates blank axes and logs WARNING."""
        mapper = {'I': (0, slice(0, 1)), 'MISSING': (0, slice(1, 2))}
        with caplog.at_level('WARNING', logger='ecgprocess.plot_ecgs'):
            drawing = ECGDrawing()(mock_reader, mapper=mapper)
        assert len(drawing.axes['MISSING'].get_lines()) == 0
        assert 'MISSING' in caplog.text

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingRendering:
    """Tests for ECGDrawing.__call__ trace, limits, grid, and validation."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_trace_and_limits(self, mock_reader) -> None:
        """Trace is plotted; x_lim auto-computes from n_samples/fs; y_lim
        matches style."""
        style = ECGStyle()
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, style=style)
        ax = drawing.axes['I']
        assert len(ax.get_lines()) == 1
        assert ax.get_xlim()[0] == 0.0
        # should be equal to len(signal) / sampling_rate
        assert ax.get_xlim()[1] == 1250 / 500.0
        assert ax.get_ylim() == style.y_lim
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_background_and_grid(self, mock_reader) -> None:
        """Axes patch is visible; four LineCollections drawn for the grid."""
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        ax = drawing.axes['I']
        assert ax.patch.get_visible() is True
        lcs = [c for c in ax.collections if isinstance(c, LineCollection)]
        assert len(lcs) == 4
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_sampling_rate_override_adjusts_xlim(self, mock_reader) -> None:
        """sampling_rate= overrides MetaData value; x_lim upper reflects
        new rate."""
        drawing = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER, sampling_rate=250.0,
        )
        assert drawing.axes['I'].get_xlim()[1] == (1250 / 250.0)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingLeadLabels:
    """Tests for ECGDrawing lead label annotations (show_lead_labels)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_labels_present_when_enabled(self, mock_reader) -> None:
        """Each lead panel has exactly one text annotation with the lead name."""
        drawing = ECGDrawing()(
            mock_reader, mapper=_12LEAD_MAPPER, show_lead_labels=True,
        )
        for lead, ax in drawing.axes.items():
            texts = [t.get_text() for t in ax.texts]
            assert lead in texts
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_kwargs_label_forwarded(self, mock_reader) -> None:
        """Custom kwargs_label override the default text style."""
        drawing = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER,
            show_lead_labels=True,
            kwargs_label={'fontsize': 12, 'color': 'red'},
        )
        txt = drawing.axes['I'].texts[0]
        assert txt.get_fontsize() == 12
        assert txt.get_color() == 'red'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingCalPulse:
    """Tests for ECGDrawing calibration pulse (show_cal_pulse)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_extends_xlim(self, mock_reader) -> None:
        """show_cal_pulse=True extends x upper limit by 0.4 s (200 samples
        at 500 Hz)."""
        without = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        x_hi_without = without.axes['I'].get_xlim()[1]
        with_ = ECGDrawing()(
            mock_reader, mapper=_SIMPLE_MAPPER, show_cal_pulse=True,
        )
        x_hi_with = with_.axes['I'].get_xlim()[1]
        assert x_hi_with == pytest.approx(x_hi_without + 0.4)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cal_pulse_line_extends_xlim(self, mock_reader) -> None:
        """show_cal_pulse=True with style "line" extends x upper limit by
        0.1 + 3/fs + 0.1 s (pre + 3-sample spike + post)."""
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
    def test_cal_pulse_does_not_mutate_signals(self, mock_reader) -> None:
        """Caller WaveForms arrays are unchanged after show_cal_pulse=True."""
        original_len = len(mock_reader.WaveForms['I'])
        original = mock_reader.WaveForms['I'].copy()
        ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER, show_cal_pulse=True)
        assert len(mock_reader.WaveForms['I']) == original_len
        assert all(mock_reader.WaveForms['I'] == original)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestECGDrawingToNumpy:
    """Tests for ECGDrawing.to_numpy."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_not_called_raises(self) -> None:
        """NotCalledError raised when to_numpy is called before __call__."""
        with pytest.raises(NotCalledError):
            ECGDrawing().to_numpy()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_shape_and_dtype(self, mock_reader) -> None:
        """to_numpy returns a (height, width, 4) uint8 RGBA array."""
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        arr = drawing.to_numpy(close=False)
        assert arr.ndim == 3
        assert arr.shape[2] == 4
        assert arr.dtype == np.uint8
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_close_clears_figure(self, mock_reader) -> None:
        """close=True sets figure to None after extraction."""
        drawing = ECGDrawing()(mock_reader, mapper=_SIMPLE_MAPPER)
        drawing.to_numpy(close=True)
        assert drawing.figure is None
