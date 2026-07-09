"""
Shared pytest configuration for the ECGProcess test suite.

Provides the `tensorflow` marker: tests marked with
`@pytest.mark.tensorflow` are skipped automatically when tensorflow is
not installed, so the suite passes in both environments (tensorflow is
an optional dependency).
"""
import importlib.util
import pytest

# availability is checked without importing tensorflow, so the
# lazy-import guarantees under test are not defeated at collection time
TENSORFLOW_INSTALLED = importlib.util.find_spec('tensorflow') is not None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def pytest_collection_modifyitems(config, items):
    """Skip `tensorflow`-marked tests when tensorflow is not installed."""
    if TENSORFLOW_INSTALLED:
        return
    skip_tf = pytest.mark.skip(
        reason='tensorflow is not installed (optional dependency)')
    for item in items:
        if 'tensorflow' in item.keywords:
            item.add_marker(skip_tf)
