import logging
import os
import pytest
import numpy as np
import pandas as pd
import pydicom
from ecgprocess.errors import (
    MissingTagError, XMLValidationError,
    InputValidationError,
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
from ecgprocess.plot_ecgs import (
    ECGStyle,
)
from ecgprocess.writer import (
    FigureWriter,
)
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

# #### remove waveform and use this in a fixture
def remove_waveform(in_path, out_path):
    ds = pydicom.dcmread(in_path)
    if "WaveformSequence" in ds:
        del ds.WaveformSequence
    ds.save_as(out_path)

@pytest.fixture
def dicom_no_waveform(tmp_path):
    """
    Reads dicom file and removes the waveforms from the second one.
    """
    # Adjust these paths as necessary for your local setup
    first_path = dicom_path_list[0]
    second_path = dicom_path_list[1]
    out_path = tmp_path / "second_no_waveform.dcm"
    remove_waveform(second_path, out_path)
    return [first_path, str(out_path)]

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
        # getting errors
        with pytest.raises(PermissionError):
            res = ecgtable(ignore_permission=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_call_logging(self, caplog):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_wrong_list)
        with caplog.at_level(logging.WARNING, logger='ecgprocess.tabular'):
            ecgtable()
        assert len(caplog.records) > 0
        caplog.clear()
        with caplog.at_level(logging.ERROR, logger='ecgprocess.tabular'):
            ecgtable()
        assert len(caplog.records) == 0
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
        # unique False, with the config omit the UID
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
        assert wave[0]['I'][2] != 29.28, 'still has the original value'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_loop_table_confirm(self, dicom_no_waveform):
        dicom_path_list_no_wave = dicom_no_waveform
        ecgreader = ECGDICOMReader(resample_500=False)
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list_no_wave,
                            )
        res = ecgtable(confirm_median=True, confirm_wave=True)
        meta, wave, median = res._loop_table(
            getattr(res, TabNames.CPATH_L),
            parsed_config=parser_dicom,
        )
        # confirming only one file is extracted
        assert len(meta) == len(median) == len(wave) == 1
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
        # run; numpy/tfrecord writers require equal-length records, so
        # opt in to the new pad/truncate.
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            signal_length_w=5000, signal_length_m=600)
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
    def test_write_ecg_npy(self, tmp_path):
        expected_content = ['metadata.npy', 'waveforms.npy',
                            'medianbeats.npy', 'FailedFiles.txt',
                            'header_metadata.txt']
        # change current directory
        os.chdir(tmp_path)
        # run; array writers require equal-length records, so opt in to
        # the pad/truncate.
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            signal_length_w=5000, signal_length_m=600)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, file_type='npy')
        # one .npy per source plus the sidecar
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        assert set(content) == set(expected_content)
        # signal arrays are float32 and memory-mappable
        wave = np.load('waveforms.npy', mmap_mode='r')
        assert wave.shape == (2, 12, 5000)
        assert wave.dtype == np.float32
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_ecg_figure(self, tmp_path):
        # change current directory
        os.chdir(tmp_path)
        # run; the default layout renders the clinical 3x4 grid with a
        # rhythm strip, one image per record named by UID. The writer
        # renders a single source, so median extraction is disabled.
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            extract_median=False)
        writer = FigureWriter(
            kwargs_call={'style': ECGStyle(figsize=(4., 2.), dpi=50)})
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, writer=writer)
        # one valid PNG per record
        target = getattr(res, TabNames.WRITE_ECG_PATH)
        pngs = [c for c in os.listdir(target) if c.endswith('.png')]
        assert len(pngs) == 2
        for p in pngs:
            with open(os.path.join(target, p), 'rb') as fh:
                assert fh.read(8) == b'\x89PNG\r\n\x1a\n'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.tensorflow
    def test_write_ecg_tfrecords(self, tmp_path):
        expected_content = ['ecg_data.tfrecord', 'FailedFiles.txt',
                            'header_metadata.txt']
        # change current directory
        os.chdir(tmp_path)
        # run; numpy/tfrecord writers require equal-length records, so
        # opt in to the new pad/truncate.
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            signal_length_w=5000, signal_length_m=600)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, file_type='tensorflow')
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        # #### Not inspeting the tensorflow files directly - to fidly at the
        # moment .
        assert set(content) == set(expected_content)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.wfdb
    def test_write_ecg_wfdb(self, tmp_path):
        # change current directory
        os.chdir(tmp_path)
        # run; a WFDB record is single-source, so median extraction is
        # disabled (mirrors test_write_ecg_figure). resample_500 defaults
        # to True on ECGDICOMReader, populating the processed-rate
        # metadata WFDBWriter requires.
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            extract_median=False)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, writer='wfdb')
        target = getattr(res, TabNames.WRITE_ECG_PATH)
        content = os.listdir(target)
        hea_files = sorted(c for c in content if c.endswith('.hea'))
        assert len(hea_files) == 2
        assert all(c.replace('.hea', '.dat') in content for c in hea_files)
        # round-trip the first record
        import wfdb
        record = wfdb.rdrecord(os.path.join(target, hea_files[0][:-4]))
        assert record.fs == 500
        assert record.units == ['mV'] * len(record.sig_name)
        assert record.comments[0].startswith('UID: ')
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestPadTruncate(object):
    """
    Unit tests for the opt-in pad/truncate feature on ``ECGTable``.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_init(self):
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            signal_length_w=2500, signal_length_m=600,
                            pad_value=-1.0)
        assert getattr(ecgtable, TabNames.SIG_LEN_W) == 2500
        assert getattr(ecgtable, TabNames.SIG_LEN_M) == 600
        assert getattr(ecgtable, TabNames.PAD_VALUE) == -1.0
        with pytest.raises(InputValidationError):
            ECGTable(ecgreader, path_list=dicom_path_list,
                     signal_length_w=0)
        with pytest.raises(InputValidationError):
            ECGTable(ecgreader, path_list=dicom_path_list,
                     signal_length_m=-1)
        with pytest.raises(InputValidationError):
            ECGTable(ecgreader, path_list=dicom_path_list,
                     signal_length_w='oops')
        with pytest.raises(InputValidationError):
            ECGTable(ecgreader, path_list=dicom_path_list,
                     pad_value='oops')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_pad_or_truncate(self):
        ecgtable = ECGTable(ECGDICOMReader(), path_list=dicom_path_list)
        signals = {'I': np.array([1.0, 2.0, 3.0], dtype=np.float64),
                   'II': np.arange(10, dtype=np.int32),
                   'III': None}
        out = ecgtable._pad_or_truncate(signals, target_length=5,
                                        pad_value=-9.0)
        np.testing.assert_array_equal(
            out['I'], np.array([1.0, 2.0, 3.0, -9.0, -9.0]))
        np.testing.assert_array_equal(out['II'], np.arange(5))
        assert out['II'].dtype == np.int32
        assert out['III'] is None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestWriteEcgDispatch(object):
    """
    Testing the ECGTable.write_ecg dispatch: the per-call custom writer=
    hook, and the deprecated file_type overruling writer.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_writer_argument_routes(self, tmp_path):
        os.chdir(tmp_path)
        records = {}
        def _recording_writer(meta_list, wave_list, median_list, ctx):
            records['n_meta'] = len(meta_list)
            records['target'] = ctx.target
            with open(os.path.join(ctx.target, 'marker.txt'), 'w') as fh:
                fh.write('written')
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list)
        res = ecgtable(verbose=False).write_ecg(
            parsed_config=parser_dicom, writer=_recording_writer)
        assert records['n_meta'] == 2
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        assert 'marker.txt' in content
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_file_type_overrules_writer(self, tmp_path):
        # NOTE when both are supplied the deprecated file_type wins and a
        # DeprecationWarning is emitted; the custom writer is not called.
        os.chdir(tmp_path)
        records = {}
        def _recording_writer(meta_list, wave_list, median_list, ctx):
            records['called'] = True
            with open(os.path.join(ctx.target, 'marker.txt'), 'w') as fh:
                fh.write('written')
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list)
        with pytest.warns(DeprecationWarning):
            res = ecgtable(verbose=False).write_ecg(
                parsed_config=parser_dicom,
                writer=_recording_writer, file_type='table')
        content = os.listdir(getattr(res, TabNames.WRITE_ECG_PATH))
        assert 'called' not in records
        assert 'marker.txt' not in content
        assert 'metadata.tsv.gz' in content

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestWriteEcgAnnotateFailures(object):
    """
    Testing that write-stage annotation failures follow the ignore_data
    flag: raising by default, or skipping the record and adding it to
    FailedFiles.txt when ignore_data is set.
    """
    # a template referencing a key absent from the example metadata
    _SPEC_ABSENT = [{'text': '{absent key}', 'xy': (0.5, 0.99)}]
    _SMALL_STYLE = ECGStyle(figsize=(4., 2.), dpi=40)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_annotation_failure_raises_by_default(self, tmp_path):
        os.chdir(tmp_path)
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            extract_median=False)
        writer = FigureWriter(
            annotate=self._SPEC_ABSENT,
            kwargs_call={'style': self._SMALL_STYLE})
        with pytest.raises(InputValidationError, match='absent key'):
            ecgtable(verbose=False).write_ecg(
                parsed_config=parser_dicom, writer=writer)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_annotation_failure_recorded_with_ignore_data(self, tmp_path):
        os.chdir(tmp_path)
        ecgreader = ECGDICOMReader()
        ecgtable = ECGTable(ecgreader, path_list=dicom_path_list,
                            extract_median=False)
        writer = FigureWriter(
            annotate=self._SPEC_ABSENT,
            kwargs_call={'style': self._SMALL_STYLE})
        res = ecgtable(verbose=False, ignore_data=True).write_ecg(
            parsed_config=parser_dicom, writer=writer)
        target = getattr(res, TabNames.WRITE_ECG_PATH)
        content = os.listdir(target)
        # every record fails the annotation: no images are written but
        # both failures land in FailedFiles.txt with the write-stage cause
        assert not any(c.endswith('.png') for c in content)
        assert 'FailedFiles.txt' in content
        with open(os.path.join(target, 'FailedFiles.txt')) as fh:
            rows = [r for r in fh.read().splitlines() if r]
        assert len(rows) == 2
        assert all('Annotation failed' in r for r in rows)
        assert all('absent key' in r for r in rows)
