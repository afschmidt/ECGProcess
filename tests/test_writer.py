import os
import pytest
import numpy as np
import pandas as pd
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.writer import (
    BaseWriter,
    WriteContext,
    TableWriter,
    NumpyWriter,
    WRITERS,
    register_writer,
    resolve_writer,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# helpers
# NOTE these fakes keep the writer tests independent of `ECGTable`: the
# helper callables that a real `WriteContext` carries as bound `ECGTable`
# methods are replaced by lightweight stubs.

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _fake_write_file_names(chunk_num=None, **kwargs):
    """Stub of ``ECGTable._write_file_names`` with tsv extension logic."""
    ext = '.tsv'
    if kwargs.get('compression') in ('gz', 'gzip'):
        ext = ext + '.gz'
    sep = ''
    chunk = ''
    if chunk_num is not None:
        sep = '_'
        chunk = str(chunk_num)
    return (
        'metadata' + sep + chunk + ext,
        'waveforms' + sep + chunk + ext,
        'medianbeats' + sep + chunk + ext,
        'ecg_data' + sep + chunk + ext,
    )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_context(target, e_meta=True, e_wave=True, e_median=True,
                  chunk_num=None, get_long_table=None):
    """Build a WriteContext backed by inert stub helpers."""
    def _default_long_table(lead_list, signal_type, purge_header=True):
        return pd.DataFrame({'Voltage': [1.0, 2.0],
                             'Signal type': [signal_type, signal_type]})
    return WriteContext(
        e_meta=e_meta,
        e_wave=e_wave,
        e_median=e_median,
        kwargs_tab={},
        key_list=['a', 'b'],
        target=str(target),
        chunk_num=chunk_num,
        write_file_names=_fake_write_file_names,
        get_long_table=get_long_table or _default_long_table,
    )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_array_context(target, e_meta=True, e_wave=True, e_median=True,
                        chunk_num=None):
    """WriteContext whose filename stub yields an `ecg_data.npz` basename."""
    def _npz_names(chunk_num=None, **kwargs):
        sep = '' if chunk_num is None else '_'
        chunk = '' if chunk_num is None else str(chunk_num)
        base = 'ecg_data' + sep + chunk
        return (base, base, base, base + '.npz')
    return WriteContext(
        e_meta=e_meta,
        e_wave=e_wave,
        e_median=e_median,
        kwargs_tab={},
        key_list=['a', 'b'],
        target=str(target),
        chunk_num=chunk_num,
        write_file_names=_npz_names,
        get_long_table=lambda *a, **kw: None,
    )

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestRegistry(object):
    """Testing the writer registry and register_writer decorator."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_table_writer_registered(self):
        assert TabNames.WRITE_TAB in WRITERS
        assert WRITERS[TabNames.WRITE_TAB] is TableWriter
        assert issubclass(TableWriter, BaseWriter)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_register_writer_adds_to_registry(self):
        key = 'unit_test_writer'
        assert key not in WRITERS
        try:
            @register_writer(key)
            class _TmpWriter(BaseWriter):
                def write(self, meta_list, wave_list, median_list, ctx):
                    return None
            assert WRITERS[key] is _TmpWriter
        finally:
            WRITERS.pop(key, None)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_register_writer_rejects_duplicate(self):
        with pytest.raises(ValueError):
            @register_writer(TabNames.WRITE_TAB)
            class _DupWriter(BaseWriter):
                def write(self, meta_list, wave_list, median_list, ctx):
                    return None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_register_writer_rejects_non_basewriter(self):
        assert 'not_a_writer' not in WRITERS
        with pytest.raises(TypeError):
            @register_writer('not_a_writer')
            class _NotAWriter(object):
                def write(self, meta_list, wave_list, median_list, ctx):
                    return None
        assert 'not_a_writer' not in WRITERS

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestWriteContext(object):
    """Testing the WriteContext dataclass."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_construction(self, tmp_path):
        ctx = _make_context(tmp_path, chunk_num=3)
        assert ctx.e_meta is True
        assert ctx.e_wave is True
        assert ctx.e_median is True
        assert ctx.kwargs_tab == {}
        assert ctx.key_list == ['a', 'b']
        assert ctx.target == str(tmp_path)
        assert ctx.chunk_num == 3
        assert callable(ctx.write_file_names)
        assert callable(ctx.get_long_table)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestResolveWriter(object):
    """Testing resolve_writer normalisation."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resolve_subclass(self):
        resolved = resolve_writer(TableWriter)
        assert isinstance(resolved, TableWriter)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resolve_instance(self):
        instance = TableWriter()
        assert resolve_writer(instance) is instance
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resolve_callable(self, tmp_path):
        calls = []
        def _bare_writer(meta_list, wave_list, median_list, ctx):
            calls.append(ctx.target)
        resolved = resolve_writer(_bare_writer)
        assert isinstance(resolved, BaseWriter)
        resolved.write([], [], [], _make_context(tmp_path))
        assert calls == [str(tmp_path)]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resolve_rejects_bad_type(self):
        with pytest.raises(TypeError):
            resolve_writer(42)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestTableWriter(object):
    """
    Unit testing TableWriter.write in isolation from ECGTable, using a
    WriteContext backed by stub helpers. The tab-specific options
    (append/sep/compression) live on the writer instance, mirroring how
    ECGTable.write_ecg configures it.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_writes_all_files(self, tmp_path):
        ctx = _make_context(tmp_path)
        meta_list = [{'age': 50}, {'age': 60}]
        TableWriter(tab_compression=None).write(
            meta_list, ['w1', 'w2'], ['m1', 'm2'], ctx)
        assert set(os.listdir(tmp_path)) == {
            'metadata.tsv', 'waveforms.tsv', 'medianbeats.tsv'}
        meta = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t', index_col=0)
        assert list(meta.index) == ['a', 'b']
        assert meta['age'].tolist() == [50, 60]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_export_flags_gate_output(self, tmp_path):
        ctx = _make_context(tmp_path, e_wave=False, e_median=False)
        TableWriter(tab_compression=None).write(
            [{'age': 50}, {'age': 60}], [], [], ctx)
        assert set(os.listdir(tmp_path)) == {'metadata.tsv'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_long_table_signal_types(self, tmp_path):
        calls = []
        def _record_long_table(lead_list, signal_type, purge_header=True):
            calls.append(signal_type)
            return pd.DataFrame({'Voltage': [1.0]})
        ctx = _make_context(tmp_path, get_long_table=_record_long_table)
        TableWriter(tab_compression=None).write(
            [{'age': 1}, {'age': 2}], ['w'], ['m'], ctx)
        assert calls == [CTypes.WaveForms, CTypes.MedianBeats]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_chunk_and_compression_extension(self, tmp_path):
        # NOTE non-append mode is what honours the chunk suffix; append mode
        # writes a single unsuffixed file.
        ctx = _make_context(tmp_path, chunk_num=2)
        TableWriter(tab_append=False, tab_compression='gzip').write(
            [{'age': 1}, {'age': 2}], ['w'], ['m'], ctx)
        assert set(os.listdir(tmp_path)) == {
            'metadata_2.tsv.gz', 'waveforms_2.tsv.gz',
            'medianbeats_2.tsv.gz'}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNumpyWriter(object):
    """Round-trip and flag-gating tests for the uncompressed .npz writer."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path):
        # a SUBSET of leads (I, II) at equal length 5; absent leads become
        # NaN. This also exercises the subset support in
        # signal_dicts_to_numpy_array.
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50, 'note': 'x'}, {'age': 60, 'note': 'y'}]
        ctx = _make_array_context(tmp_path, e_median=False)
        NumpyWriter().write(meta, wave, [], ctx)
        assert 'ecg_data.npz' in os.listdir(tmp_path)
        assert 'header_metadata.txt' in os.listdir(tmp_path)
        data = np.load(tmp_path / 'ecg_data.npz')
        try:
            # canonical layout is (n_records, 12 leads, signal_length)
            waves = data[CTypes.WaveForms]
            assert waves.shape == (2, 12, 5)
            # present leads carry data; absent leads are NaN
            assert not np.isnan(waves[0, 0]).any()
            assert np.isnan(waves[0, 2]).all()
            # 'note' dropped -> single numeric column
            assert data[CTypes.MetaData].shape == (2, 1)
            assert CTypes.MedianBeats not in data.files
        finally:
            data.close()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flag_gating_single_lead_only(self, tmp_path):
        # a single present lead is valid; the rest are NaN
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = _make_array_context(tmp_path, e_meta=False, e_median=False)
        NumpyWriter().write([], wave, [], ctx)
        data = np.load(tmp_path / 'ecg_data.npz')
        try:
            assert data.files == [CTypes.WaveForms]
            assert data[CTypes.WaveForms].shape == (2, 12, 5)
        finally:
            data.close()
        # no metadata -> no header sidecar
        assert 'header_metadata.txt' not in os.listdir(tmp_path)
