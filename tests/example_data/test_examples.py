"""
Testing an XML schema againt a testing XML file.
"""

import ecgprocess.example_data.examples as examples
from ecgprocess.utils.reader_tools import validate_xml
from lxml import etree

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_validate_xml():
    xml_paths = examples.list_xml_paths()
    tree = validate_xml(xml_path=xml_paths['example_1'],
                 xsd_path=xml_paths['example_1_schema'])
    assert isinstance(tree, etree._ElementTree)

