import datetime
import json
import os
import numpy as np
import pytest
import xmltodict
from lxml import etree
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import InputValidationError, XMLValidationError
from ecgprocess.writer import (
    BaseWriter,
    WriteContext,
    WRITERS,
    WriterValidator,
    XMLWriter,
    resolve_writer,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CTypes = Core.DataTypes

# the XSD accepting the `_make_simple_template` document; `Rate` alone,
# so an added element is 'not expected' and exercises the strict switch
SIMPLE_XSD = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="ECG">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Rate" type="xs:string"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:string"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# helpers

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_xml_template():
    """A template drawing on all three sources, with attributes and lists."""
    return {
        'ECG': {
            '@id': f'{CTypes.MetaData}.unique identifier',
            'Lead': [{'#text': f'{CTypes.WaveForms}.I'}],
            'Median': f'{CTypes.MedianBeats}.I',
        }
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_simple_template():
    """A metadata-only template matching SIMPLE_XSD."""
    return {
        'ECG': {
            '@id': f'{CTypes.MetaData}.unique identifier',
            'Rate': f'{CTypes.MetaData}.rate',
        }
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_xml_records(n=2):
    """Metadata, waveform and median-beat dicts for `n` records."""
    meta_list = [
        {'unique identifier': f'uid-{index}', 'rate': 500.0}
        for index in range(n)
    ]
    wave_list = [{'I': np.arange(3.0) + index} for index in range(n)]
    median_list = [{'I': np.array([0.5, 1.5])} for _ in range(n)]
    return meta_list, wave_list, median_list

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _make_xml_context(target, key_list, e_meta=True, e_wave=True,
                      e_median=True, skip_data=False):
    """Build a WriteContext for the given key_list."""
    return WriteContext(
        e_meta=e_meta, e_wave=e_wave, e_median=e_median,
        key_list=key_list, target=str(target), chunk_num=None,
        skip_data=skip_data,
    )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _write_xsd(tmp_path):
    """Dump SIMPLE_XSD and return its path as a string."""
    path = tmp_path / 'simple.xsd'
    path.write_text(SIMPLE_XSD)
    return str(path)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestXMLWriter(object):
    """
    Testing the XML writer skeleton: registration in the writer
    framework, constructor validation, template loading, the eager
    template walk (a malformed reference must raise at construction, not
    at write time), and sanitised per-record file naming.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered_and_validates(self):
        assert WRITERS[TabNames.WRITE_XML] is XMLWriter
        assert issubclass(XMLWriter, BaseWriter)
        # the registry route instantiates the class with no arguments
        assert isinstance(resolve_writer(TabNames.WRITE_XML), XMLWriter)
        WriterValidator(XMLWriter)
        WriterValidator(XMLWriter(template=_make_xml_template()))
        assert XMLWriter.FILE_EXT == '.xml'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('kwargs', [
        {'template': 1},
        {'xsd_path': 1},
        {'strict': 'yes'},
        {'xml_declaration': 'yes'},
        {'pretty': 'yes'},
        {'encoding': 1},
    ])
    def test_rejects_wrong_types(self, kwargs):
        kwargs.setdefault('template', _make_xml_template())
        with pytest.raises(InputValidationError):
            XMLWriter(**kwargs)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_loads_template_from_json_path(self, tmp_path):
        template = _make_xml_template()
        path = tmp_path / 'template.json'
        path.write_text(json.dumps(template))
        assert XMLWriter(template=str(path)).template == template
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('leaf', [
        'urn:hl7-org:v3',
        'MetaData',
        'MetaData.',
        'OtherData.raw',
        'MetaDta.unique identifier',
    ])
    def test_leaves_that_are_not_references_are_literals(self, leaf):
        # anything that does not name a known source is a constant
        assert XMLWriter(template={'ECG': {'V': leaf}})._sources == set()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('leaf', [
        'metadata.unique identifier',
        'WAVEFORMS.I',
        'medianbeats.I',
    ])
    def test_source_differing_only_in_case_raises(self, leaf):
        with pytest.raises(InputValidationError):
            XMLWriter(template={'ECG': {'V': leaf}})
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_error_locates_the_offending_leaf(self):
        with pytest.raises(InputValidationError) as excinfo:
            XMLWriter(template={'ECG': {'Lead': [{'#text': 'metadata.x'}]}})
        message = str(excinfo.value)
        # the message locates the leaf, quotes it, and names the source
        # it was probably meant to reference
        assert 'ECG.Lead[0].#text' in message
        assert 'metadata.x' in message
        assert CTypes.MetaData in message
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_collects_referenced_sources(self):
        # nested, attribute and list leaves are all walked; non-string
        # leaves are literals and contribute no source
        writer = XMLWriter(template=_make_xml_template())
        assert writer._sources == {
            CTypes.MetaData, CTypes.WaveForms, CTypes.MedianBeats}
        assert XMLWriter(template={'ECG': {'N': 12}})._sources == set()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_record_file_name_sanitises_uid(self):
        writer = XMLWriter(template=_make_xml_template())
        assert writer._record_file_name('weird id/1!') == 'weird_id_1_.xml'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('key', [
        '1Bad', 'Bad Name', 'Bad<Name', 'Bad&Name', '',
    ])
    def test_validate_name_rejects_illegal_names(self, key):
        """
        A leading digit, embedded whitespace, angle brackets, an
        ampersand, and an empty string are all illegal XML names.
        """
        with pytest.raises(InputValidationError):
            XMLWriter._validate_name(key, f'ECG.{key}')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('key', [
        'Tag', '_tag', 'ns:tag', 'tag-1', 'tag.1', '@attr', '#text',
    ])
    def test_validate_name_accepts_legal_names(self, key):
        """
        '@attr' and '#text' are xmltodict's attribute/text markers;
        the rest are plain element names.
        """
        XMLWriter._validate_name(key, f'ECG.{key}')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestXMLWriterWrite(object):
    """
    Testing the write path: one document per record resolved from all
    three sources, leaf normalisation, the upfront configuration guards,
    and per-record failure handling under `ctx.skip_data`.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_writes_one_document_per_record(self, tmp_path):
        meta, wave, median = _make_xml_records()
        ctx = _make_xml_context(tmp_path, ['a', 'b'])
        XMLWriter(template=_make_xml_template()).write(
            meta, wave, median, ctx)
        assert set(os.listdir(tmp_path)) == {'a.xml', 'b.xml'}
        parsed = xmltodict.parse((tmp_path / 'a.xml').read_text())
        # every source resolves into the one document, arrays as text
        assert parsed['ECG']['@id'] == 'uid-0'
        assert parsed['ECG']['Lead'] == '0.0,1.0,2.0'
        assert parsed['ECG']['Median'] == '0.5,1.5'
        assert ctx.failed_records == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('value, expected', [
        (np.float64(1.5), '1.5'),
        (float('nan'), 'NaN'),
        (float('-inf'), '-INF'),
        (datetime.date(2026, 7, 31), '2026-07-31'),
        ('clean\x00text', 'cleantext'),
    ])
    def test_leaf_normalisation(self, tmp_path, value, expected):
        meta, wave, median = _make_xml_records(n=1)
        meta[0]['field'] = value
        ctx = _make_xml_context(tmp_path, ['a'])
        XMLWriter(
            template={'ECG': {'V': f'{CTypes.MetaData}.field'}},
        ).write(meta, wave, median, ctx)
        parsed = xmltodict.parse((tmp_path / 'a.xml').read_text())
        assert parsed['ECG']['V'] == expected
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_literals_are_written_verbatim(self, tmp_path):
        # the namespace declaration a real schema needs is a constant,
        # not a reference into the record
        meta, wave, median = _make_xml_records(n=1)
        XMLWriter(template={'AnnotatedECG': {
            '@xmlns': 'urn:hl7-org:v3',
            'id': f'{CTypes.MetaData}.unique identifier',
        }}).write(meta, wave, median, _make_xml_context(tmp_path, ['a']))
        parsed = xmltodict.parse((tmp_path / 'a.xml').read_text())
        assert parsed['AnnotatedECG']['@xmlns'] == 'urn:hl7-org:v3'
        assert parsed['AnnotatedECG']['id'] == 'uid-0'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_config_errors_raise_before_any_file(self, tmp_path):
        meta, wave, median = _make_xml_records()
        ctx = _make_xml_context(tmp_path, ['a', 'b'], e_median=False)
        # the template reads MedianBeats, which was not extracted
        with pytest.raises(InputValidationError):
            XMLWriter(template=_make_xml_template()).write(
                meta, wave, [], ctx)
        # an unconfigured writer is equally a configuration error
        with pytest.raises(InputValidationError):
            XMLWriter().write(meta, wave, median,
                              _make_xml_context(tmp_path, ['a', 'b']))
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_field_respects_skip_data(self, tmp_path):
        meta, wave, median = _make_xml_records()
        # only the second record carries the referenced field
        meta[1]['extra'] = 'present'
        template = {'ECG': {'V': f'{CTypes.MetaData}.extra'}}
        ctx = _make_xml_context(tmp_path, ['a', 'b'], skip_data=True)
        XMLWriter(template=template).write(meta, wave, median, ctx)
        # the failing record is recorded and leaves no partial file
        assert os.listdir(tmp_path) == ['b.xml']
        assert [uid for uid, _ in ctx.failed_records] == ['a']
        # without skip_data the same record raises
        strict_ctx = _make_xml_context(tmp_path, ['a', 'b'])
        with pytest.raises(InputValidationError):
            XMLWriter(template=template).write(
                meta, wave, median, strict_ctx)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_xsd_validation(self, tmp_path):
        meta, wave, median = _make_xml_records(n=1)
        xsd_path = _write_xsd(tmp_path)
        target = tmp_path / 'out'
        target.mkdir()
        # #### a conforming document is written, its schema compiled once
        writer = XMLWriter(
            template=_make_simple_template(), xsd_path=xsd_path)
        writer.write(meta, wave, median, _make_xml_context(target, ['a']))
        schema = writer._schema
        writer.write(meta, wave, median, _make_xml_context(target, ['b']))
        assert writer._schema is schema
        assert set(os.listdir(target)) == {'a.xml', 'b.xml'}
        # #### 'Extra' is absent from the XSD, so validation fails and the
        # record never reaches disk
        template = _make_simple_template()
        template['ECG']['Extra'] = f'{CTypes.MetaData}.rate'
        broken = tmp_path / 'broken'
        broken.mkdir()
        with pytest.raises(XMLValidationError):
            XMLWriter(template=template, xsd_path=xsd_path).write(
                meta, wave, median, _make_xml_context(broken, ['a']))
        assert os.listdir(broken) == []
        # #### strict=False tolerates elements absent from the schema
        XMLWriter(template=template, xsd_path=xsd_path, strict=False).write(
            meta, wave, median, _make_xml_context(broken, ['a']))
        assert os.listdir(broken) == ['a.xml']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_invalid_element_name_respects_skip_data(self, tmp_path):
        """
        A template key that is not a legal XML element or attribute
        name is skipped and recorded like any other per-record
        failure, instead of writing malformed XML or raising an error
        the skip handler does not catch.
        """
        meta, wave, median = _make_xml_records()
        template = {'ECG': {'1Bad': f'{CTypes.MetaData}.rate'}}
        ctx = _make_xml_context(tmp_path, ['a', 'b'], skip_data=True)
        XMLWriter(template=template).write(meta, wave, median, ctx)
        assert os.listdir(tmp_path) == []
        assert [uid for uid, _ in ctx.failed_records] == ['a', 'b']
        # without skip_data the same template raises
        strict_ctx = _make_xml_context(tmp_path, ['a', 'b'])
        with pytest.raises(InputValidationError):
            XMLWriter(template=template).write(
                meta, wave, median, strict_ctx)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_document_syntax_error_respects_skip_data(
            self, tmp_path, monkeypatch):
        """
        A document that is not well-formed XML is skipped and recorded
        like any other per-record failure when a schema is set,
        instead of aborting the whole write. `xmltodict.unparse` is
        monkeypatched to force this case directly, since
        `XMLWriter._validate_name` already blocks the one concrete
        cause (an illegal element/attribute name) before this point.
        """
        meta, wave, median = _make_xml_records()
        xsd_path = _write_xsd(tmp_path)
        target = tmp_path / 'out'
        target.mkdir()
        monkeypatch.setattr(
            'ecgprocess.writer.writer_xml.xmltodict.unparse',
            lambda *args, **kwargs: 'this is not well-formed xml',
        )
        ctx = _make_xml_context(target, ['a', 'b'], skip_data=True)
        XMLWriter(
            template=_make_simple_template(), xsd_path=xsd_path,
        ).write(meta, wave, median, ctx)
        assert os.listdir(target) == []
        assert [uid for uid, _ in ctx.failed_records] == ['a', 'b']
        # without skip_data the same malformed document raises
        strict_ctx = _make_xml_context(target, ['a', 'b'])
        with pytest.raises(etree.XMLSyntaxError):
            XMLWriter(
                template=_make_simple_template(), xsd_path=xsd_path,
            ).write(meta, wave, median, strict_ctx)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_bad_schema_file_raises_regardless_of_skip_data(self, tmp_path):
        """
        An invalid XSD schema file is a configuration error, not a
        per-record data error: it always raises, before any record is
        processed, regardless of `ctx.skip_data`.
        """
        bad_xsd = tmp_path / 'bad.xsd'
        bad_xsd.write_text('<not-a-schema/>')
        meta, wave, median = _make_xml_records(n=1)
        target = tmp_path / 'out'
        target.mkdir()
        ctx = _make_xml_context(target, ['a'], skip_data=True)
        with pytest.raises(etree.XMLSchemaParseError):
            XMLWriter(
                template=_make_simple_template(), xsd_path=str(bad_xsd),
            ).write(meta, wave, median, ctx)
        assert os.listdir(target) == []
