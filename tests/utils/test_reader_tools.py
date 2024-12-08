import pytest
import numpy as np
from lxml import etree
from xmltodict import parse
from ecgprocess.utils import reader_tools as reader_utils
from ecgprocess.errors import (
    XMLValidationError, InputValidationError, MissingTagError
)

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
# XML functions
class TestXMLFunctions(object):
    """
    Testing XML functions.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml(self, valid_xml, valid_xsd):
        xml_doc = reader_utils.validate_xml(xml_path=valid_xml,
                                            xsd_path=valid_xsd, strict=True,)
        assert isinstance(xml_doc, etree._ElementTree)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml_not_strict(self, invalid_xml, valid_xsd):
        with pytest.warns(UserWarning):
            xml_doc = reader_utils.validate_xml(xml_path=invalid_xml,
                                             xsd_path=valid_xsd, strict=False)
        assert isinstance(xml_doc, etree._ElementTree)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_validate_xml_errors(self, invalid_xml, strict_xsd):
        with pytest.raises(XMLValidationError):
            reader_utils.validate_xml(xml_path=invalid_xml,
                                      xsd_path=strict_xsd, strict=True)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_valid(self, xml_element_tree):
        """Test xml_to_dict with a valid XML document."""
        result = reader_utils.xml_to_dict(xml_element_tree)
        assert isinstance(result, dict)
        assert 'RootTag' in result
        assert result['RootTag']['Element1'] == 'Value1'
        assert result['RootTag']['Element2'] == 'Value2'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_with_non_utf8_encoding(
        self, non_utf8_encoded_xml_element_tree):
            """Test xml_to_dict with a non-UTF-8 encoded XML document."""
            result = reader_utils.xml_to_dict(
                non_utf8_encoded_xml_element_tree, encoding='ISO-8859-1')
            assert isinstance(result, dict)
            assert 'RootTag' in result
            assert result['RootTag']['Element1'] == 'Value1'
            assert result['RootTag']['Element2'] == 'Value2'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_empty(self):
        """Test xml_to_dict with an empty XML document."""
        empty_tree = etree.ElementTree()
        with pytest.raises(TypeError):
            reader_utils.xml_to_dict(empty_tree)
        with pytest.raises(InputValidationError):
            reader_utils.xml_to_dict({})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xml_to_dict_invalid_structure(self, invalid_xml):
        """Test xml_to_dict with an invalid XML structure."""
        parser = etree.XMLParser(remove_blank_text=True)
        with open(invalid_xml, 'rb') as xml_file:
            tree = etree.parse(xml_file, parser)
        result = reader_utils.xml_to_dict(tree)
        assert isinstance(result, dict)
        assert 'UnexpectedElement' in result['RootTag']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict(self, nested_dict_fixture):
        # Test case when skip_root is True (default)
        expected = {'b': 1, 'c.d': 2, 'e_0.f': 3, 'e_1': 4, 'e_2': None}
        result = reader_utils.flatten_dict(nested_dict_fixture)
        assert result == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict_skip_root(self, nested_dict_fixture):
        # Test case when skip_root is False
        expected = {'a.b': 1, 'a.c.d': 2, 'a.e_0.f': 3, 'a.e_1': 4,
                    'a.e_2': None}
        result = reader_utils.flatten_dict(nested_dict_fixture,
                                           skip_root=False)
        assert result == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_flatten_dict_separator(self, nested_dict_fixture):
        # Test case when using a custom separator
        expected = {'a_b': 1, 'a_c_d': 2, 'a_e_0_f': 3, 'a_e_1': 4,
                    'a_e_2': None}
        result = reader_utils.flatten_dict(nested_dict_fixture, sep='_',
                                        skip_root=False)
        assert result == expected

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Extract data
class TestGetECGData(object):
    """
    Testing `get_ecg_data`
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_basic_functionality(self):
        data_dict = {"signal1": [1, 2, 3], "signal2": [4, 5, 6]}
        config = {"output1": "signal1", "output2": "signal3"}
        res, res_missing = reader_utils.get_ecg_data(data_dict, config)
        assert res == {"output1": [1, 2, 3], "output2": None}
        assert res_missing == ["signal3"]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_parse_numeric(self):
        data_dict = {"value1": "123", "value2": "4.56"}
        config = {"int_val": "value1", "float_val": "value2"}
        res, _ = reader_utils.get_ecg_data(data_dict, config,
                                           parse_numeric=True)
        assert res == {"int_val": 123, "float_val": 4.56}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_as_array(self):
        data_dict = {"signal1": ['1, 2, 3'], "signal2": [4, 5, 6]}
        config = {"output1": "signal1"}
        res, _ = reader_utils.get_ecg_data(data_dict, config,
                                           as_array=True,
                                           bits=np.float32)
        assert np.array_equal(
            res["output1"], np.array([1, 2, 3], dtype=np.float32))
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_data_error(self):
        data_dict = {"signal1": [1, 2, 3]}
        config = {"output1": "signal2"}
        with pytest.raises(MissingTagError):
            reader_utils.get_ecg_data(data_dict, config, skip_empty=False)

