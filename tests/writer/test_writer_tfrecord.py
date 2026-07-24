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
        # #### waveforms: flattened canonical (n_records, 12 leads, length)
        waves = np.array(
            feature[CTypes.WaveForms].float_list.value).reshape(2, 12, 5)
        np.testing.assert_allclose(waves[0, 0], np.arange(5.0))
        np.testing.assert_allclose(waves[1, 1], np.arange(5.0) + 3)
        # absent leads carry NaN
        assert np.isnan(waves[0, 2]).all()
        # #### median beats were not exported
        assert CTypes.MedianBeats not in feature

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
