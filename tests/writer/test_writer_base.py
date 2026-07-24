import pytest
from ecgprocess.constants import (
    TabularNames as TabNames,
)
from ecgprocess.errors import Error_MSG, InputValidationError
from ecgprocess.writer import (
    BaseWriter,
    TableWriter,
    NumpyWriter,
    WRITERS,
    register_writer,
    resolve_writer,
    WriterValidator,
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
    def test_construction(self, tmp_path, make_context):
        ctx = make_context(tmp_path, chunk_num=3)
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
    def test_resolve_callable(self, tmp_path, make_context):
        calls = []
        def _bare_writer(meta_list, wave_list, median_list, ctx):
            calls.append(ctx.target)
        resolved = resolve_writer(_bare_writer)
        assert isinstance(resolved, BaseWriter)
        resolved.write([], [], [], make_context(tmp_path))
        assert calls == [str(tmp_path)]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resolve_rejects_bad_type(self):
        with pytest.raises(TypeError):
            resolve_writer(42)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestWriterValidator(object):
    """
    Testing the WriterValidator pre-flight compliance check: pass cases
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
        class _MiniNpy(NumpyWriter):
            FILE_EXT = '.npy'
            def _save(self, res_dict, ctx):
                return None
        WriterValidator(_Good)
        WriterValidator(_Good())
        WriterValidator(_Variadic)
        WriterValidator(_MiniNpy)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_rejects_non_writers(self):
        def _bare(meta_list, wave_list, median_list, ctx):
            return None
        for bad in (42, 'npy', _bare):
            with pytest.raises(InputValidationError) as err:
                WriterValidator(bad)
            assert Error_MSG.WRITER_NOT_WRITER.format(bad) in str(err.value)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_write_contract_violations(self):
        class _NoArgs(BaseWriter):
            def write(self):
                return None
        with pytest.raises(InputValidationError) as err:
            WriterValidator(BaseWriter)
        assert Error_MSG.WRITER_ABSTRACT.format('write') in str(err.value)
        with pytest.raises(InputValidationError) as err:
            WriterValidator(_NoArgs)
        assert Error_MSG.WRITER_SIGNATURE.split('{')[0] in str(err.value)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_init_args(self):
        class _NeedsArg(BaseWriter):
            def __init__(self, path):
                self.path = path
            def write(self, meta_list, wave_list, median_list, ctx):
                return None
        with pytest.raises(InputValidationError) as err:
            WriterValidator(_NeedsArg)
        assert Error_MSG.WRITER_INIT.split('{')[0] in str(err.value)
        WriterValidator(_NeedsArg('out.txt'))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_multi_violation_single_raise(self):
        class _Broken(BaseWriter):
            FILE_EXT = 'json'
            def file_names(self, chunk_num=None):
                return ()
            def write(self):
                return None
        with pytest.raises(InputValidationError) as err:
            WriterValidator(_Broken)
        message = str(err.value)
        assert Error_MSG.WRITER_SIGNATURE.split('{')[0] in message
        assert Error_MSG.WRITER_FILE_EXT_DOT.format('json') in message
        assert Error_MSG.WRITER_NAMES_LEN.format(0) in message
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_describe_prints_checklist(self, capsys):
        result = WriterValidator.describe()
        captured = capsys.readouterr()
        assert result is None
        output = captured.out
        assert 'write' in output
        assert 'FILE_EXT' in output
        assert 'WriteContext' in output
        assert 'key_list' in output
        assert 'target' in output
        assert 'chunk_num' in output
        assert 'failed_records' in output
        assert 'append' in output
