import os
import pytest
import numpy as np
import pandas as pd
from typing import Any
import ecgprocess.utils.config_tools as config_utils
from ecgprocess.errors import (
    FileValidationError, MissingTagError, XMLValidationError,
    is_type,
)
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.process_dicom import(
    ECGDICOMReader,
)
from ecgprocess.process_xml import(
    ECGXMLReader,
)
from ecgprocess.tabular import (
    ECGTable,
    signal_identity,
)
# from ecgprocess.plot_ecgs import (
#     ECGDrawing,
# )
from tempfile import NamedTemporaryFile
from ecgprocess.example_data.examples import (
    list_dicom_paths,
    list_xml_paths,
)
from ecgprocess.example_data.examples import config_file
from ecgprocess.utils.general import (
    list_tar,
)


pytestmark = pytest.mark.skip(reason=("Need to refactor to work with the "
                                      "updated process_* modules."
                                      ))
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CLeads = Core.Leads
CMeta = Core.MetaData

# #### Relevant paths
dicom_file_path = list_dicom_paths()['example_dicom_1']
dicom_path_list = [
    list_dicom_paths()['example_dicom_2'],
    list_dicom_paths()['example_dicom_1'],
]
dicom_wrong_list = ['wrong'] + dicom_path_list
xml_file_path = list_xml_paths()['example_1']
xml_schema_path = list_xml_paths()['example_1_schema']
xml_schema_error_path = list_xml_paths()['example_1_schema_error']

# #### XML config file
config_xml = {
    "WaveForms": [
        "I\tStripData.WaveformData_0.#text",
        "II\tStripData.WaveformData_1.#text",
    ],
    "MetaData": [
        "unique identifier\tUID.DICOMStudyUID",
        "number of leads\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
        "resolution unit (waveforms)\tStripData.Resolution.@units",
        "resolution (waveforms)\tStripData.Resolution.#text",
        "resolution unit (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.@units",
        "resolution (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.#text",
        "sampling frequency (original)\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
        "sampling frequency unit\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
        "sampling number (waveforms)\tStripData.ChannelSampleCountTotal",
        "sampling number (medianbeats)\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
        "age\tPatientInfo.Age.#text",
        "gender\tPatientInfo.Gender",
        "birthday day\tPatientInfo.BirthDateTime.Day",
        "birthday month\tPatientInfo.BirthDateTime.Month",
        "birthday year\tPatientInfo.BirthDateTime.Year",
        "sysbp unit\tPatientVisit.SysBP.@units",
        "diabpb unit\tPatientVisit.DiaBP.@units",
        "sysbp\tPatientVisit.SysBP.@text",
        "diabpb\tPatientVisit.DiaBP.@text",
        "pacemaker\tPatientInfo.PaceMaker",
    ]
}
with NamedTemporaryFile("w") as tmp_file:
    _ = config_file(path=tmp_file.name, text=config_xml)
    parser_xml = config_utils.ConfigParser(tmp_file.name)()
# adding the mapper
parser_xml.map(mapper=config_utils.DataMap())

# #### XML config file 2
config_xml2 = {
    "WaveForms": [
        "I\tStripData.WaveformData_0.#text",
        "II\tStripData.WaveformData_1.#text",
    ],
    "MetaData": [
        "number of leads\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
        "resolution unit (waveforms)\tStripData.Resolution.@units",
        "resolution (waveforms)\tStripData.Resolution.#text",
        "resolution unit (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.@units",
        "resolution (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.#text",
        "sampling frequency (original)\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
        "sampling frequency unit\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
        "sampling number (waveforms)\tStripData.ChannelSampleCountTotal",
        "sampling number (medianbeats)\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
        "age\tPatientInfo.Age.#text",
        "gender\tPatientInfo.Gender",
        "birthday day\tPatientInfo.BirthDateTime.Day",
        "birthday month\tPatientInfo.BirthDateTime.Month",
        "birthday year\tPatientInfo.BirthDateTime.Year",
        "sysbp unit\tPatientVisit.SysBP.@units",
        "diabpb unit\tPatientVisit.DiaBP.@units",
        "sysbp\tPatientVisit.SysBP.@text",
        "diabpb\tPatientVisit.DiaBP.@text",
        "pacemaker\tPatientInfo.PaceMaker",
    ]
}
with NamedTemporaryFile("w") as tmp_file:
    _ = config_file(path=tmp_file.name, text=config_xml2)
    parser_xml2 = config_utils.ConfigParser(tmp_file.name)()
# adding the mapper
parser_xml2.map(mapper=config_utils.DataMap())

