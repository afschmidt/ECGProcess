import os
import sys
import subprocess
import pytest
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
)
from ecgprocess.writer import (
    TFRecordWriter,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.mark.tensorflow
class TestTFRecordWriter(object):
    """
    Content-level round-trip test for the tfrecord writer: the record is
    parsed back and the feature values are compared against the input.
    Skipped when tensorflow is not installed (see conftest.py).
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path, make_context):
        import tensorflow as tf
        # a SUBSET of leads (I, II) at equal length 5; absent leads are NaN
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50.0, 'note': 'x'}, {'age': 60.0, 'note': 'y'}]
        ctx = make_context(tmp_path, e_median=False)
        TFRecordWriter().write(meta, wave, [], ctx)
        assert 'ecg_data.tfrecord' in os.listdir(tmp_path)
        assert 'header_metadata.txt' in os.listdir(tmp_path)
        # #### parse the single serialised example back
        records = list(tf.data.TFRecordDataset(
            str(tmp_path / 'ecg_data.tfrecord')))
        assert len(records) == 1
        feature = tf.train.Example.FromString(
            records[0].numpy()).features.feature
        # #### metadata: 'note' dropped, flattened (2 records, 1 column)
        assert list(feature[CTypes.MetaData].float_list.value) == [50.0, 60.0]
        # #### waveforms: tf.io.parse_tensor recovers shape and dtype with
        # no hardcoded reshape (n_records=2, 12 leads, length=5)
        serialized = feature[CTypes.WaveForms].bytes_list.value[0]
        waves = tf.io.parse_tensor(serialized, out_type=tf.float32).numpy()
        assert waves.shape == (2, 12, 5)
        np.testing.assert_allclose(waves[0, 0], np.arange(5.0))
        np.testing.assert_allclose(waves[1, 1], np.arange(5.0) + 3)
        # absent leads carry NaN
        assert np.isnan(waves[0, 2]).all()
        # #### median beats were not exported
        assert CTypes.MedianBeats not in feature
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_differing_chunk_shapes_no_corruption(self, tmp_path,
                                                   make_context):
        """
        Two chunks written by the same writer instance with different
        record counts and signal lengths must each decode back to their
        own shape. Before the shape-preserving format, a reader had to
        assume one fixed reshape for every chunk; this guards against
        that silent-corruption failure mode returning.
        """
        import tensorflow as tf
        writer = TFRecordWriter()
        # #### chunk 0: 2 records, signal length 5
        wave_a = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx_a = make_context(
            tmp_path, e_meta=False, e_median=False, chunk_num=0)
        writer.write([], wave_a, [], ctx_a)
        # #### chunk 1: 3 records, signal length 3 (a smaller final chunk
        # with a different record count and signal length)
        wave_b = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1},
                  {'I': np.arange(3.0) + 2}]
        ctx_b = make_context(
            tmp_path, e_meta=False, e_median=False, chunk_num=1)
        writer.write([], wave_b, [], ctx_b)
        _, _, _, file_a, _ = writer.file_names(chunk_num=0)
        _, _, _, file_b, _ = writer.file_names(chunk_num=1)

        def _read_waves(path):
            record = list(tf.data.TFRecordDataset(str(path)))[0]
            feature = tf.train.Example.FromString(
                record.numpy()).features.feature
            serialized = feature[CTypes.WaveForms].bytes_list.value[0]
            return tf.io.parse_tensor(serialized, out_type=tf.float32).numpy()

        waves_a = _read_waves(tmp_path / file_a)
        waves_b = _read_waves(tmp_path / file_b)
        assert waves_a.shape == (2, 12, 5)
        assert waves_b.shape == (3, 12, 3)
        np.testing.assert_allclose(waves_a[1, 0], np.arange(5.0) + 1)
        np.testing.assert_allclose(waves_b[2, 0], np.arange(3.0) + 2)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestLazyTensorflow(object):
    """
    Testing that tensorflow is an optional, lazily imported dependency:
    importing the package must not import tensorflow, and using the
    tfrecord writer without tensorflow installed must raise an actionable
    ImportError naming the install route.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_package_import_does_not_import_tensorflow(self):
        # a fresh interpreter is needed: the current test process may
        # already have tensorflow in sys.modules from other tests
        code = (
            'import sys; '
            'import ecgprocess; '
            'import ecgprocess.writer; '
            'import ecgprocess.tabular; '
            "assert 'tensorflow' not in sys.modules, "
            "'tensorflow imported at package import time'"
        )
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_tensorflow_raises_actionable_error(
            self, tmp_path, monkeypatch, make_context):
        # None in sys.modules makes `import tensorflow` raise ImportError,
        # emulating an absent installation regardless of prior imports
        monkeypatch.setitem(sys.modules, 'tensorflow', None)
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        with pytest.raises(ImportError, match=r'ecgprocess\[tensorflow\]'):
            TFRecordWriter().write([], wave, [], ctx)
        # the import is checked before any file is written
        assert os.listdir(tmp_path) == []
