# import os
# import shutil
import pytest
import tarfile
import warnings
import numpy as np
from ecgprocess.utils import general as gen_utils
from ecgprocess.errors import  InputValidationError

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def test_directory(tmp_path):
    # Create a temporary directory with some files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("This is file 1")
    (test_dir / "file2.txt").write_text("This is file 2")
    return test_dir

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def tar_file_path(tmp_path):
    # Path to the tar file to be created
    return tmp_path / "archive.tar.gz"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def tar_file_with_contents(tmp_path):
    """Fixture that creates a tar file with some sample files."""
    tar_path = tmp_path / "sample_archive.tar.gz"
    with tarfile.open(tar_path, 'w:gz') as tar:
        for i in range(3):
            file_path = tmp_path / f"file{i}.txt"
            file_path.write_text(f"This is file {i}")
            tar.add(file_path, arcname=f"file{i}.txt")
    return tar_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Tar functions
class TestTarFunctions(object):
    """
    Testing Tar functions.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_replace_with_tar(self, test_directory, tar_file_path):
        gen_utils.replace_with_tar(old_dir=str(test_directory),
                                   new_tar=str(tar_file_path))
        # Check if the tar file was created
        assert tar_file_path.exists(), "The tar archive was not created."
        # Check if the old directory was deleted
        assert not test_directory.exists(), "The old directory was not deleted."
        # Verify contents of the tar file
        with tarfile.open(tar_file_path, "r:gz") as tar:
            files_in_tar = tar.getnames()
            assert "file1.txt" in files_in_tar, "file1.txt was not archived."
            assert "file2.txt" in files_in_tar, "file2.txt was not archived."
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize("mode", ["w:gz", "w:bz2", "w:xz"])
    def test_replace_with_tar_modes(self, test_directory, tar_file_path, mode):
        gen_utils.replace_with_tar(old_dir=str(test_directory),
                                   new_tar=str(tar_file_path), mode=mode)
        # Check if the tar file was created with the specified mode
        assert tar_file_path.exists(), (f"The tar archive was not created with "
                                        f"mode {mode}.")
        # Verify contents of the tar file in read mode for the compression used
        with tarfile.open(tar_file_path, f"r:{mode.split(':')[1]}") as tar:
            files_in_tar = tar.getnames()
            assert "file1.txt" in files_in_tar, "file1.txt was not archived."
            assert "file2.txt" in files_in_tar, "file2.txt was not archived."
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_replase_with_tar_filenotfound(self, test_directory):
        with pytest.raises(FileExistsError):
            gen_utils.replace_with_tar(old_dir=str(test_directory),
                                       new_tar=str('error'))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_replace_with_tar_self_inclusion(self, test_directory):
        """
        `new_tar` resolving to a path inside `old_dir` must be rejected
        up front, instead of letting `os.walk` pick up the still-growing
        archive and add it to itself.
        """
        nested_tar = test_directory / "archive.tar.gz"
        with pytest.raises(ValueError):
            gen_utils.replace_with_tar(old_dir=str(test_directory),
                                       new_tar=str(nested_tar))
        # `old_dir` and its original contents must be untouched
        assert test_directory.exists(), "old_dir should not be removed."
        assert not nested_tar.exists(), "No archive should be produced."
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_list_tar_valid(self, tar_file_with_contents):
        result = gen_utils.list_tar(str(tar_file_with_contents))
        assert isinstance(result, list), "The output should be a list."
        assert len(result) == 3, "The tar file should contain three files."
        assert "file0.txt" in result, "file0.txt should be in the tar file."
        assert "file1.txt" in result, "file1.txt should be in the tar file."
        assert "file2.txt" in result, "file2.txt should be in the tar file."
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_list_tar_invalid_mode(self, tar_file_with_contents):
        """Test list_tar with an invalid mode."""
        with pytest.raises(ValueError, match="`mode` should start with `r:`"):
            gen_utils.list_tar(str(tar_file_with_contents), mode='w:gz')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_list_tar_empty_tar(self, tmp_path):
        """Test list_tar with an empty tar file."""
        empty_tar_path = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_tar_path, 'w:gz') as tar:
            pass
        result = gen_utils.list_tar(str(empty_tar_path))
        assert isinstance(result, list), "The output should be a list."
        assert len(result) == 0, "The tar file should be empty."

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_assign_empty():
    result1 = gen_utils.assign_empty_default(['hello', None, 'world'],
                                             empty_object=list)
    result2 = gen_utils.assign_empty_default(['hello', 'world'], empty_object=list)
    result3 = gen_utils.assign_empty_default([None, 42, 'test', None],
                                             empty_object=dict)
    assert result1 == ['hello', [], 'world']
    assert result2 == ['hello', 'world']
    assert result3 == [{}, 42, 'test', {}]
    with pytest.raises(InputValidationError):
        _ = gen_utils.assign_empty_default('not a list', empty_object=list)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Pytest test case for _update_kwargs
def test_update_kwargs_with_overlapping_keys():
    update_dict = {'c': 'black'}
    result = gen_utils._update_kwargs(update_dict, c='red', alpha=0.5)
    assert result == {'c': 'black', 'alpha': 0.5}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_managed_property():
    # toy data
    val1 = 20
    val2 = 20.0
    val3 = 30
    class TestClass:
        prop  = gen_utils.ManagedProperty('prop')
        prop2 = gen_utils.ManagedProperty('prop2', int)
        prop3 = gen_utils.ManagedProperty('prop3', int)
        def __init__(self):
            type(self).prop3.set_with_setter(self, val3)
    # evaluating stuff
    obj = TestClass()
    obj.prop = val1
    # make sure the getter worked.
    assert obj.prop == val1
    # make sure an error is raised
    with pytest.raises(ValueError):
        obj.prop2 = val2
    # confirm the value has not been set
    assert obj.prop2 is None
    # confirm prop3 cannot be set
    with pytest.raises(AttributeError):
        obj.prop3 = 15
    assert obj.prop3 == val3
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# parse function functions
class TestParseNumber(object):
    """
    Testing parse_number
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_number_valid(self):
        result = gen_utils.parse_number("1,2,3.5,4")
        assert result == [1, 2, 3.5, 4]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_number_list(self):
        list_2 = ["1,2.5,3", "2"]
        result = gen_utils.parse_number(["1,2.5,3"])
        result2 = gen_utils.parse_number(list_2)
        assert result == [1, 2.5, 3]
        assert result2 == list_2
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_number_nonnumber(self):
        result = gen_utils.parse_number("1,2,abc")
        assert result == "1,2,abc"
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_number_sep_ec(self):
        result = gen_utils.parse_number("1;2;3,5", sep=";", dec=",")
        assert result == [1, 2, 3.5]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_number_non_string_input(self):
        result = gen_utils.parse_number(123)
        assert result == 123

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_string_concat():
    '''
    Testing different inputs
    '''
    assert gen_utils.string_concat('hello', 'world') == 'hello, world'
    assert gen_utils.string_concat('hello', 'world', sep='\n') == 'hello\nworld'
    assert gen_utils.string_concat(np.nan, 'world', sep=': ') == 'world'
    assert gen_utils.string_concat(1.0, 'world', sep=': ') == '1.0: world'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestChunkList(object):
    """
    Testing chunks
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize(
        "lst, size, expected",
        [
            # standard
            ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
            # last chunk smaller
            ([1, 2, 3, 4, 5], 3, [[1, 2, 3], [4, 5]]),
            # Single elements
            ([1, 2, 3, 4, 5], 1, [[1], [2], [3], [4], [5]]),
            # Exact size
            ([1, 2, 3], 3, [[1, 2, 3]]),
            # Size larger than list len
            ([1, 2, 3], 4, [[1, 2, 3]]),
            # empty
            ([], 3, []),
        ],
    )
    def test_chunk_list_valid(self, lst, size, expected):
        result = list(gen_utils.chunk_list(lst, size))
        assert result == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize(
        "lst, size, exception",
        [
            ([1, 2, 3], 0, ValueError),
            ("not a list", 3, InputValidationError),
            ([1, 2, 3], "not an int", InputValidationError),
        ],
    )
    def test_invalid_cases(self, lst, size, exception):
        with pytest.raises(exception):
            list(gen_utils.chunk_list(lst, size))
    
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_update_dict_with_warning():
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}
    # Test with verbose=True, expect a warning for the duplicate 'b'
    with warnings.catch_warnings(record=True) as w:
        updated_dict = gen_utils.update_dict_with_warning(
            d1.copy(), d2, verbose=True)
    assert len(w) == 1, "Expected exactly one warning for duplicate keys"
    assert "Duplicate key 'b' found." in str(w[0].message)
    assert updated_dict == {"a": 1, "b": 3, "c": 4}
    # Test with verbose=False, expect no warnings
    with warnings.catch_warnings(record=True) as w:
        updated_dict_no_warn = gen_utils.update_dict_with_warning(
            d1.copy(), d2, verbose=False)
    assert len(w) == 0, "Did not expect a warning when verbose=False"
    assert updated_dict_no_warn == {"a": 1, "b": 3, "c": 4}
