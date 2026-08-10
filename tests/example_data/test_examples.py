"""
Testing an XML schema against a testing XML file.
"""

import os
import numpy as np
import pytest
import ecgprocess.example_data.examples as examples
from ecgprocess.utils.reader_tools import validate_xml
from ecgprocess.writer import WriteContext, XMLWriter
from lxml import etree

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_validate_xml():
    xml_paths = examples.list_xml_paths()
    tree = validate_xml(xml_path=xml_paths['example_1'],
                 xsd_path=xml_paths['example_1_schema'])
    assert isinstance(tree, etree._ElementTree)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_xml_writer_example_template_and_schema_agree(tmp_path):
    """The shipped XMLWriter template and its XSD validate together."""
    paths = examples.list_xml_writer_paths()
    assert os.path.isfile(paths['example_1_template'])
    assert os.path.isfile(paths['example_1_schema'])
    writer = XMLWriter(template=paths['example_1_template'],
                        xsd_path=paths['example_1_schema'])
    meta = [{'unique identifier': 'uid-0',
             'sampling frequency (original)': 500.0}]
    wave = [{'I': np.arange(3.0), 'II': np.arange(3.0) + 1}]
    median = [{'I': np.array([0.5, 1.5]), 'II': np.array([0.25, 0.75])}]
    ctx = WriteContext(
        e_meta=True, e_wave=True, e_median=True,
        key_list=['uid-0'], target=str(tmp_path), chunk_num=None)
    writer.write(meta, wave, median, ctx)
    written = tmp_path / 'uid-0.xml'
    assert written.is_file()
    tree = validate_xml(xml_path=str(written),
                        xsd_path=paths['example_1_schema'])
    assert isinstance(tree, etree._ElementTree)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_dataset_duplicate_registration_raises():
    """Registering two dataset functions under the same name raises a
    KeyError instead of the second silently overwriting the first."""
    name = "_test_duplicate_dataset_fn"

    def _test_duplicate_dataset_fn(*args, **kwargs):
        return None

    assert _test_duplicate_dataset_fn.__name__ == name
    try:
        examples.dataset(_test_duplicate_dataset_fn)
        with pytest.raises(KeyError):
            examples.dataset(_test_duplicate_dataset_fn)
    finally:
        examples._DATASETS.pop(name, None)

