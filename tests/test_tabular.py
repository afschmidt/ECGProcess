import os
import pytest
import numpy as np
import pandas as pd
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
from typing import Any
from ecgprocess.errors import (
    MissingTagError, XMLValidationError,
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
from ecgprocess.utils.engineering_tools import(
    signal_standardise_res,
)
# from ecgprocess.plot_ecgs import (
#     ECGDrawing,
# )
from ecgprocess.example_data.examples import (
    parsed_config,
    list_dicom_paths,
    list_xml_paths,
)
from ecgprocess.utils.general import (
    list_tar,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CLeads = Core.Leads
CMeta = Core.MetaData
CTypes = Core.DataTypes

# #### Relevant paths
dicom_file_path = list_dicom_paths()['example_dicom_1']
dicom_path_list = [
    list_dicom_paths()['example_dicom_1'],
    list_dicom_paths()['example_dicom_2'],
]
dicom_wrong_list = ['wrong'] + dicom_path_list
xml_file_path = list_xml_paths()['example_1']
xml_schema_path = list_xml_paths()['example_1_schema']
xml_schema_error_path = list_xml_paths()['example_1_schema_error']

# #### parsed config files
parser_dicom = parsed_config()['parsed_dicom1']
parser_xml = parsed_config()['parsed_xml1']
parser_xml2 = parsed_config()['parsed_xml2']

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestTable(object):
    """
    Testing ECGTable
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_init(self):
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
        assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
        assert getattr(ecgtable, TabNames.SCHEMA) is None
        assert getattr(ecgtable, TabNames.ENG_WAVE) == signal_identity
        # testing the different extract parameters
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            extract_meta=False, extract_median=False)
        assert getattr(ecgtable, TabNames.E_MEDIAN) == False
        assert getattr(ecgtable, TabNames.E_WAVE) == True
        # testing with schema
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            schema=xml_schema_path)
        assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
        assert getattr(ecgtable, TabNames.SCHEMA) == xml_schema_path
        assert getattr(ecgtable, TabNames.E_MEDIAN) == True
        # testing the engineer parameters
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            engineer_wave=signal_standardise_res)
        assert getattr(ecgtable, TabNames.ENG_MEDIAN) == signal_identity
        assert getattr(ecgtable, TabNames.ENG_WAVE) == signal_standardise_res
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_call(self):
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
        res = ecgtable()
        assert getattr(ecgtable, TabNames.RPATH_L) == [xml_file_path]
        assert getattr(ecgtable, TabNames.CPATH_L) == [xml_file_path]
        assert len(getattr(ecgtable, TabNames.FPATH_L)) == 0
        # including incorrect paths
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_wrong_list)
        res = ecgtable()
        assert getattr(ecgtable, TabNames.RPATH_L) == dicom_wrong_list
        assert getattr(ecgtable, TabNames.CPATH_L) == dicom_path_list
        assert len(getattr(ecgtable, TabNames.FPATH_L)) == 1
        assert getattr(res, TabNames.SKIP_DATA) == False
        assert getattr(res, TabNames.SKIP_INVALID) == False
        # getting warnings
        ecgtable = ECGTable(ecgreader, path_list=dicom_wrong_list)
        with pytest.warns(UserWarning):
            res = ecgtable(verbose=True)
        # getting errors
        with pytest.raises(PermissionError):
            res = ecgtable(ignore_permission=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_loop_table_default(self):
        # without validation
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path])
        res = ecgtable()
        meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
                                             parsed_config=parser_xml)
        assert len(median) != 0
        assert len(meta[0][CMeta.UID]) > 0
        assert meta[0][CMeta.NLEADS] == 12
        assert len(wave[0][CLeads.I]) > 0
        # excluding medianbeats and waveforms
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            extract_median=False, extract_wave=False,)
        res = ecgtable()
        meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
                                             parsed_config=parser_xml)
        assert len(median) == 0
        assert len(wave) == 0
        assert getattr(res, TabNames.KEY_L)[0] == meta[0][CMeta.UID]
        # unique False, with the config ommit the UID
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            extract_median=False, extract_wave=False,)
        res = ecgtable()
        meta, wave, median = res._loop_table(getattr(res, TabNames.CPATH_L),
                                             parsed_config=parser_xml2,
                                             unique=False,)
        assert meta[0][CMeta.UID] is None
        assert getattr(res, TabNames.KEY_L) == ['1']
        # kwargs to reader call, setting skip_root to false results
        # in no data being extracted because the config files does not match
        # anymore. Adjusting the reader to deal with this lack of key data.
        ecgreader = ECGXMLReader(resample_500=False)
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path], )
        res = ecgtable()
        meta, wave, median = res._loop_table(
            getattr(res, TabNames.CPATH_L), parsed_config=parser_xml,
            unique=False, kwargs_reader_call={'skip_root':False},
        )
        # assert (m is None for m in meta[0].values())
        assert all(m is None for m in wave[0].values())
        assert all(m is None for m in median[0].values())
        # kwargs to reader extract, setting skip_empty to False
        # will raise a reader error.
        ecgreader = ECGXMLReader(resample_500=False)
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],)
        res = ecgtable()
        with pytest.raises(MissingTagError):
            res._loop_table(
                getattr(res, TabNames.CPATH_L), parsed_config=parser_xml,
                kwargs_reader_extract={'skip_empty':False},
            )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_loop_table_xml(self):
        # using an XML schema
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            schema=xml_schema_path,)
        res = ecgtable()
        meta, wave, median = res._loop_table(
            getattr(res, TabNames.CPATH_L),
            parsed_config=parser_xml,
        )
        assert len(median) != 0
        assert len(meta[0][CMeta.UID]) > 0
        assert meta[0][CMeta.NLEADS] == 12
        assert len(wave[0][CLeads.I]) > 0
        # causing in invalidation error
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            schema=xml_schema_error_path,)
        res = ecgtable()
        with pytest.raises(XMLValidationError):
            res._loop_table(
                getattr(res, TabNames.CPATH_L),
                parsed_config=parser_xml,
            )
        # ignoring the error
        ecgreader = ECGXMLReader()
        ecgtable = ECGTable(ecgreader, path_list=[xml_file_path],
                            schema=xml_schema_error_path,)
        res = ecgtable(ignore_invalid=True)
        meta, wave, median = res._loop_table(
            getattr(res, TabNames.CPATH_L),
            parsed_config=parser_xml,
        )
        assert meta == wave == median == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_loop_table_engineer_func(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=[dicom_file_path],
                            engineer_wave=signal_standardise_res,
                            )
        res = ecgtable()
        _, wave, _ = res._loop_table(
            getattr(res, TabNames.CPATH_L),
            parsed_config=parser_dicom,
        )
        assert np.round(wave[0]['I'][2], 1) == 30.0
        assert wave[0]['I'][2] != 29.28, 'still has the orignal value'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_get_table(self):
        # testing with unique true
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        table = ecgtable().get_table(parsed_config=parser_dicom,)
        assert getattr(table, CTypes.MetaData).shape[1] > 10
        assert getattr(table, CTypes.WaveForms).shape[1] == 5
        assert getattr(table, CTypes.MedianBeats).shape[0] > 600
        # unique false
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        table = ecgtable().get_table(parsed_config=parser_dicom,
                                     unique=False)
        assert getattr(table, CTypes.MetaData)['key'].to_list() == ['1', '2']
        assert getattr(table, CTypes.WaveForms)['key'].unique().tolist() ==\
            ['1', '2']
        assert getattr(table, CTypes.MedianBeats)['key'].unique().tolist() ==\
            ['1', '2']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg(self, tmp_path):
        expected_content = ['waveforms.tsv.gz', 'medianbeats.tsv.gz',
                              'metadata.tsv.gz', 'FailedFiles.txt']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(parsed_config=parser_dicom)
        # get content and read in a table
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        table = pd.read_csv(os.path.join(getattr(res, TabNames.WRITE_ECG_PATH),
                                         expected_content[2]),
                            sep='\t', index_col=0,
                            )
        wave = pd.read_csv(os.path.join(getattr(res, TabNames.WRITE_ECG_PATH),
                                         expected_content[1]),
                            sep='\t', index_col=0,
                            )
        assert set(content) == set(expected_content)
        assert table.shape[0] == 2
        assert table.shape[1] > 10
        assert wave.shape[1] > 4
        assert wave.shape[0] > 1000
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_no_append(self, tmp_path):
        expected_content = ['waveforms.tsv.gz', 'medianbeats.tsv.gz',
                              'metadata.tsv.gz', 'FailedFiles.txt']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, tab_append=False,)
        # get content and read in a table
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        table = pd.read_csv(os.path.join(getattr(res, TabNames.WRITE_ECG_PATH),
                                         expected_content[2]),
                            sep='\t', index_col=0,
                            )
        wave = pd.read_csv(os.path.join(getattr(res, TabNames.WRITE_ECG_PATH),
                                         expected_content[1]),
                            sep='\t', index_col=0,
                            )
        assert set(content) == set(expected_content)
        assert table.shape[0] == 2
        assert table.shape[1] > 10
        assert wave.shape[1] > 4
        assert wave.shape[0] > 1000
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_chunk(self, tmp_path):
        expected_content = [
            'waveforms_2.tsv.gz', 'medianbeats_2.tsv.gz',
            'medianbeats_1.tsv.gz', 'waveforms_1.tsv.gz',
            'metadata_2.tsv.gz', 'FailedFiles.txt',
            'metadata_1.tsv.gz']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, tab_append=False,
            chunk=1,
        )
        # get content and read in a table
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        assert set(content) == set(expected_content)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_numpy(self, tmp_path):
        expected_content = ['ecg_data.npz', 'FailedFiles.txt',
                            'header_metadata.txt']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, file_type='numpy')
        # get content and read in a table
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        with np.load(expected_content[0]) as data:
            meta = data[CTypes.MetaData]
            wave = data[CTypes.WaveForms]
            median = data[CTypes.MedianBeats]
        # getting the header as well.
        header = pd.read_csv(
            os.path.join(getattr(res, TabNames.WRITE_ECG_PATH),
                         'header_metadata.txt'),
            sep='\t', index_col=0,
                            )
        assert header.shape[0] > 10
        assert set(content) == set(expected_content)
        assert meta.shape[0] == 2
        assert wave.shape == (2, 12, 5000)
        assert median.shape == (2, 12, 600)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_tfrecords(self, tmp_path):
        expected_content = ['ecg_data.tfrecord', 'FailedFiles.txt',
                            'header_metadata.txt']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, file_type='tensorflow')
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        # #### Not inspeting the tensorflow files directly - to fidly at the
        # moment .
        assert set(content) == set(expected_content)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_tar(self, tmp_path):
        expected_content = ['waveforms.tsv.gz', 'medianbeats.tsv.gz',
                              'metadata.tsv.gz', 'FailedFiles.txt']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(parsed_config=parser_dicom,
                                                target_tar='dir.tar.gz')
        # get content and read in a table
        content = list_tar(getattr(res, TabNames.WRITE_ECG_PATH))
        assert set(content) == set(expected_content)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_wo_compression(self, tmp_path):
        expected_content = ['chunkrecord.txt', 'waveforms.tsv',
                            'medianbeats.tsv', 'metadata.tsv']
        # change current directory
        os.chdir(tmp_path)
        # run
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,)
        res = ecgtable(verbose=False).write_ecg(parsed_config=parser_dicom,
                                                tab_compression=None,
                                                write_failed=False,
                                                write_chunk_record=True,
                                                )
        # get content and read in a table
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        assert set(content) == set(expected_content)
