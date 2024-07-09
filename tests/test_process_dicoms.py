import pytest
from ecgprocess.constants import ProcessDicomNames as PDNames
from ecgprocess.errors import MissingDICOMTagError
from ecgprocess.process_dicoms import (
    ECGDICOMReader,
)
from ecgprocess.example_data.examples import (
    list_data_paths,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Relevant paths
dicom_file_path = list_data_paths()['example_dicom']

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ECGDICOMReader
class TestECGDICOMReader(object):
    """
    Testing ECGDICOMReader
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self):
        ECG_DCM = ECGDICOMReader()
        res = ECG_DCM(path=dicom_file_path)
        assert len(res.__getattribute__(PDNames.RESULTS_DICT)) > 0
        assert isinstance(res.__getattribute__(PDNames.RESULTS_DICT), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES2), dict)
        assert len(res.__getattribute__(PDNames.LEAD_VOLTAGES)) == 12
        assert res.__getattribute__(PDNames.OVERSAMPLED) == True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_leads(self):
        ECG_DCM = ECGDICOMReader(augment_leads=True)
        res = ECG_DCM(path=dicom_file_path)
        assert len(res.__getattribute__(PDNames.RESULTS_DICT)) > 0
        assert isinstance(res.__getattribute__(PDNames.RESULTS_DICT), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES2), dict)
        assert len(res.__getattribute__(PDNames.LEAD_VOLTAGES)) == 12
        assert len(res.__getattribute__(PDNames.LEAD_VOLTAGES2)) == 12
        assert res.__getattribute__(PDNames.OVERSAMPLED) == True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_resample(self):
        ECG_DCM = ECGDICOMReader(resample_500=False)
        res = ECG_DCM(path=dicom_file_path)
        assert len(res.__getattribute__(PDNames.RESULTS_DICT)) > 0
        assert isinstance(res.__getattribute__(PDNames.RESULTS_DICT), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES), dict)
        assert isinstance(res.__getattribute__(PDNames.LEAD_VOLTAGES2), dict)
        assert len(res.__getattribute__(PDNames.LEAD_VOLTAGES)) == 12
        assert len(res.__getattribute__(PDNames.LEAD_VOLTAGES2)) == 12
        assert res.__getattribute__(PDNames.OVERSAMPLED) == False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_verbose(self):
        ECG_DCM = ECGDICOMReader()
        with pytest.warns(UserWarning):
            ECG_DCM(path=dicom_file_path, verbose=True)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_errors(self):
        ECG_DCM = ECGDICOMReader()
        with pytest.raises(MissingDICOMTagError):
            ECG_DCM(path=dicom_file_path, skip_empty=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_path(self):
        ECG_DCM = ECGDICOMReader()
        with pytest.raises(PermissionError):
            ECG_DCM(path='wrong', skip_empty=False)

