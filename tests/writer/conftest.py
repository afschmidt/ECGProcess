"""
Shared pytest fixtures for the tests/writer/ suite.
"""
import numpy as np
import pytest
from ecgprocess.constants import CoreData as Core
from ecgprocess.plot_ecgs import ECGStyle
from ecgprocess.writer import WriteContext

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CMeta = Core.MetaData

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# fixtures

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def make_context():
    """Factory building a WriteContext for two records keyed 'a' and 'b'."""
    def _make(target, e_meta=True, e_wave=True, e_median=True,
              chunk_num=None, skip_data=False):
        return WriteContext(
            e_meta=e_meta,
            e_wave=e_wave,
            e_median=e_median,
            key_list=['a', 'b'],
            target=str(target),
            chunk_num=chunk_num,
            skip_data=skip_data,
        )
    return _make

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def make_figure_records():
    """Factory building signal dicts for given leads plus SF metadata."""
    def _make(leads, n=2, length=100):
        rng = np.random.default_rng(7)
        sig_list = [
            {lead: rng.standard_normal(length) for lead in leads}
            for _ in range(n)
        ]
        meta_list = [{CMeta.SF: 100.0} for _ in range(n)]
        return meta_list, sig_list
    return _make

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def leads_12():
    """The 12 standard leads in clinical column order."""
    return [
        'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
        'V1', 'V2', 'V3', 'V4', 'V5', 'V6',
    ]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def small_style():
    """A small render style keeping the figure tests fast."""
    return ECGStyle(figsize=(4., 2.), dpi=40)
