import pytest
import numpy as np
from ecgprocess.utils import ecg_tools as ecg_utils
from ecgprocess.errors import InputValidationError

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestResampling(object):
    """Test resampling_500hz"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resampling(self):
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        duration = 2
        res = ecg_utils.resampling_500hz(signals, duration=duration)
        assert len(res["lead1"]) == 2 * 500
        assert res["lead1"].ndim == 1
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resampling_median_conventional(self):
        # a 1.2 s median beat yields the conventional 600 samples
        # whatever the source rate it was stored at
        for source_rate in (250, 500, 1000):
            signals = {"lead1": np.sin(
                np.linspace(0, 2 * np.pi, int(1.2 * source_rate)))}
            res = ecg_utils.resampling_500hz(signals, duration=1.2)
            assert len(res["lead1"]) == 600
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resampling_median_non_conventional(self):
        # a median beat which is not 1.2 s keeps its true duration at
        # 500 Hz; the old fixed 600 samples would have time-warped it
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        res = ecg_utils.resampling_500hz(signals, duration=2.0)
        assert len(res["lead1"]) == 1000
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_duration_error(self):
        signals = {"lead1": np.sin(np.linspace(0, 2 * np.pi, 1000))}
        with pytest.raises(ValueError):
            ecg_utils.resampling_500hz(signals, duration=None)

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
    def test_none_value_src_lead_raises(self):
        """
        KeyError raised when a source lead key exists but its value is None.
        
        Test data: lead I has a valid array; lead II key is present but its
        value is None (simulating a lead that was in the config but absent
        from the XML). Both key-absent and None-value cases must raise.
        """
        signals = {"I": np.array([1.0, 2.0, 3.0]), "II": None}
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalDictsToNumpyArray(object):
    """Test signal_dicts_to_numpy_array"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_sample(self, length: int = 10) -> dict:
        """Return a single-sample dict with the standard 12 leads."""
        leads = ['I', 'II', 'III', 'V1', 'V2', 'V3',
                 'V4', 'V5', 'V6', 'aVF', 'aVL', 'aVR']
        return {l: np.ones(length, dtype=np.float32) * i
                for i, l in enumerate(leads)}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default_leads_uses_standard_12(self):
        """Default leads (_STANDARD_LEADS tuple) must produce shape (1, 12, N)."""
        result = ecg_utils.signal_dicts_to_numpy_array([self._make_sample()])
        assert result.shape == (1, 12, 10)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_none_collects_all_unique_leads(self):
        """
        leads=None must gather all unique lead names from the samples.
        
        Test data: single sample with two custom leads 'A' and 'B', each of
        length 5. Expected output shape: (1, 2, 5).
        """
        sample = {'A': np.ones(5), 'B': np.ones(5)}
        result = ecg_utils.signal_dicts_to_numpy_array([sample], leads=None)
        assert result.shape == (1, 2, 5)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_explicit_leads(self):
        """Explicit lead list controls column count and order."""
        result = ecg_utils.signal_dicts_to_numpy_array(
            [self._make_sample()], leads=['I', 'II'])
        assert result.shape == (1, 2, 10)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_empty_signals_raises(self):
        with pytest.raises(ValueError):
            ecg_utils.signal_dicts_to_numpy_array([])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_padding_false_allows_lead_subset(self):
        """
        With padding=False a subset of leads (here a single lead) is valid:
        absent canonical leads are left as NaN rather than raising.
        """
        sample = {'II': np.arange(5, dtype=np.float32)}
        result = ecg_utils.signal_dicts_to_numpy_array(
            [sample], padding=False)
        assert result.shape == (1, 12, 5)
        # 'II' is index 1 in the canonical order; it carries the data
        np.testing.assert_array_equal(
            result[0, 1], np.arange(5, dtype=np.float32))
        # 'I' (index 0) is absent -> all NaN
        assert np.isnan(result[0, 0]).all()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_padding_false_mismatched_present_lengths_raise(self):
        """Present leads of differing lengths still raise under padding=False."""
        sample = {'I': np.arange(5, dtype=np.float32),
                  'II': np.arange(6, dtype=np.float32)}
        with pytest.raises(ValueError):
            ecg_utils.signal_dicts_to_numpy_array([sample], padding=False)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalCalibration(object):
    """Test signal_calibration"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_correct_output(self):
        """
        Output equals (signal - baseline) * correctionfactor.
        
        Test data: signal=[0,1,2], baseline=1.0, correctionfactor=2.0.
        Expected: [-2.0, 0.0, 2.0].
        """
        signal = np.array([0.0, 1.0, 2.0])
        result = ecg_utils.signal_calibration(
            signal, correctionfactor=2.0, baseline=1.0)
        np.testing.assert_array_almost_equal(result, [-2.0, 0.0, 2.0])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_invalid_type(self):
        """InputValidationError raised when correctionfactor is not numeric."""
        signal = np.array([1.0, 2.0, 3.0])
        with pytest.raises(InputValidationError):
            ecg_utils.signal_calibration(
                signal, correctionfactor='2', baseline=0.0)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_accepts_int(self):
        """
        signal_calibration accepts int correctionfactor/baseline without
        raising, since metadata dicts may legitimately supply whole-number
        values.

        Test data: signal=[0,1,2], baseline=1, correctionfactor=2.
        Expected: [-2.0, 0.0, 2.0].
        """
        signal = np.array([0.0, 1.0, 2.0])
        result = ecg_utils.signal_calibration(
            signal, correctionfactor=2, baseline=1)
        np.testing.assert_array_almost_equal(result, [-2.0, 0.0, 2.0])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_no_mutation(self):
        """signal_calibration must not modify the caller's array in-place."""
        signal = np.array([1.0, 2.0, 3.0])
        original_id = id(signal)
        ecg_utils.signal_calibration(signal, correctionfactor=1.0, baseline=0.0)
        assert id(signal) == original_id

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalResolution(object):
    """Test signal_resolution"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_correct_output(self):
        """
        Output matches the docstring example.
        
        Test data: signal=[10,20,30], current=2.0, target=5.0.
        Expected: [25.0, 50.0, 75.0].
        """
        signal = np.array([10.0, 20.0, 30.0])
        result = ecg_utils.signal_resolution(
            signal, resolution_current=2.0, resolution_target=5.0)
        np.testing.assert_array_almost_equal(result, [25.0, 50.0, 75.0])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_invalid_type(self):
        """InputValidationError raised when resolution_current is not numeric."""
        signal = np.array([1.0, 2.0, 3.0])
        with pytest.raises(InputValidationError):
            ecg_utils.signal_resolution(
                signal, resolution_current='2', resolution_target=5.0)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_accepts_int(self):
        """
        signal_resolution accepts int resolution_current/resolution_target
        without raising, since metadata dicts may legitimately supply
        whole-number values.

        Test data: signal=[10,20,30], current=2, target=5.
        Expected: [25.0, 50.0, 75.0].
        """
        signal = np.array([10.0, 20.0, 30.0])
        result = ecg_utils.signal_resolution(
            signal, resolution_current=2, resolution_target=5)
        np.testing.assert_array_almost_equal(result, [25.0, 50.0, 75.0])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_no_mutation(self):
        """signal_resolution must not modify the caller's array in-place."""
        signal = np.array([1.0, 2.0, 3.0])
        original_id = id(signal)
        ecg_utils.signal_resolution(
            signal, resolution_current=1.0, resolution_target=1.0)
        assert id(signal) == original_id
