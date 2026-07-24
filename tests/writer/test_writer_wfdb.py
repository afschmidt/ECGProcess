import os
import sys
import subprocess
import pytest
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.writer import (
    BaseWriter,
    WriteContext,
    WFDBWriter,
    WRITERS,
    WriterValidator,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CProc = Core.ProcessingData

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# helpers

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_wfdb_records(leads, n=2, length=50, sf_key=CProc.SF_NEW_W,
                       fs=500.0):
    """Signal dicts for `leads` plus metadata carrying the processed fs."""
    rng = np.random.default_rng(11)
    sig_list = [
        {lead: rng.standard_normal(length) for lead in leads}
        for _ in range(n)
    ]
    meta_list = [{sf_key: fs} for _ in range(n)]
    return meta_list, sig_list

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_wfdb_context(target, key_list, e_meta=True, e_wave=True,
                       e_median=False):
    """Build a WriteContext for the given (arbitrary-length) key_list."""
    return WriteContext(
        e_meta=e_meta, e_wave=e_wave, e_median=e_median,
        key_list=key_list, target=str(target), chunk_num=None,
    )

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.mark.wfdb
class TestWFDBWriter(object):
    """
    Testing the WFDB per-record writer's core surface: registration,
    round-trip fidelity through `wfdb.rdrecord` (including the
    `units_field` override), source selection, UID sanitisation, and
    the consolidated source/precondition guards. Skipped when wfdb is
    not installed (see conftest.py).
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered_and_validates(self):
        assert WRITERS[TabNames.WRITE_WFDB] is WFDBWriter
        assert issubclass(WFDBWriter, BaseWriter)
        WriterValidator(WFDBWriter)
        WriterValidator(WFDBWriter())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_round_trip(self, tmp_path):
        # the core proof point: header (fs, sig_name, units incl. the
        # units_field override), physical-value fidelity, and header
        # comments (UID + meta_fields)
        import wfdb
        leads = ['I', 'II', 'V1']
        meta, wave = _make_wfdb_records(leads, fs=500.0)
        meta[0]['note'] = 'first'
        meta[0]['unit_meta'] = 'uV'
        meta[1]['note'] = 'second'
        ctx = _make_wfdb_context(tmp_path, ['a', 'b'])
        WFDBWriter(meta_fields=['note'], units_field='unit_meta').write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {
            'a.hea', 'a.dat', 'b.hea', 'b.dat'}
        record = wfdb.rdrecord(str(tmp_path / 'a'))
        assert record.fs == 500.0
        assert record.sig_name == leads
        # record 'a' carries unit_meta -> overrides the 'mV' default
        assert record.units == ['uV'] * len(leads)
        # int16 quantisation tolerance: gain/baseline are auto-computed
        # by wfdb from p_signal, so the round trip is not exact
        np.testing.assert_allclose(
            record.p_signal,
            np.column_stack([wave[0][lead] for lead in leads]),
            atol=1e-2,
        )
        assert record.comments[0] == 'UID: a'
        assert 'note: first' in record.comments
        # record 'b' has no unit_meta -> falls back to the 'mV' default
        record_b = wfdb.rdrecord(str(tmp_path / 'b'))
        assert record_b.units == ['mV'] * len(leads)
        assert record_b.comments[0] == 'UID: b'
        assert 'note: second' in record_b.comments
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_median_source(self, tmp_path):
        import wfdb
        leads = ['I', 'II']
        meta, median = _make_wfdb_records(
            leads, sf_key=CProc.SF_NEW_M, fs=100.0)
        ctx = _make_wfdb_context(
            tmp_path, ['a', 'b'], e_wave=False, e_median=True)
        WFDBWriter(source='median').write(meta, [], median, ctx)
        record = wfdb.rdrecord(str(tmp_path / 'a'))
        assert record.fs == 100.0
        assert record.sig_name == leads
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_uid_sanitisation(self, tmp_path):
        import wfdb
        meta, wave = _make_wfdb_records(['I'], n=1, fs=500.0)
        ctx = _make_wfdb_context(tmp_path, ['weird id/1!'])
        WFDBWriter().write(meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {
            'weird_id_1_.hea', 'weird_id_1_.dat'}
        record = wfdb.rdrecord(str(tmp_path / 'weird_id_1_'))
        assert record.comments[0] == 'UID: weird id/1!'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_meta_fields_all_sentinel(self, tmp_path):
        """Verify meta_fields='all' copies every key in the record's metadata."""
        import wfdb
        leads = ['I', 'II']
        meta, wave = _make_wfdb_records(leads, fs=500.0)
        # Add various metadata fields to the records
        meta[0]['note'] = 'important notes'
        meta[0]['acquisition_date'] = '2026-07-20'
        meta[0]['custom_field'] = 'custom_value'
        meta[0]['unit_meta'] = 'uV'
        ctx = _make_wfdb_context(tmp_path, ['a', 'b'])
        # Write with meta_fields='all'
        WFDBWriter(meta_fields='all').write(meta, wave, [], ctx)
        # Read back the first record
        record = wfdb.rdrecord(str(tmp_path / 'a'))
        # Verify all metadata keys appear in comments
        comments_str = ' '.join(record.comments)
        assert 'note: important notes' in comments_str
        assert 'acquisition_date: 2026-07-20' in comments_str
        assert 'custom_field: custom_value' in comments_str
        assert 'unit_meta: uV' in comments_str
        assert 'UID: a' in record.comments[0]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_meta_fields_all_with_newlines(self, tmp_path):
        """Verify metadata values with newlines are sanitised to single lines."""
        import wfdb
        leads = ['I']
        meta, wave = _make_wfdb_records(leads, n=1, fs=500.0)
        # Add metadata with various newline patterns
        meta[0]['multiline_note'] = 'line 1\nline 2\nline 3'
        meta[0]['carriage_return'] = 'before\rafter'
        meta[0]['windows_newline'] = 'before\r\nafter'
        ctx = _make_wfdb_context(tmp_path, ['a'])
        WFDBWriter(meta_fields='all').write(meta, wave, [], ctx)
        record = wfdb.rdrecord(str(tmp_path / 'a'))
        # All comments should be single-line strings (no actual newlines in them)
        for comment in record.comments:
            assert '\n' not in comment
            assert '\r' not in comment
        
        # The values should be present but with newlines replaced by spaces
        comments_str = ' '.join(record.comments)
        assert 'multiline_note: line 1 line 2 line 3' in comments_str
        assert 'carriage_return: before after' in comments_str
        assert 'windows_newline: before after' in comments_str
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_meta_fields_explicit_list_unchanged(self, tmp_path):
        """Verify explicit list meta_fields=[...] behavior is unchanged."""
        import wfdb
        leads = ['I']
        meta, wave = _make_wfdb_records(leads, n=1, fs=500.0)
        meta[0]['field_a'] = 'value_a'
        meta[0]['field_b'] = 'value_b'
        meta[0]['field_c'] = 'value_c'
        ctx = _make_wfdb_context(tmp_path, ['a'])
        # Write with explicit list (should only include field_a and field_b)
        WFDBWriter(meta_fields=['field_a', 'field_b']).write(meta, wave, [], ctx)
        record = wfdb.rdrecord(str(tmp_path / 'a'))
        comments_str = ' '.join(record.comments)
        # Only explicitly requested fields should appear
        assert 'field_a: value_a' in comments_str
        assert 'field_b: value_b' in comments_str
        assert 'field_c' not in comments_str  # Not requested
        assert 'UID: a' in record.comments[0]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestLazyWFDB(object):
    """
    Testing that wfdb is an optional, lazily imported dependency:
    importing the package must not import wfdb, and using the wfdb
    writer without wfdb installed must raise an actionable ImportError
    naming the install route.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_package_import_does_not_import_wfdb(self):
        # a fresh interpreter is needed: the current test process may
        # already have wfdb in sys.modules from other tests
        code = (
            'import sys; '
            'import ecgprocess; '
            'import ecgprocess.writer; '
            'import ecgprocess.tabular; '
            "assert 'wfdb' not in sys.modules, "
            "'wfdb imported at package import time'"
        )
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_wfdb_raises_actionable_error(
            self, tmp_path, monkeypatch):
        # None in sys.modules makes `import wfdb` raise ImportError,
        # emulating an absent installation regardless of prior imports
        monkeypatch.setitem(sys.modules, 'wfdb', None)
        wave = [{'I': np.arange(5.0)}]
        meta = [{CProc.SF_NEW_W: 500.0}]
        ctx = _make_wfdb_context(tmp_path, ['a'])
        with pytest.raises(ImportError, match=r'ecgprocess\[wfdb\]'):
            WFDBWriter().write(meta, wave, [], ctx)
        # the import is checked before any file is written
        assert os.listdir(tmp_path) == []
