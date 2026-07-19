"""
Shared pytest configuration for the ECGProcess test suite.

Provides the `tensorflow` and `wfdb` markers: tests marked with
`@pytest.mark.tensorflow`/`@pytest.mark.wfdb` are skipped automatically
when the corresponding package is not installed, so the suite passes in
both environments (tensorflow and wfdb are optional dependencies).
"""
import os
import importlib.util
import pytest

# set before any test module can import tensorflow: the C++ core reads
# this once at first import, keeping its startup banner out of the test
# output (production paths are covered by `_import_tensorflow`)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
# availability is checked without importing tensorflow/wfdb, so the
# lazy-import guarantees under test are not defeated at collection time
TENSORFLOW_INSTALLED = importlib.util.find_spec('tensorflow') is not None
WFDB_INSTALLED = importlib.util.find_spec('wfdb') is not None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def pytest_collection_modifyitems(config, items):
    """Skip optional-dependency-marked tests when the package is absent."""
    skip_tf = pytest.mark.skip(
        reason='tensorflow is not installed (optional dependency)')
    skip_wfdb = pytest.mark.skip(
        reason='wfdb is not installed (optional dependency)')
    for item in items:
        if not TENSORFLOW_INSTALLED and 'tensorflow' in item.keywords:
            item.add_marker(skip_tf)
        if not WFDB_INSTALLED and 'wfdb' in item.keywords:
            item.add_marker(skip_wfdb)
