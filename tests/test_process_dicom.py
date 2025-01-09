import pytest
import warnings
import ecgprocess.utils.config_tools as config_utils
from unittest import mock
from tempfile import NamedTemporaryFile
from ecgprocess.errors import MissingTagError
from ecgprocess.process_dicom import (
    ECGDICOMReader,
    FixedDICOMReader,
)
from ecgprocess.example_data.examples import (
    list_dicom_paths as list_data_paths,
    config_file,
)
from ecgprocess.constants import (
    ProcessXMLNames as PXMLNam,
    ProcessDicomNames as PDNames,
    CoreData as Core,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
CTypes = Core.DataTypes
CProc = Core.ProcessingData
# Relevant paths
dicom_file_path = list_data_paths()['example_dicom_1']
dicom_file_path2 = list_data_paths()['example_dicom_2']
# example config
example_config = {
    "WaveForms": [
        'aVR\t\t\t\t\tWaveformData.ECG_Leads_3',
        'aVL\t\t\t\t\tWaveformData.ECG_Leads_4',
        'II\t\t\t\t\tWrong',
    ],
    "MedianBeats": [
        'V1\t\t\t\t\tWaveformData.Median_Beats_6',
        'V2\t\t\t\t\tWaveformData.Median_Beats_7',
    ],
    "MetaData": [
        "unique identifier\t\t\t\tSOP Class UID",
        "number of leads\t\t\t\t\tWaveform Sequence_0.Number of Waveform Channels",
        "resolution unit (waveforms)\t\t\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
        "resolution (waveforms)\t\t\t\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity",
        "resolution unit (medianbeats)\t\t\tWaveform Sequence_1.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
        "patient identifier\t\t\t\tPatient ID",
        "gender\t\t\t\t\t\tPatient's Sex",
        "birthday\t\t\t\t\tPatient's Birth Date",
    ]
}
pattern = {f"Waveform Annotation Sequence_{i}.":\
           "Name Code Sequence_0.Code Meaning" for i in range(17)}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ECGDICOMReader
class TestECGDICOMReader(object):
    """
    Testing ECGDICOMReader
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_init(self):
        # default
        ECG_DCM = ECGDICOMReader()
        assert getattr(ECG_DCM, CProc.TAGS) is None
        assert getattr(ECG_DCM, CProc.RAW) is None
        # assert hasattr(ECG_DCM, CProc.TAGS) == False
        assert getattr(ECG_DCM, '_as_array') == True
        assert getattr(ECG_DCM, PXMLNam.AUG_LEADS) == False
        assert getattr(ECG_DCM, PXMLNam.RESAMPLE) == True
        # with arguments
        ECG_DCM = ECGDICOMReader(augment_leads=True, resample_500=False)
        assert getattr(ECG_DCM, PXMLNam.AUG_LEADS) == True
        assert getattr(ECG_DCM, PXMLNam.RESAMPLE) == False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_call(self):
        ECG_DCM = ECGDICOMReader()
        file1 = ECG_DCM(path=dicom_file_path)
        assert len(getattr(file1, CProc.TAGS)) > 100
        assert len(getattr(file1, CProc.RAW)) > 100
        assert len(getattr(file1, CProc.TAGS)) ==\
            len(getattr(file1, CProc.RAW))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_dicom_file(self, tmp_path):
        # Create a dummy invalid DICOM file
        invalid_file = tmp_path / "invalid_file.dcm"
        invalid_file.write_text("This is not a valid DICOM file")
        ECG_DCM = ECGDICOMReader()
        with pytest.raises(ValueError):
            _ = ECG_DCM(path=invalid_file)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_permission_file(self):
        # Mock the behavior of opening the file and raise PermissionError
        ECG_DCM = ECGDICOMReader()
        with mock.patch("builtins.open",
                        mock.MagicMock(side_effect=PermissionError)):
            with pytest.raises(PermissionError):
                _ = ECG_DCM(path="invalid_file.dcm")
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract(self):
        n_leads = 'number of leads'
        # set-up the config file and parse it
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=example_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)()
        # examples
        _ = parsed_confg.map(mapper=config_utils.DataMap())
        ECG_DCM = ECGDICOMReader(resample_500=False)
        file2 = ECG_DCM(path=dicom_file_path2, verbose=True)
        # extraction 1
        with pytest.warns(UserWarning):
            extract2 = file2.extract(config=parsed_confg)
        assert extract2.MetaData[n_leads] == 12
        assert extract2.WaveForms['II'] is None
        assert extract2.WaveForms['aVL'].ndim == 1
        # extraction 2
        with pytest.raises(MissingTagError):
            file2.extract(config=parsed_confg, skip_empty=False)
        # extraction 3
        file3 = ECG_DCM(path=dicom_file_path2, verbose=False)
        extract3 = file3.extract(config=parsed_confg, parse_numeric=False)
        assert extract2.MetaData[n_leads] == 12
        assert extract2.WaveForms['II'] is None
        assert extract2.WaveForms['aVL'].ndim == 1
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract_pattern(self):
        n_leads = 'number of leads'
        # set-up the config file and parse it
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=example_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)()
        # examples
        _ = parsed_confg.map(mapper=config_utils.DataMap())
        ECG_DCM = ECGDICOMReader(resample_500=False)
        file2 = ECG_DCM(path=dicom_file_path2, verbose=True)
        # extraction 1
        with pytest.warns(UserWarning):
            extract2 = file2.extract(config=parsed_confg, pattern=pattern)
        assert extract2.MetaData[n_leads] == 12
        assert extract2.MetaData['PR Interval (Numeric Value)'] == 0.0
        assert extract2.WaveForms['II'] is None
        assert extract2.WaveForms['aVL'].ndim == 1

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FixedDICOMReader
class TestFixedDICOMReader(object):
    """
    Testing FixedDICOMReader
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self):
        ECG_DCM = FixedDICOMReader()
        res = ECG_DCM(path=dicom_file_path)
        assert len(getattr(res, CTypes.MetaData)) > 0
        assert isinstance(getattr(res,CTypes.MetaData), dict)
        assert isinstance(getattr(res,CTypes.WaveForms), dict)
        assert isinstance(getattr(res,CTypes.MedianBeats), dict)
        assert len(getattr(res,CTypes.WaveForms)) == 12
        assert getattr(res,CTypes.MetaData)['MedianWaveformUnits']==\
                       'microvolt'
        assert getattr(res,CTypes.MetaData)['sampling number (medianbeats)']==\
            600
        assert getattr(res,CTypes.MetaData)['sampling number (waveforms)']==5000
        assert getattr(res,'augment_leads') == False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_leads(self):
        ECG_DCM = FixedDICOMReader(augment_leads=True)
        res = ECG_DCM(path=dicom_file_path)
        assert len(getattr(res,CTypes.MetaData)) > 0
        assert isinstance(getattr(res,CTypes.MetaData), dict)
        assert isinstance(getattr(res,CTypes.WaveForms), dict)
        assert isinstance(getattr(res,CTypes.MedianBeats), dict)
        assert len(getattr(res,CTypes.WaveForms)) == 12
        assert len(getattr(res,CTypes.MedianBeats)) == 12
        assert getattr(res,'augment_leads') == True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_resample(self):
        ECG_DCM = FixedDICOMReader(resample_500=False)
        res = ECG_DCM(path=dicom_file_path)
        assert len(getattr(res,CTypes.MetaData)) > 0
        assert isinstance(getattr(res,CTypes.MetaData), dict)
        assert isinstance(getattr(res,CTypes.WaveForms), dict)
        assert isinstance(getattr(res,CTypes.MedianBeats), dict)
        assert len(getattr(res,CTypes.WaveForms)) == 12
        assert len(getattr(res,CTypes.MedianBeats)) == 12
        assert getattr(res,'resample_500') == False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecg_trait(self):
        ECG_DCM = FixedDICOMReader()
        # mess-up the name to check case sensitivity (should not be)
        QT_NAM = 'QT Interval'
        w_qt_int = 'qt interval'
        ECG_DCM.ECG_TRAIT_DICT[QT_NAM] = [QT_NAM, w_qt_int]
        res = ECG_DCM(path=list_data_paths()['example_dicom_2'])
        assert isinstance(getattr(res, CTypes.MetaData), dict)
        assert getattr(res, CTypes.MetaData)['QRS Duration'] == 92
        assert getattr(res, CTypes.MetaData)['QT Interval UNIT'] ==\
            'millisecond'
        assert getattr(res, CTypes.MetaData)[QT_NAM] == 378
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecg_trait_value_conversion_with_null(self):
        """
        Test ECG trait value extraction when the `ECG_TRAIT_VALUE` is set to
        None.
        """
        # Load the DICOM file
        ECG_DCM = FixedDICOMReader(retain_raw=True)
        ecg_instance = ECG_DCM(path=dicom_file_path2)
        # turn on verbose
        ecg_instance.verbose = True
        # get raw ECG
        ECG = ecg_instance.DMCReadInstance
        # Simulate setting the specific attribute to None
        for waveform_annotation in getattr(ECG, 'WaveformAnnotationSequence'):
            if hasattr(waveform_annotation, 'NumericValue'):
                setattr(waveform_annotation, 'NumericValue', None)
        # make sure we get warnings
        with warnings.catch_warnings(record=True) as w:
            # warnings.simplefilter("always")
            _, _, miss  = ecg_instance._get_waveform_annotation(
                dicom_instance=ECG, skip_empty=True,
            )
            # warnings.resetwarnings()
        # Confirm warnings were raised and there are missing
        assert len(w) > 0
        assert len(miss) > 0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_verbose(self):
        ECG_DCM = FixedDICOMReader()
        with pytest.warns(UserWarning):
            _ = ECG_DCM(path=dicom_file_path, verbose=True)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_errors(self):
        ECG_DCM = FixedDICOMReader()
        with pytest.raises(MissingTagError):
            _ = ECG_DCM(path=dicom_file_path, skip_empty=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_path(self):
        ECG_DCM = FixedDICOMReader()
        with pytest.raises(PermissionError):
            _ = ECG_DCM(path='wrong', skip_empty=False)
