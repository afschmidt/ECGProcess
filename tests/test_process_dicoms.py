import pytest
import numpy as np
from ecgprocess.process_dicoms import (
    ECGDICOMReader,
)
from ecgprocess.example_data.examples import (
    list_data_paths,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Relevant paths
dicom_file_path = list_data_paths()['example_dicom']
ECG_DCM = ECGDICOMReader()
temp = ECG_DCM(path=dicom_file_path)
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ECGDICOMReader
class TestECGDICOMReader(object)
    """
    Testing ECGDICOMReader
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self, interval_values):
        ECG_DCM = ECGDICOMReader()
        ECG_DCM(path=dicom_file_path)
        res = univariable_quantiles_exact(interval_values, quantile=0.5)
        assert res.__getattribute__(NamesI.POINT) == 3
        assert res.__getattribute__(NamesI.VALUES) == [2, 11]
        assert res.__getattribute__(NamesI.INDICES) == [2, 8]
        assert np.round(res.__getattribute__(NamesI.COVERAGE),2) == 0.96
        assert res.__getattribute__(NamesI.MATRIX_COLUMNS) == [6,5,7,8,9]
        assert res.__getattribute__(NamesI.MATRIX_ROWS) == [1, 0, 2, 3, 4]
        assert isinstance(res.__getattribute__(NamesI.MATRIX_COVERAGE),
                           np.ndarray)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_alpha(self, interval_values):
        res = univariable_quantiles_exact(interval_values, quantile=0.5,
                                          alpha=0.10)
        assert res.__getattribute__(NamesI.VALUES) == [1.5, 10]
        assert res.__getattribute__(NamesI.INDICES) == [1, 7]
        assert np.round(res.__getattribute__(NamesI.COVERAGE),2) == 0.91
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # NOTE window works fine, but changing the value does not impact output
    # which is not necessaritly bad, just need to think of edge cases to force
    # a distinct output
    def test_window(self, interval_values):
        res = univariable_quantiles_exact(interval_values, quantile=0.2,
                                          window=4, alpha=0.20,
                                          )
        assert res.__getattribute__(NamesI.VALUES) == [1.5, 4]
        assert res.__getattribute__(NamesI.INDICES) == [1, 5]
        assert np.round(res.__getattribute__(NamesI.COVERAGE),2) == 0.85
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_errors(self, interval_values):
        with pytest.raises(TypeError):
            _ = univariable_quantiles_exact(interval_values[0:2], quantile=0.5,
                                              alpha=0.10)
        with pytest.raises(IndexError):
            _ = univariable_quantiles_exact(interval_values[0:4], quantile=0.5,
                                              alpha=0.10)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# univariable_poisson
class TestUnivariablePoissonStandardNormal(object):
    """
    Testing univariable_poisson_standard_normal
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self, interval_values):
        res = univariable_poisson_standard_normal(interval_values)
        assert np.round(res.__getattribute__(NamesI.POINT),2) == 4.44
        assert all(np.round(res.__getattribute__(NamesI.VALUES), 2) ==\
                   [3.07, 5.82])
        assert res.__getattribute__(NamesI.COVERAGE) == 0.95
        assert np.round(res.__getattribute__(NamesI.SE),2) == 0.7
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_alpha(self, interval_values):
        res = univariable_poisson_standard_normal(interval_values, alpha=0.01)
        assert np.round(res.__getattribute__(NamesI.POINT),2) == 4.44
        assert all(np.round(res.__getattribute__(NamesI.VALUES), 2) ==\
                   [2.63, 6.25])
        assert res.__getattribute__(NamesI.COVERAGE) == 0.99

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# wald_confidence_interval
class TestWaldConfidenceInterval(object):
    """
    Testing wald_confidence_interval
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self):
        res = wald_confidence_interval(0.2, 0.01)
        assert res.__getattribute__(NamesI.POINT) == 0.20
        assert np.round(res.__getattribute__(NamesI.SE),2) == 0.01
        assert list(np.round(res.__getattribute__(NamesI.VALUES), 2)) ==\
                   [0.18, 0.22]
        assert res.__getattribute__(NamesI.COVERAGE) == 0.95
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_alpha(self):
        res = wald_confidence_interval(0.2, 0.01, alpha=0.001)
        assert res.__getattribute__(NamesI.POINT) == 0.20
        assert np.round(res.__getattribute__(NamesI.SE),2) == 0.01
        assert list(np.round(res.__getattribute__(NamesI.VALUES), 2)) ==\
                   [0.17, 0.23]
        assert res.__getattribute__(NamesI.COVERAGE) == 0.999


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# beta_confidence_interval
class TestBetaConfidenceInterval(object):
    """
    Testing beta_confidence_interval
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self):
        res = beta_confidence_interval(0.2, 20)
        assert res.__getattribute__(NamesI.POINT) == 0.20
        assert list(np.round(res.__getattribute__(NamesI.VALUES), 2)) ==\
                   [0.06, 0.44]
        assert res.__getattribute__(NamesI.COVERAGE) == 0.95
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_alpha(self):
        res = beta_confidence_interval(0.2, 20, alpha=0.25)
        assert res.__getattribute__(NamesI.POINT) == 0.20
        assert list(np.round(res.__getattribute__(NamesI.VALUES), 2)) ==\
                   [0.1, 0.35]
        assert res.__getattribute__(NamesI.COVERAGE) == 0.75
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_errors(self):
        with pytest.raises(ValueError):
            _ = beta_confidence_interval(0.0542, 20)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_integer(self):
        res = beta_confidence_interval(0.0542, 20, integer=False)
        assert res.__getattribute__(NamesI.POINT) == 0.0542
        assert list(np.round(res.__getattribute__(NamesI.VALUES), 2)) ==\
                   [0.0, 0.25]
        assert res.__getattribute__(NamesI.COVERAGE) == 0.95
