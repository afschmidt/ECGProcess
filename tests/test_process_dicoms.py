import pytest
from ecgprocess.constants import ProcessDicomNames as PDNames
from ecgprocess.errors import MissingDICOMTagError
from ecgprocess.process_dicoms import (
    ECGDICOMReader,
    ECGDICOMTable,
)
from ecgprocess.example_data.examples import (
    list_data_paths,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Relevant paths
dicom_file_path = list_data_paths()['example_dicom_1']
dicom_path_list = [
    list_data_paths()['example_dicom_1'],
    list_data_paths()['example_dicom_2'],
]
dicom_wrong_list = ['wrong']

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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestECGDICOMTable(object):
    """
    Testing ECGDICOMTable
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default_call(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
        res = ecgtable(verbose=False)
        assert getattr(res, PDNames.CPATH_L) == dicom_path_list
        assert len(getattr(res, PDNames.FPATH_L)) == 0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_path_call(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGDICOMTable(ecgreader,
                                 path_list=dicom_path_list + dicom_wrong_list)
        with pytest.warns(UserWarning):
            res = ecgtable(verbose=True, skip_missing=True)
        assert getattr(res, PDNames.CPATH_L) == dicom_path_list
        assert getattr(res, PDNames.FPATH_L) == dicom_wrong_list
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_error_call(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGDICOMTable(ecgreader,
                                 path_list=dicom_path_list + dicom_wrong_list)
        with pytest.raises(PermissionError):
            _ = ecgtable(verbose=True, skip_missing=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_table(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
        res = ecgtable().get_table(update_keys={'I (Einthoven)': 'I'})
        assert len(getattr(res, PDNames.KEY_L)) == 2
        assert getattr(res, PDNames.KEY_L)[0] ==\
            '2.25.269796857626990821315969488216511468638'
        assert getattr(res, PDNames.INFO_T).shape[1] > 0
        assert len(getattr(res, PDNames.WAVE_T)['Lead'].unique()) == 12
        assert len(getattr(res, PDNames.MEDIAN_T)['Lead'].unique()) == 12
        assert getattr(res, PDNames.MEDIAN_T).shape[0] > 1000
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_table_error(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
        with pytest.raises(KeyError):
            _ = ecgtable().get_table()



