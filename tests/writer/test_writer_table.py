import os
import logging
import pytest
import numpy as np
import pandas as pd
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.writer import (
    TableWriter,
    signal_dicts_to_long_table,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestTableWriter(object):
    """
    Unit testing TableWriter.write in isolation from ECGTable. The
    tab-specific options (append/sep/compression) live on the writer
    instance, mirroring how ECGTable.write_ecg configures it; filenames
    (including the compression suffix) come from the writer itself.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_writes_all_files(self, tmp_path, make_context):
        ctx = make_context(tmp_path)
        meta_list = [{'age': 50}, {'age': 60}]
        wave = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        median = [{'I': np.arange(2.0)}, {'I': np.arange(2.0) + 1}]
        TableWriter(tab_compression=None).write(
            meta_list, wave, median, ctx)
        assert set(os.listdir(tmp_path)) == {
            'metadata.tsv', 'waveforms.tsv', 'medianbeats.tsv'}
        meta = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t', index_col=0)
        assert list(meta.index) == ['a', 'b']
        assert meta['age'].tolist() == [50, 60]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_export_flags_gate_output(self, tmp_path, make_context):
        ctx = make_context(tmp_path, e_wave=False, e_median=False)
        TableWriter(tab_compression=None).write(
            [{'age': 50}, {'age': 60}], [], [], ctx)
        assert set(os.listdir(tmp_path)) == {'metadata.tsv'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_long_table_signal_types(self, tmp_path, make_context):
        # each signal source is written long-format with its own constant
        # 'Signal type' column
        wave = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        median = [{'I': np.arange(2.0)}, {'I': np.arange(2.0) + 1}]
        ctx = make_context(tmp_path)
        TableWriter(tab_compression=None).write(
            [{'age': 1}, {'age': 2}], wave, median, ctx)
        waves = pd.read_csv(tmp_path / 'waveforms.tsv', sep='\t')
        medians = pd.read_csv(tmp_path / 'medianbeats.tsv', sep='\t')
        assert waves['Signal type'].unique().tolist() == [CTypes.WaveForms]
        assert medians['Signal type'].unique().tolist() ==\
            [CTypes.MedianBeats]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_chunk_and_compression_extension(self, tmp_path, make_context):
        # NOTE non-append mode is what honours the chunk suffix; append mode
        # writes a single unsuffixed file.
        wave = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        median = [{'I': np.arange(2.0)}, {'I': np.arange(2.0) + 1}]
        ctx = make_context(tmp_path, chunk_num=2)
        writer = TableWriter(tab_append=False, tab_compression='gzip')
        # the compression suffix is writer-owned via file_ext
        assert writer.file_ext() == '.tsv.gz'
        writer.write([{'age': 1}, {'age': 2}], wave, median, ctx)
        assert set(os.listdir(tmp_path)) == {
            'metadata_2.tsv.gz', 'waveforms_2.tsv.gz',
            'medianbeats_2.tsv.gz'}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestSignalDictsToLongTable(object):
    """
    Unit testing the module-level long-format helper lifted out of
    `ECGTable`: the melt layout, None-signal handling, and the explicit
    `prev_keys` key-consistency contract.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_long_format(self):
        lead_list = [
            {'I': np.array([1.0, 2.0]), 'II': np.array([3.0, 4.0])},
            {'I': np.array([5.0, 6.0]), 'II': np.array([7.0, 8.0])},
        ]
        table = signal_dicts_to_long_table(
            lead_list, key_list=['a', 'b'], signal_type=CTypes.WaveForms)
        assert list(table.columns) == [
            TabNames.KEY, 'Sampling sequence', 'Lead', 'Voltage',
            'Signal type']
        # 2 records x 2 samples x 2 leads
        assert table.shape[0] == 8
        assert table['Signal type'].unique().tolist() == [CTypes.WaveForms]
        rec_a_lead_i = table[
            (table[TabNames.KEY] == 'a') & (table['Lead'] == 'I')]
        assert rec_a_lead_i['Voltage'].tolist() == [1.0, 2.0]
        assert rec_a_lead_i['Sampling sequence'].tolist() == [0, 1]
        rec_b_lead_ii = table[
            (table[TabNames.KEY] == 'b') & (table['Lead'] == 'II')]
        assert rec_b_lead_ii['Voltage'].tolist() == [7.0, 8.0]
        # an empty lead list yields an empty table
        empty = signal_dicts_to_long_table(
            [], key_list=[], signal_type=CTypes.WaveForms)
        assert empty.empty
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_none_signals(self, caplog):
        # a None lead is replaced by an all-NaN array of the record's
        # signal length, with a warning
        lead_list = [{'I': np.arange(3.0), 'II': None}]
        with caplog.at_level(logging.WARNING, logger='ecgprocess.writer'):
            table = signal_dicts_to_long_table(
                lead_list, key_list=['a'], signal_type=CTypes.WaveForms)
        assert len(caplog.records) == 1
        assert table[table['Lead'] == 'II']['Voltage'].isna().all()
        assert table[table['Lead'] == 'I']['Voltage'].notna().all()
        # an all-None record falls back to placeholder length-1 arrays
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger='ecgprocess.writer'):
            table = signal_dicts_to_long_table(
                [{'I': None}], key_list=['a'],
                signal_type=CTypes.WaveForms)
        assert len(caplog.records) == 1
        assert table.shape[0] == 1
        assert table['Voltage'].isna().all()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_errors_and_prev_keys(self):
        # differing signal lengths within a record
        with pytest.raises(ValueError):
            signal_dicts_to_long_table(
                [{'I': np.arange(3.0), 'II': np.arange(4.0)}],
                key_list=['a'], signal_type=CTypes.WaveForms)
        # distinct lead keys between records
        with pytest.raises(KeyError):
            signal_dicts_to_long_table(
                [{'I': np.arange(3.0)}, {'II': np.arange(3.0)}],
                key_list=['a', 'b'], signal_type=CTypes.WaveForms)
        # cross-call key persistence is an explicit parameter: a
        # mismatching prev_keys seed fails the same consistency check
        with pytest.raises(KeyError):
            signal_dicts_to_long_table(
                [{'I': np.arange(3.0)}], key_list=['a'],
                signal_type=CTypes.WaveForms, prev_keys=['II'])
