import os
import pytest
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.writer import (
    NumpyWriter,
    NpzWriter,
    NpyWriter,
    WRITERS,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNumpyWriterBase(object):
    """Testing the abstract numpy-family base class contract."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_base_is_abstract_and_unregistered(self):
        # the base cannot be instantiated (abstract _save); only its
        # concrete subclasses are registered under a file_type key
        with pytest.raises(TypeError):
            NumpyWriter()
        assert NumpyWriter not in WRITERS.values()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNpzWriter(object):
    """Round-trip and flag-gating tests for the uncompressed .npz writer."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered_under_npz_only(self):
        # 'npz' is the canonical registry key; the legacy 'numpy' alias
        # lives in the deprecated file_type path, not the registry
        assert WRITERS[TabNames.WRITE_NPZ] is NpzWriter
        assert TabNames.WRITE_NUMPY not in WRITERS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path, make_context):
        # a SUBSET of leads (I, II) at equal length 5; absent leads become
        # NaN. This also exercises the subset support in
        # signal_dicts_to_numpy_array.
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50, 'note': 'x'}, {'age': 60, 'note': 'y'}]
        ctx = make_context(tmp_path, e_median=False)
        NpzWriter().write(meta, wave, [], ctx)
        assert 'ecg_data.npz' in os.listdir(tmp_path)
        assert 'header_metadata.txt' in os.listdir(tmp_path)
        data = np.load(tmp_path / 'ecg_data.npz')
        try:
            # canonical layout is (n_records, 12 leads, signal_length)
            waves = data[CTypes.WaveForms]
            assert waves.shape == (2, 12, 5)
            # present leads carry data; absent leads are NaN
            assert not np.isnan(waves[0, 0]).any()
            assert np.isnan(waves[0, 2]).all()
            # 'note' dropped -> single numeric column
            assert data[CTypes.MetaData].shape == (2, 1)
            assert CTypes.MedianBeats not in data.files
        finally:
            data.close()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flag_gating_single_lead_only(self, tmp_path, make_context):
        # a single present lead is valid; the rest are NaN
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        NpzWriter().write([], wave, [], ctx)
        data = np.load(tmp_path / 'ecg_data.npz')
        try:
            assert data.files == [CTypes.WaveForms]
            assert data[CTypes.WaveForms].shape == (2, 12, 5)
        finally:
            data.close()
        # no metadata -> no header sidecar
        assert 'header_metadata.txt' not in os.listdir(tmp_path)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNpyWriter(object):
    """
    Round-trip and flag-gating tests for the per-array `.npy` writer: one
    `.npy` file per enabled source per chunk, memory-mappable, float32
    signals, plus the metadata header sidecar.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered(self):
        assert TabNames.WRITE_NPY in WRITERS
        # NOTE will remove on refactor - deprecated.
        assert WRITERS[TabNames.WRITE_NPY] is NpyWriter
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path, make_context):
        # a SUBSET of leads (I, II) at equal length 5; absent leads are NaN
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        median = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50, 'note': 'x'}, {'age': 60, 'note': 'y'}]
        ctx = make_context(tmp_path)
        NpyWriter().write(meta, wave, median, ctx)
        # #### one file per source plus the metadata header sidecar
        assert set(os.listdir(tmp_path)) == {
            'metadata.npy', 'waveforms.npy', 'medianbeats.npy',
            'header_metadata.txt'}
        # #### signals: canonical layout, float32, memory-mappable
        waves = np.load(tmp_path / 'waveforms.npy', mmap_mode='r')
        assert waves.shape == (2, 12, 5)
        assert waves.dtype == np.float32
        np.testing.assert_allclose(waves[0, 0], np.arange(5.0))
        np.testing.assert_allclose(waves[1, 1], np.arange(5.0) + 3)
        # present leads carry data; absent leads are NaN
        assert np.isnan(waves[0, 2]).all()
        medians = np.load(tmp_path / 'medianbeats.npy', mmap_mode='r')
        assert medians.shape == (2, 12, 3)
        assert medians.dtype == np.float32
        # #### metadata: 'note' dropped -> single numeric column
        metadata = np.load(tmp_path / 'metadata.npy', mmap_mode='r')
        assert metadata.shape == (2, 1)
        np.testing.assert_allclose(metadata[:, 0], [50, 60])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_chunk_suffix(self, tmp_path, make_context):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = make_context(tmp_path, e_meta=False, e_median=False,
                            chunk_num=2)
        NpyWriter().write([], wave, [], ctx)
        assert os.listdir(tmp_path) == ['waveforms_2.npy']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flag_gating(self, tmp_path, make_context):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        NpyWriter().write([], wave, [], ctx)
        # only the enabled source is written; no metadata -> no sidecar
        assert os.listdir(tmp_path) == ['waveforms.npy']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_custom_dtype(self, tmp_path, make_context):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        NpyWriter(dtype=np.float64).write([], wave, [], ctx)
        assert np.load(tmp_path / 'waveforms.npy').dtype == np.float64
