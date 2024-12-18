import os
import pytest
import ecgprocess.utils.config_tools as config_utils
from tempfile import NamedTemporaryFile
from ecgprocess.constants import ProcessDicomNames as PDNames
from ecgprocess.errors import MissingTagError
from ecgprocess.process_dicom import (
    ECGDICOMReader,
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
    def test_wrong_permission_file(self, tmp_path):
        # Create a dummy invalid DICOM file
        unreadable_file = tmp_path / "invalid_file.dcm"
        unreadable_file.write_text("This is not a valid DICOM file")
        os.chmod(unreadable_file, 0o000)
        ECG_DCM = ECGDICOMReader()
        with pytest.raises(PermissionError):
            _ = ECG_DCM(path=unreadable_file)
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
