# import os
import pytest
import tarfile
# import shutil
from lxml import etree
# from pathlib import Path
from ecgprocess.utils import general as gen_utils
from ecgprocess.errors import XMLValidationError, InputValidationError

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Fixture

# Sample valid XML and XSD content for testing
VALID_XML_PATH = "valid_example.xml"
VALID_XSD_PATH = "valid_schema.xsd"
INVALID_XML_PATH = "invalid_example.xml"
STRICT_XSD_PATH = "strict_schema.xsd"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def nested_dict_fixture():
    return {
        'a': {
            'b': 1,
            'c': {
                'd': 2
            },
            'e': [
                {'f': 3},
                4,
                None
            ]
        }
    }

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
# Create temporary XML and XSD files for testing
@pytest.fixture
def valid_xml(tmp_path):
    xml_content = """
    <RootTag>
        <Element1>Value1</Element1>
        <Element2>Value2</Element2>
    </RootTag>
    """
    xml_path = tmp_path / VALID_XML_PATH
    xml_path.write_text(xml_content)
    return xml_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def valid_xsd(tmp_path):
    xsd_content = """
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
        <xs:element name="RootTag">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="Element1" type="xs:string"/>
                    <xs:element name="Element2" type="xs:string"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    </xs:schema>
    """
    xsd_path = tmp_path / VALID_XSD_PATH
    xsd_path.write_text(xsd_content)
    return xsd_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def invalid_xml(tmp_path):
    xml_content = """
    <RootTag>
        <Element1>Value1</Element1>
        <Element2>Value2</Element2>
        <UnexpectedElement>Extra</UnexpectedElement>
    </RootTag>
    """
    xml_path = tmp_path / INVALID_XML_PATH
    xml_path.write_text(xml_content)
    return xml_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def strict_xsd(tmp_path):
    xsd_content = """
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
        <xs:element name="RootTag">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="Element1" type="xs:string"/>
                    <xs:element name="Element2" type="xs:string"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    </xs:schema>
    """
    xsd_path = tmp_path / STRICT_XSD_PATH
    xsd_path.write_text(xsd_content)
    return xsd_path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def xml_element_tree(valid_xml):
    """Fixture that returns a parsed lxml ElementTree from a valid XML file."""
    parser = etree.XMLParser(remove_blank_text=True)
    with open(valid_xml, 'rb') as xml_file:
        tree = etree.parse(xml_file, parser)
    return tree

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def encoded_xml_element_tree(valid_xml):
    """Fixture for an XML file with a specified encoding."""
    parser = etree.XMLParser(encoding='utf-8')
    with open(valid_xml, 'rb') as xml_file:
        tree = etree.parse(xml_file, parser)
    return tree

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def non_utf8_encoded_xml_element_tree(valid_xml):
    """Fixture for an XML file with a non-UTF-8 encoding (e.g., ISO-8859-1)."""
    parser = etree.XMLParser(encoding='ISO-8859-1')
    with open(valid_xml, 'rb') as xml_file:
        tree = etree.parse(xml_file, parser)
    return tree

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest


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
# XML functions
class TestXMLFunctions(object):
    """
    Testing XML functions.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml(self, valid_xml, valid_xsd):
        xml_doc = gen_utils.validate_xml(xml_path=valid_xml, xsd_path=valid_xsd,
                               strict=True,)
        assert isinstance(xml_doc, etree._ElementTree)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml_not_strict(self, invalid_xml, valid_xsd):
        with pytest.warns(UserWarning):
            xml_doc = gen_utils.validate_xml(xml_path=invalid_xml,
                                             xsd_path=valid_xsd, strict=False)
        assert isinstance(xml_doc, etree._ElementTree)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml_errors(self, invalid_xml, strict_xsd):
        with pytest.raises(XMLValidationError):
            gen_utils.validate_xml(xml_path=invalid_xml, xsd_path=strict_xsd,
                                   strict=True)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_valid(self, xml_element_tree):
        """Test xml_to_dict with a valid XML document."""
        result = gen_utils.xml_to_dict(xml_element_tree)
        assert isinstance(result, dict)
        assert 'RootTag' in result
        assert result['RootTag']['Element1'] == 'Value1'
        assert result['RootTag']['Element2'] == 'Value2'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_with_non_utf8_encoding(self, non_utf8_encoded_xml_element_tree):
            """Test xml_to_dict with a non-UTF-8 encoded XML document."""
            result = gen_utils.xml_to_dict(non_utf8_encoded_xml_element_tree,
                                           encoding='ISO-8859-1')
            assert isinstance(result, dict)
            assert 'RootTag' in result
            assert result['RootTag']['Element1'] == 'Value1'
            assert result['RootTag']['Element2'] == 'Value2'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_empty(self):
        """Test xml_to_dict with an empty XML document."""
        empty_tree = etree.ElementTree()
        with pytest.raises(TypeError):
            gen_utils.xml_to_dict(empty_tree)
        with pytest.raises(InputValidationError):
            gen_utils.xml_to_dict({})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_invalid_structure(self, invalid_xml):
        """Test xml_to_dict with an invalid XML structure."""
        parser = etree.XMLParser(remove_blank_text=True)
        with open(invalid_xml, 'rb') as xml_file:
            tree = etree.parse(xml_file, parser)
        result = gen_utils.xml_to_dict(tree)
        assert isinstance(result, dict)
        assert 'UnexpectedElement' in result['RootTag']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict(self, nested_dict_fixture):
        # Test case when skip_root is True (default)
        expected = {'b': 1, 'c.d': 2, 'e_0.f': 3, 'e_1': 4, 'e_2': None}
        result = gen_utils.flatten_dict(nested_dict_fixture)
        assert result == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict_skip_root(self, nested_dict_fixture):
        # Test case when skip_root is False
        expected = {'a.b': 1, 'a.c.d': 2, 'a.e_0.f': 3, 'a.e_1': 4,
                    'a.e_2': None}
        result = gen_utils.flatten_dict(nested_dict_fixture, skip_root=False)
        assert result == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict_separator(self, nested_dict_fixture):
        # Test case when using a custom separator
        expected = {'a_b': 1, 'a_c_d': 2, 'a_e_0_f': 3, 'a_e_1': 4,
                    'a_e_2': None}
        result = gen_utils.flatten_dict(nested_dict_fixture, sep='_',
                                        skip_root=False)
        assert result == expected

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
def test_property_factor():
    val1 = 20
    val2 = 20.0
    class TestClass:
        prop = gen_utils.property_factory('prop')
        prop2 = gen_utils.property_factory('prop2', int)
        prop3 = gen_utils.property_factory('prop3', int, once=True)
    obj = TestClass()
    obj.prop = val1
    # make sure the getter worked.
    assert obj.prop == val1
    # make sure an error is raised
    with pytest.raises(InputValidationError):
        obj.prop2 = val2
    # confirm the value has not been set
    assert obj.prop2 is None
    # confirm the setter is remove after the first use
    obj.prop3 = val1
    obj.prop3 == val1
    with pytest.raises(AttributeError):
        obj.prop3 = 10
    
