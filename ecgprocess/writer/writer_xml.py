"""
The template-driven XML writer.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import datetime
import json
import logging
import math
import os
import re
import tempfile
from typing import Any
import numpy as np
import xmltodict
from lxml import etree
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
    UtilsGeneralNames as UGNames,
    WriteNames,
)
from ecgprocess.errors import (
    Error_MSG,
    is_type,
    InputValidationError,
    Warn_MSG,
    XMLValidationError,
)
from ecgprocess.writer.writer_base import (
    BaseWriter,
    WriteContext,
    register_writer,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
CTypes = Core.DataTypes
# NOTE hardcoded (not __name__), see writer_base._log
_log = logging.getLogger('ecgprocess.writer')
# the characters XML 1.0 forbids outright; tab, newline and carriage
# return are the only C0 controls it allows
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_XML)
class XMLWriter(BaseWriter):
    """
    Writes one XML document per ECG UID from a user-supplied template.
    
    Each record is written as `<sanitised-UID>.xml`. The template is a
    nested `dict` following `xmltodict` conventions (a `'@name'` key is an
    attribute, a `'#text'` key is element text, a `list` value repeats the
    sibling element). A leaf string of the form `'<DataType>.<field name>'`
    is a reference resolved against that record's data, where `DataType` is
    one of `'MetaData'`, `'WaveForms'`, or `'MedianBeats'`, so one document
    may draw on all three sources at once. Any other leaf is a literal
    written out as it stands, which is how fixed values such as a namespace
    declaration or a schema version are expressed.
    
    The template is walked once at construction to collect the sources it
    reads and to catch a reference whose `DataType` is written in the wrong
    case, which raises `InputValidationError` there and then rather than
    part-way through a batch run. Whether a referenced field exists in a
    given record is settled at write time.
    
    Parameters
    ----------
    template : `dict`, `str`, or `NoneType`, default `NoneType`
        The document template, either as a `dict` or as a path to a JSON
        file holding one. `NoneType` leaves the writer unconfigured, so
        that the registry route (`writer='xml'`), which instantiates the
        class without arguments, resolves; `write` then rejects it.
    xsd_path : `str` or `NoneType`, default `NoneType`
        A path to an XSD schema. When set, each built document is
        validated against it before anything is written to disk; the
        schema is compiled once per writer instance.
    strict : `bool`, default `True`
        Passed to the XSD validation, mirroring
        :func:`ecgprocess.utils.reader_tools.validate_xml`: when False,
        errors reporting elements absent from the schema are ignored and
        all other errors still raise.
    xml_declaration : `bool`, default `True`
        Whether to prepend the `<?xml ... ?>` declaration.
    pretty : `bool`, default `True`
        Whether to indent the written document.
    encoding : `str`, default `'utf-8'`
        The document encoding, named in the XML declaration.
    
    Raises
    ------
    InputValidationError
        If a parameter has the wrong type, if a JSON template file does
        not hold an object, or if a template leaf names a data source in
        the wrong case.
    
    Notes
    -----
    Literals and references are told apart by the text before the first
    dot: a leaf is a reference only when that prefix matches a data source
    exactly, and is a literal otherwise. A misspelled source therefore
    reaches the output as literal text rather than raising, so the one
    near-miss that is caught is a prefix matching a source in every respect
    but case (`'metadata.x'`, `'WAVEFORMS.I'`). The cost of that guard is
    that a genuine literal whose prefix collides with a source name
    (`'metadata.xml'` as a filename) raises and has to be reworded.
    
    Unlike `WFDBWriter` and `FigureWriter`, this writer places no
    single-source restriction on a record: waveforms, median beats, and
    metadata may all appear in one document.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.xml'
    # the data sources a template leaf may reference
    SOURCES: tuple[str, ...] = (
        CTypes.MetaData,
        CTypes.WaveForms,
        CTypes.MedianBeats,
    )
    # the filename-legal character set; other characters map to '_'
    _INVALID_CHARS = re.compile(r'[^A-Za-z0-9_-]')
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, template: dict[str, Any] | str | None = None,
                 xsd_path: str | None = None, strict: bool = True,
                 xml_declaration: bool = True, pretty: bool = True,
                 encoding: str = 'utf-8',
                 ) -> None:
        """Initialise the XML writer."""
        is_type(template, (dict, str, type(None)))
        is_type(xsd_path, (str, type(None)))
        is_type(strict, bool)
        is_type(xml_declaration, bool)
        is_type(pretty, bool)
        is_type(encoding, str)
        self.template = self._load_template(template)
        self.xsd_path = xsd_path
        self.strict = strict
        self.xml_declaration = xml_declaration
        self.pretty = pretty
        self.encoding = encoding
        # #### walk the template eagerly: a malformed reference is a
        # configuration error and is raised here, not mid-batch. The
        # collected sources back the source-not-extracted check in `write`
        self._sources = self._collect_sources(self.template)
        # compiling an XMLSchema costs orders of magnitude more than one
        # validate() call, so it is built once and reused for all records
        self._schema: "etree.XMLSchema | None" = None
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _load_template(template: dict[str, Any] | str | None,
                       ) -> dict[str, Any] | None:
        """
        Resolve the `template` parameter to a `dict` or `NoneType`.
        
        Parameters
        ----------
        template : `dict`, `str`, or `NoneType`
            The template itself, a path to a JSON file holding one, or
            `NoneType` for an unconfigured writer.
        
        Returns
        -------
        template : `dict` [`str`, `any`] or `NoneType`
            The loaded template.
        
        Raises
        ------
        InputValidationError
            If the JSON file does not hold an object.
        """
        if not isinstance(template, str):
            return template
        with open(template) as file:
            loaded = json.load(file)
        is_type(loaded, dict, 'template')
        return loaded
    # /////////////////////////////////////////////////////////////////////////
    @classmethod
    def _parse_reference(cls, value: str, path: str,
                         ) -> tuple[str, str] | None:
        """
        Split a template leaf into its source and field name.
        
        Parameters
        ----------
        value : `str`
            The leaf value, read as `'<DataType>.<field name>'`.
        path : `str`
            The leaf's position in the template, for the error message.
        
        Returns
        -------
        reference : `tuple` [`str`, `str`] or `NoneType`
            The referenced source and the field name within it, or
            `NoneType` when the leaf is a literal string.
        
        Raises
        ------
        InputValidationError
            If the leaf names a source in the wrong case, which is a
            misspelled reference rather than a plausible literal.
        """
        # a field name may itself contain dots, a source name may not
        source, separator, field = value.partition('.')
        if separator and field:
            if source in cls.SOURCES:
                return source, field
            # only a casing mismatch is treated as a typo; any other
            # unrecognised prefix is taken at face value as a literal
            for known in cls.SOURCES:
                if source.lower() == known.lower():
                    raise InputValidationError(
                        Error_MSG.XML_SOURCE_CASING.format(
                            path, value, source, known, list(cls.SOURCES)))
        return None
    # /////////////////////////////////////////////////////////////////////////
    @classmethod
    def _collect_sources(cls, node: Any, path: str = '') -> set[str]:
        """
        Validate every leaf string and collect the sources referenced.
        
        Walks the template depth-first: dictionaries and lists are
        recursed into, leaf strings are parsed as references, and any
        other leaf (numbers, booleans, `NoneType`) is a literal passed
        through unchecked.
        
        Parameters
        ----------
        node : `any`
            The template, or a nested part of it during recursion.
        path : `str`, default `''`
            The trail to `node`, built up during recursion and reported
            when a leaf is malformed.
        
        Returns
        -------
        sources : `set` [`str`]
            The distinct `CoreData.DataTypes` values the template reads.
        
        Raises
        ------
        InputValidationError
            If any leaf string is not a valid reference.
        """
        sources: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                child = f'{path}.{key}' if path else str(key)
                sources |= cls._collect_sources(value, child)
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                sources |= cls._collect_sources(value, f'{path}[{index}]')
        elif isinstance(node, str):
            reference = cls._parse_reference(node, path)
            if reference is not None:
                sources.add(reference[0])
        return sources
    # /////////////////////////////////////////////////////////////////////////
    def _record_file_name(self, uid: Any) -> str:
        """
        Return the output filename for one record.
        
        Parameters
        ----------
        uid : `any`
            The record's unique key from `WriteContext.key_list`.
        
        Returns
        -------
        name : `str`
            The `<sanitised-UID>.xml` filename.
        """
        return self._INVALID_CHARS.sub('_', str(uid)) + self.file_ext()
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _normalize_leaf(value: Any) -> Any:
        """
        Convert one resolved value into something XML can carry.
        
        Parameters
        ----------
        value : `any`
            The value read from the record.
        
        Returns
        -------
        value : `any`
            The XML-safe value. Arrays become comma-separated text, numpy
            scalars become their Python equivalent, non-finite floats take
            their XSD spelling, dates and times are ISO-formatted, and
            `NoneType` passes through for `xmltodict` to render as an
            empty element.
        """
        if value is None:
            return None
        # an array handed to `unparse` untouched would emit one repeated
        # sibling element per sample rather than text
        if isinstance(value, np.ndarray):
            return ','.join(map(str, value.tolist()))
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            if math.isnan(value):
                return 'NaN'
            return 'INF' if value > 0 else '-INF'
        if isinstance(value, (datetime.datetime, datetime.date,
                              datetime.time)):
            return value.isoformat()
        if isinstance(value, str):
            return _CONTROL_CHARS.sub('', value)
        return value
    # /////////////////////////////////////////////////////////////////////////
    @classmethod
    def _resolve(cls, node: Any, record: dict[str, dict[str, Any]],
                 path: str = '',
                 ) -> Any:
        """
        Build one record's document by resolving every template leaf.
        
        Parameters
        ----------
        node : `any`
            The template, or a nested part of it during recursion.
        record : `dict` [`str`, `dict` [`str`, `any`]]
            The record's data, keyed by `CoreData.DataTypes` value.
        path : `str`, default `''`
            The trail to `node`, reported when a field is absent.
        
        Returns
        -------
        resolved : `any`
            The template with every reference replaced by its normalised
            value, ready for `xmltodict.unparse`.
        
        Raises
        ------
        InputValidationError
            If a referenced field is absent from the record.
        """
        if isinstance(node, dict):
            return {
                key: cls._resolve(
                    value, record, f'{path}.{key}' if path else str(key))
                for key, value in node.items()
            }
        if isinstance(node, (list, tuple)):
            return [cls._resolve(value, record, f'{path}[{index}]')
                    for index, value in enumerate(node)]
        if not isinstance(node, str):
            return node
        reference = cls._parse_reference(node, path)
        if reference is None:
            return cls._normalize_leaf(node)
        source, field = reference
        data = record[source]
        if field not in data:
            raise InputValidationError(
                Error_MSG.XML_MISSING_FIELD.format(path, node, source))
        return cls._normalize_leaf(data[field])
    # /////////////////////////////////////////////////////////////////////////
    def _validate_document(self, document: str) -> None:
        """
        Validate a built document against the configured XSD.
        
        Parameters
        ----------
        document : `str`
            The serialised XML document.
        
        Raises
        ------
        XMLValidationError
            If the document does not satisfy the schema. When `strict` is
            False, errors reporting elements absent from the schema are
            ignored and only the remaining ones raise.
        """
        # the schema is parsed from its path so that relative xs:include
        # and xs:import references resolve against its own directory
        if self._schema is None:
            self._schema = etree.XMLSchema(etree.parse(self.xsd_path))
        if self._schema.validate(
                etree.fromstring(document.encode(self.encoding))):
            return
        errors = list(self._schema.error_log)
        if not self.strict:
            errors = [err for err in errors
                      if UGNames.LXML_ERROR not in err.message]
            if not errors:
                _log.warning(Warn_MSG.XML_NOT_IN_XSD)
                return
        raise XMLValidationError([err.message for err in errors])
    # /////////////////////////////////////////////////////////////////////////
    def _write_document(self, document: str, uid: Any, target: str) -> None:
        """
        Write one document to `<target>/<sanitised-UID>.xml` atomically.
        
        The document lands in a temporary file inside `target` and is then
        moved onto its final name, so an interrupted run never leaves a
        truncated file that looks complete on the next pass.
        
        Parameters
        ----------
        document : `str`
            The serialised XML document.
        uid : `any`
            The record's unique key from `WriteContext.key_list`.
        target : `str`
            The output directory.
        """
        handle, temp_path = tempfile.mkstemp(dir=target, suffix=self.FILE_EXT)
        try:
            with os.fdopen(handle, 'wb') as file:
                file.write(document.encode(self.encoding))
            os.replace(temp_path, os.path.join(
                target, self._record_file_name(uid)))
        except BaseException:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write one XML document per ECG UID.
        
        Parameters
        ----------
        meta_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing median beat signals.
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        
        Raises
        ------
        InputValidationError
            If no template is configured, if the template reads a source
            that was not extracted, or, when `ctx.skip_data` is unset, if
            a record lacks a referenced field.
        XMLValidationError
            If a built document fails XSD validation while `ctx.skip_data`
            is unset.
        """
        # #### configuration errors raise once, before anything is
        # written; only per-record data failures reach the loop below
        if self.template is None:
            raise InputValidationError(Error_MSG.XML_NO_TEMPLATE)
        extracted = {
            CTypes.MetaData: ctx.e_meta,
            CTypes.WaveForms: ctx.e_wave,
            CTypes.MedianBeats: ctx.e_median,
        }
        missing = sorted(name for name in self._sources
                         if not extracted[name])
        if missing:
            raise InputValidationError(
                Error_MSG.XML_SOURCE_NOT_EXTRACTED.format(missing))
        # #### align the optional sources with the records
        empty: list[dict[str, Any]] = [{}] * len(ctx.key_list)
        meta_iter = meta_list if ctx.e_meta else empty
        wave_iter = wave_list if ctx.e_wave else empty
        median_iter = median_list if ctx.e_median else empty
        # #### build, validate and write one document per UID
        for uid, meta, wave, median in zip(
                ctx.key_list, meta_iter, wave_iter, median_iter,
                strict=True):
            record = {
                CTypes.MetaData: meta,
                CTypes.WaveForms: wave,
                CTypes.MedianBeats: median,
            }
            try:
                document = xmltodict.unparse(
                    self._resolve(self.template, record),
                    full_document=self.xml_declaration,
                    pretty=self.pretty,
                    encoding=self.encoding,
                )
                # validating before the write leaves nothing behind for a
                # record the schema rejects
                if self.xsd_path is not None:
                    self._validate_document(document)
                self._write_document(document, uid, ctx.target)
            except (InputValidationError, XMLValidationError) as err:
                if not ctx.skip_data:
                    raise
                ctx.failed_records.append(
                    (uid, WriteNames.XML_CAUSE.format(err)))
                _log.warning(Warn_MSG.XML_SKIPPED, uid, err)

