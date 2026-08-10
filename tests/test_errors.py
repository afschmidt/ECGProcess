from __future__ import annotations
import pytest
import pandas as pd
import ecgprocess.errors as errors_module
from ecgprocess.errors import (
    InputValidationError,
    XMLValidationError,
    are_columns_in_df,
    get_param_name,
    is_series_type,
    is_type,
    same_len,
    string_to_list,
    _check_presence,
    _check_is_file,
)


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestIsType(object):
    """Tests for is_type()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_valid_single_type(self):
        """Matching type returns True."""
        assert is_type(1, int) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_valid_tuple_of_types(self):
        """Matching one of several types returns True."""
        assert is_type("hello", (str, int)) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_explicit_param_name_in_message(self):
        """Supplied param_name appears in the error message."""
        with pytest.raises(InputValidationError, match="my_param"):
            is_type("hello", int, param_name="my_param")


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestGetParamName(object):
    """Tests for get_param_name()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_current_frame_returns_none(self, monkeypatch):
        """
        If there is no current frame to inspect, return None instead
        of crashing.
        """
        monkeypatch.setattr(
            errors_module.inspect, "currentframe", lambda: None
        )
        assert get_param_name(object()) is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_outer_frame_returns_none(self, monkeypatch):
        """
        If the caller's frame has no parent frame to walk up to,
        return None instead of crashing.
        """
        class _OneHopFrame(object):
            f_back = None
        monkeypatch.setattr(
            errors_module.inspect, "currentframe", lambda: _OneHopFrame()
        )
        assert get_param_name(object()) is None


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestSameLen(object):
    """Tests for same_len()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self):
        """Equal-length objects return True."""
        assert same_len([1, 2, 3], [4, 5, 6]) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_unequal_lengths(self):
        """Error message contains the supplied object names."""
        with pytest.raises(ValueError, match="foo"):
            same_len([1], [1, 2], object_names=["foo", "bar"])


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestAreColumnsInDf(object):
    """Tests for are_columns_in_df()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_all_columns(self):
        """All expected columns present returns True."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        assert are_columns_in_df(df, ["a", "b"]) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_column_raises(self):
        """Missing column raises InputValidationError."""
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(InputValidationError):
            are_columns_in_df(df, ["a", "missing"])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_column_warns(self):
        """Missing column with warning=True issues a warning and returns False."""
        df = pd.DataFrame({"a": [1]})
        with pytest.warns(UserWarning):
            result = are_columns_in_df(df, ["a", "missing"], warning=True)
        assert result is False


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestStringToList(object):
    """Tests for string_to_list()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_string_default(self):
        """A string is wrapped as a single-element list."""
        assert string_to_list("hello") == ["hello"]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_non_string_returned_unchanged(self):
        """Non-string input is returned as-is."""
        obj = [1, 2, 3]
        assert string_to_list(obj) is obj


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestXMLValidationError(object):
    """Tests for XMLValidationError."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_message_contains_all_errors(self):
        """All supplied error strings appear in the exception message."""
        errors = ["missing tag <foo>", "invalid attribute bar"]
        exc = XMLValidationError(errors)
        for e in errors:
            assert e in str(exc)


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestIsSeriesType(object):
    """Tests for is_series_type()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_does_not_mutate_dataframe(self):
        """Calling is_series_type must not add attributes to the DataFrame."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        attrs_before = set(df.__dict__.keys())
        is_series_type(df, int)
        attrs_after = set(df.__dict__.keys())
        assert attrs_before == attrs_after, (
            "is_series_type added unexpected attributes to the DataFrame: "
            f"{attrs_after - attrs_before}"
        )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_dataframe_valid(self):
        """DataFrame of ints passes int type check."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        assert is_series_type(df, int) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_series_valid(self):
        """Series of floats passes float type check."""
        s = pd.Series([1.0, 2.0, 3.0])
        assert is_series_type(s, float) is True


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestCheckPresence(object):
    """Tests for _check_presence() (directory existence check)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nonexistent_path_raises_file_not_found(self, tmp_path):
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _check_presence(str(tmp_path / "no_such_dir"))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_file_path_raises_not_a_directory(self, tmp_path):
        """Existing file raises NotADirectoryError."""
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            _check_presence(str(f))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_existing_directory_passes(self, tmp_path):
        """Existing directory does not raise."""
        _check_presence(str(tmp_path))


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestCheckIsFile(object):
    """Tests for _check_is_file() (file existence check)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nonexistent_file_raises(self, tmp_path):
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _check_is_file(str(tmp_path / "no_such_file.cfg"))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_directory_raises_not_a_file(self, tmp_path):
        """Passing a directory raises IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            _check_is_file(str(tmp_path))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_existing_file_passes(self, tmp_path):
        """Existing file does not raise."""
        f = tmp_path / "config.cfg"
        f.write_text("x")
        _check_is_file(str(f))
