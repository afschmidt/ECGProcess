import logging
import pytest
import numpy as np
from ecgprocess.utils import engineering_tools as eng_tools
from ecgprocess.constants import TabularNames as TabNames
from ecgprocess.errors import FileValidationError, InputValidationError

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
class TestLeadMapper(object):
    """Test LeadMapper callable for lead-order normalisation."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_signals(self) -> dict:
        """Return a three-lead signals dict with distinct arrays."""
        return {
            'I':   np.array([1.0], dtype=np.float64),
            'II':  np.array([2.0], dtype=np.float64),
            'III': np.array([3.0], dtype=np.float64),
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_meta(self, order: list[str] | None = None) -> dict:
        """Return a meta_dict with 'signal name N' keys.

        Defaults to ['Lead II', 'Lead I', 'Lead III'] — non-standard device
        ordering that the mapper must correct.
        """
        if order is None:
            order = ['Lead II', 'Lead I', 'Lead III']
        return {f'signal name {i}': label for i, label in enumerate(order)}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _make_accepted_mappings(self) -> dict:
        """Return accepted_mappings for three leads."""
        return {
            'I':   ['I', 'Lead I', 'Lead I (Einthoven)'],
            'II':  ['II', 'Lead II'],
            'III': ['III', 'Lead III'],
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_happy_path_reorders_signals(self):
        """LeadMapper reassigns arrays to canonical keys.

        Device order [Lead II, Lead I, Lead III] means:
        canonical 'I' <- channel 1 (2.0), 'II' <- channel 0 (1.0).
        """
        signals = self._make_signals()
        mapper = eng_tools.LeadMapper(self._make_accepted_mappings())
        result = mapper(signals, **{TabNames.META_DICT: self._make_meta()})
        np.testing.assert_array_equal(result['I'],   np.array([2.0]))
        np.testing.assert_array_equal(result['II'],  np.array([1.0]))
        np.testing.assert_array_equal(result['III'], np.array([3.0]))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_does_not_mutate_input(self):
        """Input signals dict must be unchanged after the call."""
        signals = self._make_signals()
        original_ids = {k: id(v) for k, v in signals.items()}
        mapper = eng_tools.LeadMapper(self._make_accepted_mappings())
        mapper(signals, **{TabNames.META_DICT: self._make_meta()})
        for k, orig_id in original_ids.items():
            assert id(signals[k]) == orig_id
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_meta_dict_raises_key_error(self):
        """KeyError raised when meta_dict kwarg is absent."""
        mapper = eng_tools.LeadMapper(self._make_accepted_mappings())
        with pytest.raises(KeyError):
            mapper(self._make_signals())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_unmapped_lead_raises_key_error(self):
        """KeyError raised when a required lead has no match in meta_dict."""
        bad_meta = {'signal name 0': 'Lead X', 'signal name 1': 'Lead Y',
                    'signal name 2': 'Lead Z'}
        mapper = eng_tools.LeadMapper(self._make_accepted_mappings())
        with pytest.raises(KeyError):
            mapper(self._make_signals(), **{TabNames.META_DICT: bad_meta})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_init_invalid_accepted_mappings_raises_input_validation_error(self):
        """InputValidationError raised when accepted_mappings is not a dict of lists."""
        with pytest.raises(InputValidationError):
            eng_tools.LeadMapper(['I', 'II'])
        with pytest.raises(InputValidationError):
            eng_tools.LeadMapper({'I': 'Lead I'})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_debug_logging_emitted(self, caplog):
        """LeadMapper emits DEBUG records for mappings and each lead.
        
        Test data: three-lead non-standard order. With the logger set to DEBUG
        we expect the 'Accepted lead mappings', 'Actual lead mappings', and
        per-lead mapping records to appear.
        """
        mapper = eng_tools.LeadMapper(self._make_accepted_mappings())
        with caplog.at_level(
            logging.DEBUG,
            logger='ecgprocess.utils.engineering_tools',
        ):
            mapper(self._make_signals(), **{TabNames.META_DICT: self._make_meta()})
        messages = [r.message for r in caplog.records]
        assert any('Accepted lead mappings' in m for m in messages)
        assert any('Actual lead mappings' in m for m in messages)
        assert any("Mapping 'I'" in m for m in messages)

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
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_required_key_raises_key_error(self):
        """KeyError raised when any required metadata key is absent.
        
        Test data: each required key ('Softwave version', 'Manufacturer',
        'Model name') is removed in turn from an otherwise valid dict.
        """
        for key in ('Softwave version', 'Manufacturer', 'Model name'):
            meta = self._make_meta()
            del meta[key]
            with pytest.raises(KeyError):
                eng_tools.metadata_checkversion(meta)

