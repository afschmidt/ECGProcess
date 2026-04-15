from __future__ import annotations
import pytest
import pandas as pd
from ecgprocess.errors import is_series_type, _check_presence, _check_is_file


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestIsSeriesType(object):
    """Tests for is_series_type()."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_series_type_does_not_mutate_dataframe(self):
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
    def test_is_series_type_dataframe_valid(self):
        """Happy path: DataFrame of ints passes int type check."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        assert is_series_type(df, int) is True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_is_series_type_series_valid(self):
        """Happy path: Series of floats passes float type check."""
        s = pd.Series([1.0, 2.0, 3.0])
        assert is_series_type(s, float) is True


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestCheckPresence(object):
    """Tests for _check_presence() (directory existence check)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nonexistent_path_raises_file_not_found(self, tmp_path):
        """Non-existent path must raise FileNotFoundError."""
        missing = str(tmp_path / "no_such_dir")
        with pytest.raises(FileNotFoundError):
            _check_presence(missing)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_file_path_raises_not_a_directory(self, tmp_path):
        """Existing file (not directory) must raise NotADirectoryError."""
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            _check_presence(str(f))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_existing_directory_passes(self, tmp_path):
        """Existing directory must not raise."""
        _check_presence(str(tmp_path))


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestCheckIsFile(object):
    """Tests for _check_is_file() (file existence check)."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_nonexistent_file_raises(self, tmp_path):
        """Non-existent path must raise FileNotFoundError."""
        missing = str(tmp_path / "no_such_file.cfg")
        with pytest.raises(FileNotFoundError):
            _check_is_file(missing)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_directory_raises_not_a_file(self, tmp_path):
        """Passing a directory must raise IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            _check_is_file(str(tmp_path))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_existing_file_passes(self, tmp_path):
        """Existing file must not raise."""
        f = tmp_path / "config.cfg"
        f.write_text("x")
        _check_is_file(str(f))
