import os
import sys
import logging
import subprocess
import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import Error_MSG, InputValidationError
from ecgprocess.plot_ecgs import ECGDrawing, ECGStyle
from ecgprocess.writer import (
    BaseWriter,
    WriteContext,
    TableWriter,
    NumpyWriter,
    NpzWriter,
    NpyWriter,
    TFRecordWriter,
    FigureWriter,
    PixelWriter,
    WRITERS,
    register_writer,
    resolve_writer,
    signal_dicts_to_long_table,
    validate_writer,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes
CMeta = Core.MetaData

# the 12 standard leads in clinical column order
_LEADS_12 = [
    'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6',
]
# the PNG file signature (first 8 bytes of any valid PNG)
_PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
# a small render style keeping the figure tests fast
_SMALL_STYLE = ECGStyle(figsize=(4., 2.), dpi=40)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# helpers
# NOTE writers own their filenames (`BaseWriter.file_names`), so the
# context needs no ECGTable-bound helpers and the writer tests stay
# independent of `ECGTable`.

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_context(target, e_meta=True, e_wave=True, e_median=True,
                  chunk_num=None, skip_data=False):
    """Build a WriteContext for two records keyed 'a' and 'b'."""
    return WriteContext(
        e_meta=e_meta,
        e_wave=e_wave,
        e_median=e_median,
        key_list=['a', 'b'],
        target=str(target),
        chunk_num=chunk_num,
        skip_data=skip_data,
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
        assert ctx.key_list == ['a', 'b']
        assert ctx.target == str(tmp_path)
        assert ctx.chunk_num == 3
        assert ctx.skip_data is False
        assert ctx.failed_records == []

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
class TestValidateWriter(object):
    """
    Testing the validate_writer pre-flight compliance check: pass cases
    (class and instance parity, flexible signatures, inherited write),
    the input gate, the class/instance instantiation asymmetry, and the
    collected single-raise multi-violation report.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_compliant_writers_pass(self):
        class _Good(BaseWriter):
            FILE_EXT = '.json'
            def write(self, meta_list, wave_list, median_list, ctx):
                return None
        class _Variadic(BaseWriter):
            def write(self, *args, **kwargs):
                return None
        # the numpy-family base implements write; a subclass only
        # supplying _save satisfies the contract via inheritance
        class _MiniNpy(NumpyWriter):
            FILE_EXT = '.npy'
            def _save(self, res_dict, ctx):
                return None
        # class and instance forms both pass silently
        assert validate_writer(_Good) is None
        assert validate_writer(_Good()) is None
        assert validate_writer(_Variadic) is None
        assert validate_writer(_MiniNpy) is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_rejects_non_writers(self):
        # objects, registry strings, and bare callables are not the
        # documented subclass/instance forms
        def _bare(meta_list, wave_list, median_list, ctx):
            return None
        for bad in (42, 'npy', _bare):
            with pytest.raises(InputValidationError) as err:
                validate_writer(bad)
            assert Error_MSG.WRITER_NOT_WRITER.format(bad) in str(err.value)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_contract_violations(self):
        # an abstract write and an unbindable write are both caught
        class _NoArgs(BaseWriter):
            def write(self):
                return None
        with pytest.raises(InputValidationError) as err:
            validate_writer(BaseWriter)
        assert Error_MSG.WRITER_ABSTRACT.format('write') in str(err.value)
        with pytest.raises(InputValidationError) as err:
            validate_writer(_NoArgs)
        assert Error_MSG.WRITER_SIGNATURE.split('{')[0] in str(err.value)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_init_args(self):
        class _NeedsArg(BaseWriter):
            def __init__(self, path):
                self.path = path
            def write(self, meta_list, wave_list, median_list, ctx):
                return None
        # the class route requires bare instantiation and fails
        with pytest.raises(InputValidationError) as err:
            validate_writer(_NeedsArg)
        assert Error_MSG.WRITER_INIT.split('{')[0] in str(err.value)
        # a pre-built instance skips the instantiation check and passes
        assert validate_writer(_NeedsArg('out.txt')) is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_multi_violation_single_raise(self):
        # one raise lists every violation: bad signature, missing dot
        # on FILE_EXT, and a wrong-length file_names tuple
        class _Broken(BaseWriter):
            FILE_EXT = 'json'
            def file_names(self, chunk_num=None):
                return ('a', 'b', 'c')
            def write(self):
                return None
        with pytest.raises(InputValidationError) as err:
            validate_writer(_Broken)
        message = str(err.value)
        assert Error_MSG.WRITER_SIGNATURE.split('{')[0] in message
        assert Error_MSG.WRITER_FILE_EXT_DOT.format('json') in message
        assert Error_MSG.WRITER_NAMES_LEN.format(3) in message

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestTableWriter(object):
    """
    Unit testing TableWriter.write in isolation from ECGTable. The
    tab-specific options (append/sep/compression) live on the writer
    instance, mirroring how ECGTable.write_ecg configures it; filenames
    (including the compression suffix) come from the writer itself.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_writes_all_files(self, tmp_path):
        ctx = _make_context(tmp_path)
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
    def test_export_flags_gate_output(self, tmp_path):
        ctx = _make_context(tmp_path, e_wave=False, e_median=False)
        TableWriter(tab_compression=None).write(
            [{'age': 50}, {'age': 60}], [], [], ctx)
        assert set(os.listdir(tmp_path)) == {'metadata.tsv'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_long_table_signal_types(self, tmp_path):
        # each signal source is written long-format with its own constant
        # 'Signal type' column
        wave = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        median = [{'I': np.arange(2.0)}, {'I': np.arange(2.0) + 1}]
        ctx = _make_context(tmp_path)
        TableWriter(tab_compression=None).write(
            [{'age': 1}, {'age': 2}], wave, median, ctx)
        waves = pd.read_csv(tmp_path / 'waveforms.tsv', sep='\t')
        medians = pd.read_csv(tmp_path / 'medianbeats.tsv', sep='\t')
        assert waves['Signal type'].unique().tolist() == [CTypes.WaveForms]
        assert medians['Signal type'].unique().tolist() ==\
            [CTypes.MedianBeats]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_chunk_and_compression_extension(self, tmp_path):
        # NOTE non-append mode is what honours the chunk suffix; append mode
        # writes a single unsuffixed file.
        wave = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        median = [{'I': np.arange(2.0)}, {'I': np.arange(2.0) + 1}]
        ctx = _make_context(tmp_path, chunk_num=2)
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNumpyWriterBase(object):
    """Testing the abstract numpy-family base class contract."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_base_is_abstract_and_unregistered(self):
        # the base cannot be instantiated (abstract _save); only its
        # concrete subclasses are registered under a file_type key
        with pytest.raises(TypeError):
            NumpyWriter()
        assert NumpyWriter not in WRITERS.values()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNpzWriter(object):
    """Round-trip and flag-gating tests for the uncompressed .npz writer."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered_under_npz_only(self):
        # 'npz' is the canonical registry key; the legacy 'numpy' alias
        # lives in the deprecated file_type path, not the registry
        assert WRITERS[TabNames.WRITE_NPZ] is NpzWriter
        assert TabNames.WRITE_NUMPY not in WRITERS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path):
        # a SUBSET of leads (I, II) at equal length 5; absent leads become
        # NaN. This also exercises the subset support in
        # signal_dicts_to_numpy_array.
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50, 'note': 'x'}, {'age': 60, 'note': 'y'}]
        ctx = _make_context(tmp_path, e_median=False)
        NpzWriter().write(meta, wave, [], ctx)
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
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        NpzWriter().write([], wave, [], ctx)
        data = np.load(tmp_path / 'ecg_data.npz')
        try:
            assert data.files == [CTypes.WaveForms]
            assert data[CTypes.WaveForms].shape == (2, 12, 5)
        finally:
            data.close()
        # no metadata -> no header sidecar
        assert 'header_metadata.txt' not in os.listdir(tmp_path)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestNpyWriter(object):
    """
    Round-trip and flag-gating tests for the per-array `.npy` writer: one
    `.npy` file per enabled source per chunk, memory-mappable, float32
    signals, plus the metadata header sidecar.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered(self):
        assert TabNames.WRITE_NPY in WRITERS
        # NOTE will remove on refactor - deprecated.
        assert WRITERS[TabNames.WRITE_NPY] is NpyWriter
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path):
        # a SUBSET of leads (I, II) at equal length 5; absent leads are NaN
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        median = [{'I': np.arange(3.0)}, {'I': np.arange(3.0) + 1}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50, 'note': 'x'}, {'age': 60, 'note': 'y'}]
        ctx = _make_context(tmp_path)
        NpyWriter().write(meta, wave, median, ctx)
        # #### one file per source plus the metadata header sidecar
        assert set(os.listdir(tmp_path)) == {
            'metadata.npy', 'waveforms.npy', 'medianbeats.npy',
            'header_metadata.txt'}
        # #### signals: canonical layout, float32, memory-mappable
        waves = np.load(tmp_path / 'waveforms.npy', mmap_mode='r')
        assert waves.shape == (2, 12, 5)
        assert waves.dtype == np.float32
        np.testing.assert_allclose(waves[0, 0], np.arange(5.0))
        np.testing.assert_allclose(waves[1, 1], np.arange(5.0) + 3)
        # present leads carry data; absent leads are NaN
        assert np.isnan(waves[0, 2]).all()
        medians = np.load(tmp_path / 'medianbeats.npy', mmap_mode='r')
        assert medians.shape == (2, 12, 3)
        assert medians.dtype == np.float32
        # #### metadata: 'note' dropped -> single numeric column
        metadata = np.load(tmp_path / 'metadata.npy', mmap_mode='r')
        assert metadata.shape == (2, 1)
        np.testing.assert_allclose(metadata[:, 0], [50, 60])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_chunk_suffix(self, tmp_path):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = _make_context(tmp_path, e_meta=False, e_median=False,
                            chunk_num=2)
        NpyWriter().write([], wave, [], ctx)
        assert os.listdir(tmp_path) == ['waveforms_2.npy']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flag_gating(self, tmp_path):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        NpyWriter().write([], wave, [], ctx)
        # only the enabled source is written; no metadata -> no sidecar
        assert os.listdir(tmp_path) == ['waveforms.npy']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_custom_dtype(self, tmp_path):
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        NpyWriter(dtype=np.float64).write([], wave, [], ctx)
        assert np.load(tmp_path / 'waveforms.npy').dtype == np.float64

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_figure_records(leads, n=2, length=100):
    """Signal dicts for `leads` plus metadata carrying the sampling rate."""
    rng = np.random.default_rng(7)
    sig_list = [
        {lead: rng.standard_normal(length) for lead in leads}
        for _ in range(n)
    ]
    meta_list = [{CMeta.SF: 100.0} for _ in range(n)]
    return meta_list, sig_list

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestFigureWriter(object):
    """
    Testing the plotting-specific behaviour of the per-record image
    writer: the default clinical layout (3x4 grid plus full-width
    rhythm strip), per-UID image files, format selection, source
    selection, and figure cleanup.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default_mapper(self):
        # the built-in layout is the clinical 3x4 grid, column order
        # (I II III) (aVR aVL aVF) (V1 V2 V3) (V4 V5 V6), plus a
        # full-width lead II rhythm strip on its own bottom row
        mapper = FigureWriter.DEFAULT_MAPPER
        assert mapper['I'] == (0, slice(0, 1))
        assert mapper['II'] == (1, slice(0, 1))
        assert mapper['aVR'] == (0, slice(1, 2))
        assert mapper['V6'] == (2, slice(3, 4))
        assert mapper['II strip'] == (3, slice(0, 4))
        assert len(mapper) == 13
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_one_png_per_uid(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        FigureWriter(kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
        for name in ('a.png', 'b.png'):
            with open(tmp_path / name, 'rb') as fh:
                assert fh.read(8) == _PNG_MAGIC
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_image_format_svg(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        FigureWriter(image_format='svg',
                     kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.svg', 'b.svg'}
        with open(tmp_path / 'a.svg') as fh:
            assert '<svg' in fh.read(1024)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_dual_source_raises(self, tmp_path):
        # the writer renders exactly one source; extracting both would
        # silently drop one and collide on the <UID> filenames
        meta, wave = _make_figure_records(['I'])
        _, median = _make_figure_records(['I'], length=60)
        ctx = _make_context(tmp_path)
        with pytest.raises(InputValidationError):
            FigureWriter().write(meta, wave, median, ctx)
        # fail-fast: nothing is written
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_median_source(self, tmp_path):
        # a median beat is a single short beat; tiling would slice it
        # into meaningless column windows, so tile_x is disabled
        meta, median = _make_figure_records(_LEADS_12, length=60)
        ctx = _make_context(tmp_path, e_wave=False)
        FigureWriter(source='median', tile_x=False,
                     kwargs_call={'style': _SMALL_STYLE}).write(
            meta, [], median, ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_figures_closed_after_write(self, tmp_path):
        open_before = plt.get_fignums()
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        FigureWriter(kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert plt.get_fignums() == open_before

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestFigureWriterAnnotate(object):
    """
    Testing the metadata-driven annotation option: per-record template
    resolution, the metadata-extraction guard, and the skip-and-record
    error path governed by `ctx.skip_data`.
    """
    # a literal annotation needing no metadata
    _SPEC_LIT = [{'text': 'HELLOMARK', 'xy': (0.5, 0.99)}]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_bad_spec_raises_at_init(self):
        # a malformed spec is systematic; it must fail at construction,
        # not mid-batch
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=[{'xy': (0.5, 0.5)}])
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=[{'text': 'x', 'xy': (0.5,)}])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_annotate_forwarded_per_record(self, tmp_path, monkeypatch):
        calls = []
        original = ECGDrawing.annotate
        def _spy(self, annotations):
            calls.append(annotations)
            return original(self, annotations)
        monkeypatch.setattr(ECGDrawing, 'annotate', _spy)
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        FigureWriter(annotate=self._SPEC_LIT,
                     kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert calls == [self._SPEC_LIT, self._SPEC_LIT]
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_template_resolves_per_record(self, tmp_path):
        # svg keeps text as text (with fonttype 'none'), so the resolved
        # per-record annotation is observable in the output file
        meta, wave = _make_figure_records(_LEADS_12)
        meta[0][CMeta.UID] = 'rec1'
        meta[1][CMeta.UID] = 'rec2'
        spec = [{'text': 'ECG {' + CMeta.UID + '}', 'xy': (0.5, 0.99)}]
        ctx = _make_context(tmp_path, e_median=False)
        with plt.rc_context({'svg.fonttype': 'none'}):
            FigureWriter(annotate=spec, image_format='svg',
                         kwargs_call={'style': _SMALL_STYLE}).write(
                meta, wave, [], ctx)
        with open(tmp_path / 'a.svg') as fh:
            assert 'ECG rec1' in fh.read()
        with open(tmp_path / 'b.svg') as fh:
            assert 'ECG rec2' in fh.read()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_template_needs_meta_guard(self, tmp_path):
        # a template without extracted metadata is a configuration
        # error: fail before any file is written
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        spec = [{'text': '{' + CMeta.UID + '}', 'xy': (0.5, 0.5)}]
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=spec,
                         kwargs_call={'style': _SMALL_STYLE}).write(
                meta, wave, [], ctx)
        assert os.listdir(tmp_path) == []
        # literal annotations do not need metadata; without extracted
        # metadata the sampling rate must be supplied explicitly
        FigureWriter(annotate=self._SPEC_LIT,
                     kwargs_call={'style': _SMALL_STYLE,
                                  'sampling_rate': 100.0}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_key_raises_with_uid(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        spec = [{'text': '{absent}', 'xy': (0.5, 0.5)}]
        with pytest.raises(InputValidationError, match="record 'a'"):
            FigureWriter(annotate=spec,
                         kwargs_call={'style': _SMALL_STYLE}).write(
                meta, wave, [], ctx)
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_skip_data_records_failure(self, tmp_path):
        # only record 'b' carries the referenced key; with skip_data the
        # failing record is skipped, recorded, and the batch continues
        open_before = plt.get_fignums()
        meta, wave = _make_figure_records(_LEADS_12)
        meta[1]['extra'] = 'X'
        spec = [{'text': '{extra}', 'xy': (0.5, 0.5)}]
        ctx = _make_context(tmp_path, e_median=False, skip_data=True)
        FigureWriter(annotate=spec,
                     kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'b.png'}
        assert len(ctx.failed_records) == 1
        uid, cause = ctx.failed_records[0]
        assert uid == 'a'
        assert 'Annotation failed' in cause
        assert plt.get_fignums() == open_before

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestPixelWriter(object):
    """
    Testing the pixel-tensor writer: NHWC stacking, channel variants,
    dtype casting, metadata row alignment, and the uniform-size guard.
    """
    # the expected canvas size: _SMALL_STYLE figsize (4, 2) at dpi 40
    _H, _W = 80, 160
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered(self):
        assert WRITERS[TabNames.WRITE_PIXEL] is PixelWriter
        assert issubclass(PixelWriter, FigureWriter)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_stacked_tensor_and_metadata(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_median=False)
        PixelWriter(kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'figures.npy', 'metadata.tsv'}
        stack = np.load(tmp_path / 'figures.npy')
        # one NHWC slice per record, RGBA by default, float32 by default
        assert stack.shape == (2, self._H, self._W, 4)
        assert stack.dtype == np.float32
        # rows align with the tensor slices, UIDs as index
        meta_tab = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t',
                               index_col=0)
        assert list(meta_tab.index) == ['a', 'b']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_channel_variants(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        for channels, depth in (('rgb', 3), ('gray', 1)):
            out = tmp_path / channels
            out.mkdir()
            ctx = _make_context(out, e_meta=False, e_median=False)
            PixelWriter(channels=channels,
                        kwargs_call={'style': _SMALL_STYLE,
                                     'sampling_rate': 100.0}).write(
                meta, wave, [], ctx)
            stack = np.load(out / 'figures.npy')
            # grayscale keeps the channel axis: uniform NHWC rank
            assert stack.shape == (2, self._H, self._W, depth)
        # an unknown channel format is systematic: fail at construction
        with pytest.raises(InputValidationError):
            PixelWriter(channels='cmyk')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_dtype_cast(self, tmp_path):
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        PixelWriter(dtype=np.uint8,
                    kwargs_call={'style': _SMALL_STYLE,
                                 'sampling_rate': 100.0}).write(
            meta, wave, [], ctx)
        stack = np.load(tmp_path / 'figures.npy')
        assert stack.dtype == np.uint8
        # the white figure background keeps the native 0-255 range
        assert stack.max() == 255
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_size_mismatch_raises(self, tmp_path, monkeypatch):
        # stacking requires a shared (height, width) across the chunk;
        # simulate per-record canvas drift and expect a loud failure
        shapes = iter([(10, 20, 4), (12, 20, 4)])
        monkeypatch.setattr(
            ECGDrawing, 'to_numpy',
            lambda self, crop=False, close=True: np.zeros(
                next(shapes), dtype=np.uint8))
        meta, wave = _make_figure_records(_LEADS_12)
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        with pytest.raises(InputValidationError, match='height'):
            PixelWriter(kwargs_call={'style': _SMALL_STYLE,
                                     'sampling_rate': 100.0}).write(
                meta, wave, [], ctx)
        # fail-fast: nothing is written
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_skip_data_keeps_alignment(self, tmp_path):
        # only record 'b' carries the referenced key; with skip_data the
        # failing record is dropped from BOTH the tensor and the
        # metadata rows, so row i still matches slice i
        open_before = plt.get_fignums()
        meta, wave = _make_figure_records(_LEADS_12)
        meta[1]['extra'] = 7.0
        spec = [{'text': '{extra}', 'xy': (0.5, 0.5)}]
        ctx = _make_context(tmp_path, e_median=False, skip_data=True)
        PixelWriter(annotate=spec,
                    kwargs_call={'style': _SMALL_STYLE}).write(
            meta, wave, [], ctx)
        stack = np.load(tmp_path / 'figures.npy')
        meta_tab = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t',
                               index_col=0)
        assert stack.shape[0] == 1
        # only the surviving record 'b' remains, keeping the alignment
        assert list(meta_tab.index) == ['b']
        uid, cause = ctx.failed_records[0]
        assert uid == 'a'
        assert 'Annotation failed' in cause
        assert plt.get_fignums() == open_before

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.mark.tensorflow
class TestTFRecordWriter(object):
    """
    Content-level round-trip test for the tfrecord writer: the record is
    parsed back and the feature values are compared against the input.
    Skipped when tensorflow is not installed (see conftest.py).
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path):
        import tensorflow as tf
        # a SUBSET of leads (I, II) at equal length 5; absent leads are NaN
        wave = [{'I': np.arange(5.0), 'II': np.arange(5.0) + 1},
                {'I': np.arange(5.0) + 2, 'II': np.arange(5.0) + 3}]
        # 'note' is non-numeric and must be dropped by numeric_meta
        meta = [{'age': 50.0, 'note': 'x'}, {'age': 60.0, 'note': 'y'}]
        ctx = _make_context(tmp_path, e_median=False)
        TFRecordWriter().write(meta, wave, [], ctx)
        assert 'ecg_data.tfrecord' in os.listdir(tmp_path)
        assert 'header_metadata.txt' in os.listdir(tmp_path)
        # #### parse the single serialised example back
        records = list(tf.data.TFRecordDataset(
            str(tmp_path / 'ecg_data.tfrecord')))
        assert len(records) == 1
        feature = tf.train.Example.FromString(
            records[0].numpy()).features.feature
        # #### metadata: 'note' dropped, flattened (2 records, 1 column)
        assert list(feature[CTypes.MetaData].float_list.value) == [50.0, 60.0]
        # #### waveforms: flattened canonical (n_records, 12 leads, length)
        waves = np.array(
            feature[CTypes.WaveForms].float_list.value).reshape(2, 12, 5)
        np.testing.assert_allclose(waves[0, 0], np.arange(5.0))
        np.testing.assert_allclose(waves[1, 1], np.arange(5.0) + 3)
        # absent leads carry NaN
        assert np.isnan(waves[0, 2]).all()
        # #### median beats were not exported
        assert CTypes.MedianBeats not in feature

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestLazyTensorflow(object):
    """
    Testing that tensorflow is an optional, lazily imported dependency:
    importing the package must not import tensorflow, and using the
    tfrecord writer without tensorflow installed must raise an actionable
    ImportError naming the install route.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_package_import_does_not_import_tensorflow(self):
        # a fresh interpreter is needed: the current test process may
        # already have tensorflow in sys.modules from other tests
        code = (
            'import sys; '
            'import ecgprocess; '
            'import ecgprocess.writer; '
            'import ecgprocess.tabular; '
            "assert 'tensorflow' not in sys.modules, "
            "'tensorflow imported at package import time'"
        )
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_tensorflow_raises_actionable_error(
            self, tmp_path, monkeypatch):
        # None in sys.modules makes `import tensorflow` raise ImportError,
        # emulating an absent installation regardless of prior imports
        monkeypatch.setitem(sys.modules, 'tensorflow', None)
        wave = [{'I': np.arange(5.0)}, {'I': np.arange(5.0) + 1}]
        ctx = _make_context(tmp_path, e_meta=False, e_median=False)
        with pytest.raises(ImportError, match=r'ecgprocess\[tensorflow\]'):
            TFRecordWriter().write([], wave, [], ctx)
        # the import is checked before any file is written
        assert os.listdir(tmp_path) == []