# #### DICOM config file
leads = [attr for attr in dir(CLeads) if not attr.startswith("__")]
config_dicom = {
    "WaveForms": [
        f"{getattr(CLeads, lead)}\tWaveformData.ECG_Leads_{idx}"
        for idx, lead in enumerate(leads)],
    "MedianBeats": [
        f"{getattr(CLeads, lead)}\tWaveformData.Median_Beats{idx}"
        for idx, lead in enumerate(leads)],
    "MetaData": [
        "unique identifier\tSOP Class UID",
        "number of leads\tWaveform Sequence_0.Number of Waveform Channels",
        "resolution unit (waveforms)\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
        "resolution (waveforms)\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity",
        "resolution unit (medianbeats)\tWaveform Sequence_1.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
        "resolution (medianbeats)\tWaveform Sequence_1.Channel Definition Sequence_0.Channel Sensitivity",
        "sampling frequency (original)\tWaveform Sequence_0.Sampling Frequency",
        "sampling number (waveforms)\tWaveform Sequence_0.Number of Waveform Samples",
        "sampling number (medianbeats)\tWaveform Sequence_1.Number of Waveform Samples",
        "Softwave version\tSoftware Versions",
        "Manufacturer\tManufacturer",
        "Model name\tManufacturer's Model Name",
    ] +\
    [
        f"wave_channel_sens_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Sensitivity" for idx, _ in enumerate(leads)] +\
    [
        f"wave_channel_correctionfactor_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Sensitivity Correction Factor" for idx, _ in enumerate(leads)] +\
    [
        f"wave_channel_baseline_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Baseline" for idx, _ in enumerate(leads)]
}
with NamedTemporaryFile("w") as tmp_file:
    _ = config_file(path=tmp_file.name, text=config_dicom)
    parser_dicom = config_utils.ConfigParser(tmp_file.name)()
# adding the mapper
parser_dicom.map(mapper=config_utils.DataMap())

# #### engineer functions
def signal_correction(signals:dict[str, np.ndarray], verbose:bool=False,
                      **kwargs) -> dict[str, Any]:
    """
    Correct the waveform signal based on the signal specific sensitity,
    correction factor, and the channel baseline floats, all extracted from
    meta_dict extract from the kwargs.
    """
    # constants - these values should be in meta_dict
    sens = "wave_channel_sens_"
    corr = "wave_channel_correctionfactor_"
    base = "wave_channel_baseline_"
    # the algorithm
    is_type(verbose, bool)
    if not TabNames.META_DICT in kwargs:
        raise KeyError(f"`{TabNames.META_DICT}` should be included as kwargs")
    else:
        meta_dict = kwargs[TabNames.META_DICT]
    for i, (k, v) in enumerate(signals.items()):
        # skip of None
        if v is None:
            signals[k] = v
            continue
        # just to be sure this is an ndarray
        is_type(v, np.ndarray)
        fact = meta_dict[sens+str(i)] * meta_dict[corr+str(i)]
        if verbose:
            print(f'Applying baseline: {base} and factor: {fact} '
                  f'corrections to lead: {k}.'
                  )
        signals[k] = (v + meta_dict[base+str(i)]) * fact
    return signals

# def metadata_checkversion(metadata:dict[str, Any],
#     expected_version = ['1.02 SP03', 'MUSE_9.0.9.18167'],
#     expected_manufacturer = 'GE Healthcare', expected_model = 'MV360',
#     verbose:bool=False, **kwargs) -> dict[str, Any]:
#     """
#     Will check the DICOM version and manufacturer and will
#     raise an InputValidationError if this differs from the supplied constants.
#     """
#     # just keeping this so kwargs is used.
#     if verbose:
#         print(**kwargs)
#     # constant
#     version = "Softwave version"
#     manufact = "Manufacturer"
#     model_name = "Model name"
#     # the algorithm
#     if expected_version != metadata[version] or\
#         expected_manufacturer != metadata[manufact] or\
#         expected_model != metadata[model_name]:
#         raise FileValidationError(
#             f"The version `{metadata[version]}`, manufacturer "
#             f"`{metadata[manufact]}` or model `{metadata[model_name]}` failed "
#             "to validate."
#         )
#     # if all corect simply return meta
#     return metadata

# # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# # pytest

# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# class TestTable(object):
#     """
#     Testing ECGTable
#     """
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_init(self):
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
#         assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
#         assert getattr(ecgtable, TabNames.SCHEMA) is None
#         assert getattr(ecgtable, TabNames.ENG_WAVE) == signal_identity
#         # testing the different extract parameters
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             extract_meta=False, extract_median=False)
#         assert getattr(ecgtable, TabNames.E_MEDIAN) == False
#         assert getattr(ecgtable, TabNames.E_WAVE) == True
#         # testing with schema
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             schema=xml_schema_path)
#         assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
#         assert getattr(ecgtable, TabNames.SCHEMA) == xml_schema_path
#         assert getattr(ecgtable, TabNames.E_MEDIAN) == True
#         # testing the engineer parameters
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             engineer_wave=signal_correction)
#         assert getattr(ecgtable, TabNames.ENG_MEDIAN) == signal_identity
#         assert getattr(ecgtable, TabNames.ENG_WAVE) == signal_correction
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_call(self):
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
#         res = ecgtable()
#         assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
#         assert getattr(ecgtable, TabNames.CPATH_L) == [xml_file_path]
#         assert len(getattr(ecgtable, TabNames.FPATH_L)) == 0
#         # including incorrect paths
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGTable(ecgreader, path_list=dicom_wrong_list)
#         res = ecgtable()
#         assert getattr(ecgtable, TabNames.RPATH_L) == dicom_wrong_list
#         assert getattr(ecgtable, TabNames.CPATH_L) == dicom_path_list
#         assert len(getattr(ecgtable, TabNames.FPATH_L)) == 1
#         assert getattr(res, TabNames.SKIP_DATA) == False
#         assert getattr(res, TabNames.SKIP_INVALID) == False
#         # getting warnings
#         ecgtable = ECGTable(ecgreader, path_list=dicom_wrong_list)
#         with pytest.warns(UserWarning):
#             res = ecgtable(verbose=True)
#         # getting errors
#         with pytest.raises(PermissionError):
#             res = ecgtable(ignore_permission=False)
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_loop_table_default(self):
#         # without validation
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
#         res = ecgtable()
#         meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
#                                              parsed_config=parser_xml)
#         assert len(median) != 0
#         assert len(meta[0][CMeta.UID]) > 0
#         assert meta[0][CMeta.NLEADS] == 12
#         assert len(wave[0][CLeads.I]) > 0
#         # excluding medianbeats and waveforms
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             extract_median=False, extract_wave=False,)
#         res = ecgtable()
#         meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
#                                              parsed_config=parser_xml)
#         assert len(median) == 0
#         assert len(wave) == 0
#         assert getattr(res, TabNames.KEY_L)[0] == meta[0][CMeta.UID]
#         # unique False, with the config ommit the UID
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             extract_median=False, extract_wave=False,)
#         res = ecgtable()
#         meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
#                                              parsed_config=parser_xml2,
#                                              unique=False,)
#         assert meta[0][CMeta.UID] is None
#         assert getattr(res, TabNames.KEY_L) == [1]
#         # kwargs to reader call, setting skip_root to false results
#         # in no data being extracted because the config files does not match
#         # anymore. Adjusting the reader to deal with this lack of key data.
#         ecgreader = ECGXMLReader(resample_500=False)
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],)
#         res = ecgtable()
#         meta, wave, median = res._loop_table(
#             getattr(res, TabNames.CPATH_L), parsed_config=parser_xml,
#             kwargs_reader_call={'skip_root':False},
#         )
#         assert all(m is None for m in meta[0].values())
#         assert all(m is None for m in wave[0].values())
#         assert all(m is None for m in median[0].values())
#         # kwargs to reader extract, setting skip_empty to False
#         # will raise a reader error.
#         ecgreader = ECGXMLReader(resample_500=False)
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],)
#         res = ecgtable()
#         with pytest.raises(MissingTagError):
#             res._loop_table(
#                 getattr(res, TabNames.CPATH_L), parsed_config=parser_xml,
#                 kwargs_reader_extract={'skip_empty':False},
#             )
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_loop_table_xml(self):
#         # using an XML schema
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             schema=xml_schema_path,)
#         res = ecgtable()
#         meta, wave, median = res._loop_table(
#             getattr(res, TabNames.CPATH_L),
#             parsed_config=parser_xml,
#         )
#         assert len(median) != 0
#         assert len(meta[0][CMeta.UID]) > 0
#         assert meta[0][CMeta.NLEADS] == 12
#         assert len(wave[0][CLeads.I]) > 0
#         # causing in invalidation error
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             schema=xml_schema_error_path,)
#         res = ecgtable()
#         with pytest.raises(XMLValidationError):
#             res._loop_table(
#                 getattr(res, TabNames.CPATH_L),
#                 parsed_config=parser_xml,
#             )
#         # ignoring the error
#         ecgreader = ECGXMLReader()
#         ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
#                             schema=xml_schema_error_path,)
#         res = ecgtable(ignore_invalid=True)
#         meta, wave, median = res._loop_table(
#             getattr(res, TabNames.CPATH_L),
#             parsed_config=parser_xml,
#         )
#         assert meta == wave == median == []
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_loop_table_engineer_func(self):
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGTable(ecgreader, path_list=[dicom_file_path],
#                             engineer_wave=signal_correction,
#                             )
#         res = ecgtable()
#         _, wave, _ = res._loop_table(
#             getattr(res, TabNames.CPATH_L),
#             parsed_config=parser_dicom,
#         )
#         assert wave[0]['I'][2] == 142.8864
#         assert wave[0]['I'][2] != 29.28, 'still has the orignal value'


#     def test_get_table(self):
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().get_table(update_keys={'I (Einthoven)': 'I'})
#         assert len(getattr(res, PDNames.KEY_L)) == 2
#         assert len(getattr(res, PDNames.KEY_L)[0]) > 1
#         assert getattr(res, PDNames.INFO_T).shape[1] > 0
#         assert len(getattr(res, PDNames.WAVE_T)['Lead'].unique()) == 12
#         assert len(getattr(res, PDNames.MEDIAN_T)['Lead'].unique()) == 12
#         assert getattr(res, PDNames.MEDIAN_T).shape[0] > 1000
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_get_metatable(self):
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list,
#                                  info_type='meta')
#         res = ecgtable().get_table()
#         assert len(getattr(res, PDNames.KEY_L)) == 2
#         assert len(getattr(res, PDNames.KEY_L)[0]) > 1
#         assert getattr(res, PDNames.INFO_T).shape[1] > 0
#         assert hasattr(res, PDNames.WAVE_T) == False
#         assert hasattr(res, PDNames.MEDIAN_T) == False
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_get_table_keyerror(self):
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         with pytest.raises(KeyError):
#             _ = ecgtable().get_table()
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_get_table_valerror(self):
#         ecgreader = ECGDICOMReader()
#         with pytest.raises(ValueError):
#             _ = ECGDICOMTable(ecgreader, path_list=dicom_path_list,
#                                      info_type='ALL')
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg(self, tmp_path):
#         # change current directory
#         os.chdir(tmp_path)
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().write_ecg(update_keys={'I (Einthoven)': 'I'})
#         # get content and read in a table
#         content = os.listdir(getattr(res, PDNames.WRITE_ECG_PATH))
#         table = pd.read_csv(os.path.join(getattr(res, PDNames.WRITE_ECG_PATH),
#                                          PDNames.INFO_FILE),
#                             sep='\t')
#         assert set(content) == expect_content
#         assert table.shape[0] == 2
#         assert table.shape[1] > 10
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg_path(self, tmp_path):
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().write_ecg(update_keys={'I (Einthoven)': 'I'},
#                                    target_path=tmp_path)
#         content = os.listdir(getattr(res, PDNames.WRITE_ECG_PATH))
#         assert set(content) == expect_content
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg_tar(self, tmp_path):
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().write_ecg(update_keys={'I (Einthoven)': 'I'},
#                                    target_path=tmp_path,
#                                    target_tar='dir.tar.gz')
#         content = list_tar(getattr(res, PDNames.WRITE_ECG_PATH))
#         assert set(content) == expect_content
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg_withoutcompression(self, tmp_path):
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().write_ecg(update_keys={'I (Einthoven)': 'I'},
#                                    target_path=tmp_path,
#                                    target_tar='dir.tar.gz',
#                                    compression=None,)
#         content = list_tar(getattr(res, PDNames.WRITE_ECG_PATH))
#         assert set(content) == expect_content
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg_tar_median(self, tmp_path):
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list,
#                                  info_type='median')
#         res = ecgtable().write_ecg(update_keys={'I (Einthoven)': 'I'},
#                                    target_path=tmp_path,
#                                    target_tar='dir.tar.gz')
#         content = list_tar(getattr(res, PDNames.WRITE_ECG_PATH))
#         assert set(content) == set(
#             [PDNames.FAILED_FILE, PDNames.MEDIAN_FILE])
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_ecg_error(self, tmp_path):
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         with pytest.raises(KeyError):
#             _ = ecgtable().write_ecg(target_path=tmp_path)
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     def test_write_pdf(self, tmp_path):
#         # change current directory
#         os.chdir(tmp_path)
#         # run
#         ecgreader = ECGDICOMReader()
#         ecgdrawing = ECGDrawing(update_keys={'I (Einthoven)': 'I'})
#         ecgtable = ECGDICOMTable(ecgreader, path_list=dicom_path_list)
#         res = ecgtable().write_pdf(ecgdrawing=ecgdrawing)
#         # get content and read in a table
#         content = os.listdir(getattr(res, PDNames.WRITE_ECG_PATH))
#         pdf_count = sum(1 for it in content if '.pdf' in it.lower())
#         assert len(content) == 3
#         assert pdf_count == 2

