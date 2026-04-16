import pytest
import numpy as np
from ecgprocess.utils import engineering_tools as eng_tools
from ecgprocess.constants import TabularNames as TabNames
from ecgprocess.errors import FileValidationError

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalCorrection(object):
    """Test signal_correction does not mutate the caller's dict."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_signals(self) -> dict:
        """Return a two-lead signals dict with unit arrays."""
        return {
            'I':  np.ones(10, dtype=np.float64),
            'II': np.ones(10, dtype=np.float64) * 2,
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_meta(self, n: int = 2) -> dict:
        """Return a meta_dict with baseline=0 and correctionfactor=1 per lead.
        
        With baseline=0 and correctionfactor=1 the correction is a no-op,
        so we can isolate the mutation side-effect.
        """
        meta = {}
        for i in range(n):
            meta[f'wave_channel_baseline_{i}'] = 0.0
            meta[f'wave_channel_correctionfactor_{i}'] = 1.0
        return meta
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_does_not_mutate_input(self):
        """signal_correction must not modify the caller's signals dict.
        
        Test data: two leads each of length 10. baseline=0,
        correctionfactor=1 so the correction is a no-op — any mutation
        would still be detectable via id() or value comparison.
        """
        signals = self._make_signals()
        original_ids = {k: id(v) for k, v in signals.items()}
        eng_tools.signal_correction(
            signals,
            **{TabNames.META_DICT: self._make_meta()},
        )
        for k, orig_id in original_ids.items():
            assert id(signals[k]) == orig_id, (
                f"signal_correction mutated signals['{k}'] in-place"
            )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalStandardiseRes(object):
    """Test signal_standardise_res does not mutate the caller's dict."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_signals(self) -> dict:
        """Return a two-lead signals dict with unit arrays."""
        return {
            'I':  np.ones(10, dtype=np.float64),
            'II': np.ones(10, dtype=np.float64) * 2,
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_meta(self, n: int = 2, resolution: float = 5.0) -> dict:
        """Return a meta_dict where each lead has the target resolution.
        
        With source == target the scaling factor is 1, so the correction
        is a no-op — any mutation would still be detectable.
        """
        return {f'wave_channel_sens_{i}': resolution for i in range(n)}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_does_not_mutate_input(self):
        """signal_standardise_res must not modify the caller's signals dict.
        
        Test data: two leads each of length 10. source resolution equals
        target (5.0 uV) so the scaling is a no-op — any mutation would
        still be detectable via id() or value comparison.
        """
        signals = self._make_signals()
        original_ids = {k: id(v) for k, v in signals.items()}
        eng_tools.signal_standardise_res(
            signals,
            **{TabNames.META_DICT: self._make_meta()},
        )
        for k, orig_id in original_ids.items():
            assert id(signals[k]) == orig_id, (
                f"signal_standardise_res mutated signals['{k}'] in-place"
            )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestMetadataCheckversion(object):
    """Test metadata_checkversion"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_meta(self) -> dict:
        """Return a metadata dict matching the function defaults."""
        return {
            'Softwave version': '1.02 SP03',
            'Manufacturer': 'GE Healthcare',
            'Model name': 'MV360',
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_valid_metadata_returns_dict(self):
        """Valid metadata is returned unchanged.

        Test data: metadata matches all three default expected values.
        The return value must be the same dict object (identity check).
        """
        meta = self._make_meta()
        result = eng_tools.metadata_checkversion(meta)
        assert result is meta
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_invalid_version_raises(self):
        """FileValidationError raised when the version does not match.

        Test data: version set to an unrecognised string; manufacturer and
        model are valid defaults.
        """
        meta = self._make_meta()
        meta['Softwave version'] = 'unknown_version'
        with pytest.raises(FileValidationError):
            eng_tools.metadata_checkversion(meta)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_invalid_manufacturer_raises(self):
        """FileValidationError raised when the manufacturer does not match.

        Test data: manufacturer set to an unrecognised string; version and
        model are valid defaults.
        """
        meta = self._make_meta()
        meta['Manufacturer'] = 'unknown_manufacturer'
        with pytest.raises(FileValidationError):
            eng_tools.metadata_checkversion(meta)
