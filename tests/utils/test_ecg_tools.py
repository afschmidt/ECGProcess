import pytest
import numpy as np
from ecgprocess.utils import ecg_tools as ecg_utils

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestResampling(object):
    """Test resampling_500hz"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resampling(self):
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        duration = 2
        res = ecg_utils.resampling_500hz(signals, duration=duration,
                                         median=False)
        assert len(res["lead1"]) == 2 * 500
        assert res["lead1"].ndim == 1
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resampling_median(self):
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        res = ecg_utils.resampling_500hz(signals, median=True)
        assert len(res["lead1"]) == 600
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_duration_error(self):
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        with pytest.raises(ValueError):
            ecg_utils.resampling_500hz(signals, duration=None, median=False)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestLimbLeads(object):
    """Test get_limb_leads"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_correct(self):
        signals = {
            "I": np.array([1.0, 2.0, 3.0]),
            "II": np.array([4.0, 5.0, 6.0]),
        }
        expected_III = np.array([3.0, 3.0, 3.0])
        expected_aVR = np.array([-2.5, -3.5, -4.5])
        expected_aVL = np.array([-1.0, -0.5, 0.0])
        expected_aVF = np.array([3.5, 4.0, 4.5])
        # run function
        result = ecg_utils.get_limb_leads(signals)
        np.testing.assert_array_almost_equal(result["III"], expected_III)
        np.testing.assert_array_almost_equal(result["aVR"], expected_aVR)
        np.testing.assert_array_almost_equal(result["aVL"], expected_aVL)
        np.testing.assert_array_almost_equal(result["aVF"], expected_aVF)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_leads_error(self):
        signals = {"I": np.array([1.0, 2.0, 3.0])}  # Missing lead II
        with pytest.raises(KeyError):
            ecg_utils.get_limb_leads(signals)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_existing_limb_leads(self):
        signals = {
            "I": np.array([1.0, 2.0, 3.0]),
            "II": np.array([4.0, 5.0, 6.0]),
            "III": np.array([3.0, 3.0, 3.0]),
        }
        result = ecg_utils.get_limb_leads(signals)
        assert np.array_equal(result["III"], np.array([3.0, 3.0, 3.0]))
        np.testing.assert_array_almost_equal(result["aVR"],
                                             np.array([-2.5, -3.5, -4.5]))
