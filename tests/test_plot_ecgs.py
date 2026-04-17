from __future__ import annotations

import pytest
from ecgprocess.plot_ecgs import ECGStyle

# Tests added incrementally across Stages 2-6:
# Stage 3: reader wiring and signal validation
# Stage 4: GridSpec layout and mapper registry
# Stage 5: signal rendering and axis formatting
# Stage 6: full suite, edge cases, and cleanup


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Stage 2 — ECGStyle defaults and calibration maths


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestECGStyle:
    '''Tests for ECGStyle dataclass defaults.'''
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
