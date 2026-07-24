"""
The writer framework: `BaseWriter`, the `WRITERS` registry, and
`WriteContext`.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
import abc
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar
import numpy as np
import pandas as pd
from ecgprocess.constants import FileNames
from ecgprocess.errors import (
    is_type,
    Error_MSG,
    InputValidationError,
    Warn_MSG,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
# NOTE hardcoded (not __name__) so every writer submodule logs under the
# same 'ecgprocess.writer' name regardless of which file the record comes
# from; logging.getLogger caches by name so this is one shared logger.
_log = logging.getLogger('ecgprocess.writer')

# the writer registry, populated by the register_writer decorator. All
# writer classes are defined at module top level so their decorators run
# before the registry is read.
WRITERS: dict[str, type["BaseWriter"]] = {}

# type variable preserving the concrete class type through the
# register_writer decorator (a bare type[BaseWriter] return would erase
# the decorated writer's constructor signature for static analysis)
_W = TypeVar('_W', bound='BaseWriter')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@dataclass
class WriteContext(object):
    """
    Carries the state a writer needs from :class:`ECGTable`.
    
    This dataclass is constructed once per chunk by `ECGTable`
    and passed to the writer, providing (optional) access to data
    parsed/generated during runtime.  The writer callable does not need to
    initiate the class, but instead can (optionally) use WriteContext attributes.
    
    Parameters
    ----------
    e_meta : `bool`
        Whether to write metadata.
    e_wave : `bool`
        Whether to write waveform signals.
    e_median : `bool`
        Whether to write median beat signals.
    key_list : `list`
        The per-record unique key list used as the metadata index. Provides
        row identifiers for tabular output (e.g. a record ID); can optionally
        be used to index metadata.
    target : `str`
        The target output directory path; writers write all files to this
        path. Call `BaseWriter.file_names()` to get standard per-chunk
        filenames, then construct output paths as `target / filename`.
    chunk_num : `int` or `NoneType`
        Current chunk number (or None for single-chunk runs). Passed to
        `BaseWriter.file_names(chunk_num)` to generate chunk-suffixed
        filenames like 'metadata_0.tsv', 'metadata_1.tsv', etc.
    skip_data : `bool`, optional, default: `False`
        If True, records failing at the write stage are skipped and their
        (id, reason) pair appended to failed_records instead of raising an
        exception. If False, raise on the first failure. Internally this
        is set by the `ECGTable` `ignore_data` flag.
    failed_records : `list` [`tuple` [`str`, `str`]], optional, default: `[]`
        Shared mutable list of (record_id, error_reason) tuples for records
        skipped during write. On write failure: call
        `ctx.failed_records.append((record_id, str(error)))` if skip_data
        is True, then continue to the next record. At the end of write_ecg,
        these pairs are merged into FailedFiles.txt by ECGTable.
    
    Notes
    -----
    The writer can use these fields to decide which data types to write
    (e_meta, e_wave, e_median), where to write files (target),
    adding an chunk indicator to the oputs (chunk_num), and how to index output
    rows (key_list).
    
    Error handling is controlled by skip_data and failed_records.
    `failed_records` is a single list shared across every chunk of a run and
    returned to ECGTable to be optionally written as FailedFiles.txt.
    Writers must call `ctx.failed_records.append(...)` to add failures,
    reassigning `ctx.failed_records = [...]` silently breaks the link back
    to `ECGTable` and loses failure records for that chunk.
    """
    # NOTE add input tests?
    e_meta: bool
    e_wave: bool
    e_median: bool
    key_list: list[Any]
    target: str
    chunk_num: int | None
    skip_data: bool = False
    failed_records: list[tuple[str, str]] = field(default_factory=list)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class BaseWriter(abc.ABC):
    """
    Abstract base class for all ECG output writers.
    
    Concrete writers implement :meth:`write`, which receives the extracted
    per-chunk data lists and a :class:`WriteContext`.
    
    Attributes
    ----------
    FILE_EXT : `str`
        The on-disk extension (including the leading dot) applied to the
        standard data-file names returned by `file_names`. Writers that
        name their own files (e.g. the per-UID figure writer) keep the
        empty default.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT: str = ''
    # /////////////////////////////////////////////////////////////////////////
    def file_ext(self) -> str:
        """
        Return the extension for this writer's standard data files.
        
        Subclasses with an option-dependent extension (e.g. a
        compression suffix) override this method; the `FILE_EXT` class
        attribute covers the common fixed case.
        
        Returns
        -------
        ext : `str`
            The file extension, including the leading dot.
        """
        return self.FILE_EXT
    # /////////////////////////////////////////////////////////////////////////
    def file_names(self, chunk_num: int | None = None,
                   ) -> tuple[str, str, str, str, str]:
        """
        Return the standard per-chunk data-file names for this writer.
        
        The base names come from the `FileNames` constants and the
        extension from `file_ext`, so registered and user-supplied
        writers alike get standard names without `ECGTable` knowing
        their format.
        
        Parameters
        ----------
        chunk_num : `int` or `NoneType`, default `NoneType`
            Appends the chunk number with a '_' separator before the
            file extension.
        
        Returns
        -------
        tuple of strings
            The filenames for metadata, waveforms, medianbeats,
            ecg_data, and figures.
        """
        is_type(chunk_num, (int, type(None)))
        ext = self.file_ext()
        sep = '' if chunk_num is None else '_'
        chunk = '' if chunk_num is None else str(chunk_num)
        return (
            FileNames.METADATA + sep + chunk + ext,
            FileNames.WAVEFORMS + sep + chunk + ext,
            FileNames.MEDIANBEATS + sep + chunk + ext,
            # filename when combining everything into one
            FileNames.ECG_DATA + sep + chunk + ext,
            FileNames.FIGURES + sep + chunk + ext,
        )
    # /////////////////////////////////////////////////////////////////////////
    @abc.abstractmethod
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a single chunk of extracted ECG data to disk.
        
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
        """
        raise NotImplementedError
    # /////////////////////////////////////////////////////////////////////////
    def __repr__(self) -> str:
        """
        Return a constructor-like representation of the writer.
        
        Uses the runtime class name and the public instance attributes, so
        subclasses (including user-registered writers) inherit an accurate
        representation without overriding it. `str()` falls back to this
        method as no `__str__` is defined.
        """
        options = ', '.join(
            f'{name}={value!r}' for name, value in vars(self).items()
            if not name.startswith('_'))
        return f'{type(self).__name__}({options})'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def register_writer(name: str,
                    ) -> Callable[[type[_W]], type[_W]]:
    """
    Class decorator registering a writer under `name` in `WRITERS`.
    
    Parameters
    ----------
    name : `str`
        The registry key, matching a `file_type` value.
    
    Returns
    -------
    `Callable`
        The decorator adding the class to the registry.
    
    Raises
    ------
    TypeError
        If the decorated class is not a `BaseWriter` subclass.
    ValueError
        If `name` is already present in the registry.
    """
    is_type(name, str)
    # internal function
    def _decorator(cls: type[_W]) -> type[_W]:
        if not (isinstance(cls, type) and issubclass(cls, BaseWriter)):
            raise TypeError(
                f'`{getattr(cls, "__name__", cls)}` must be a `BaseWriter` '
                'subclass to be registered.')
        # check if already registered
        if name in WRITERS:
            raise ValueError(
                f'A writer is already registered under `{name}`.')
        WRITERS[name] = cls
        return cls
    return _decorator

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def resolve_writer(writer: Any) -> BaseWriter:
    """
    Normalise a user-supplied writer into a `BaseWriter` instance.
    
    Parameters
    ----------
    writer : `str`, `type`, `BaseWriter`, or `Callable`
        A registry-key string (looked up in :data:`WRITERS` and
        instantiated), a `BaseWriter` subclass (instantiated here), a
        `BaseWriter` instance (returned as-is), or a bare callable matching
        the `BaseWriter.write` signature. A bare callable bypasses the ABC
        guarantees and is wrapped without validation of its signature.
    
    Returns
    -------
    `BaseWriter`
        An object exposing a `write(meta_list, wave_list, median_list, ctx)`
        method.
    
    Raises
    ------
    ValueError
        If `writer` is a string not present in the registry.
    TypeError
        If `writer` is a class that is not a `BaseWriter` subclass, or is
        neither a `str`, `BaseWriter`, subclass, nor callable.
    """
    # if string look-up in WRITERS
    if isinstance(writer, str):
        try:
            cls = WRITERS[writer]
        except KeyError:
            raise ValueError(
                f'`{writer}` is not a registered writer; available: '
                f'{sorted(WRITERS)}.') from None
        return cls()
    # if type make sure it inherits from BaseWriter
    if isinstance(writer, type):
        if not issubclass(writer, BaseWriter):
            raise TypeError(
                f'`{writer.__name__}` must be a `BaseWriter` subclass.')
        return writer()
    # return
    if isinstance(writer, BaseWriter):
        return writer
    if callable(writer):
        return _CallableWriter(writer)
    # otherwise raise error
    raise TypeError(
        '`writer` must be a `BaseWriter` subclass, instance, or callable, '
        f'not `{type(writer).__name__}`.')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class WriterValidator:
    """
    Check a user-supplied writer against the `BaseWriter` requirements.
    
    The validation is data-free and instantiates the writer class or instance
    to inspect it once, without writing files. All detected violations are
    collected and reported in a single exception on construction; a compliant
    writer construction succeeds silently (an instance is returned).
    
    Parameters
    ----------
    writer : `type` [`BaseWriter`] or `BaseWriter`
        The writer class or instance to check.
    
    Raises
    ------
    InputValidationError
        If the writer violates the contract; the message lists every detected
        violation.
    
    Notes
    -----
    The following requirements are checked:
    
    1. the input is a `BaseWriter` subclass or instance;
    2. the write abstract methods is  implemented;
    3. `write` accepts the four data arguments
       (`meta_list`, `wave_list`, `median_list`, `ctx`); additional callables
       and parameters are accepted;
    4. That the supplied class can be instantiated without arguments, as done
       by `resolve_writer` for the class route (skipped for instance
       input);
    5. `FILE_EXT` is a `str` and, when non-empty, starts with a dot;
    6. `file_ext()` returns a `str` and `file_names()` returns the
       5-tuple of `str` filenames.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, writer: "type[BaseWriter] | BaseWriter") -> None:
        """
        Construct and validate the supplied writer.
        
        Parameters
        ----------
        writer : `type` [`BaseWriter`] or `BaseWriter`
            The writer class or instance to validate.
        
        Raises
        ------
        InputValidationError
            If the writer violates the contract.
        """
        self._validate(writer)
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def describe() -> None:
        """
        Print a plain-language checklist of the `BaseWriter` contract.
        
        Useful as an interactive reference in REPL or notebooks; displays
        the required methods, optional overrides, and WriteContext fields
        with their purposes.
        """
        checklist = (
            "BaseWriter contract checklist:\n"
            "\n"
            "Required method:\n"
            "\n"
            "  write(meta_list, wave_list, median_list, ctx) \n"
            "      process and write data to disk using ctx.target as output \n"
            "      directory. Should respect ctx.e_meta, ctx.e_wave, \n "
            "      ctx.e_median flags to conditionally write each data type. \n"
            "      On write failure, append (record_id, error_reason) to \n "
            "      ctx.failed_records, and skip the record if ctx.skip_data is \n"
            "      True.\n"
            "\n"
            "Optional overrides (have sensible defaults):\n"
            "\n"
            "  FILE_EXT \n"
            "      class attribute (str) for file extension including\n"
            "      dot (e.g. '.json'). Default ''. Used by file_names().\n"
            "  file_ext() \n"
            "      return FILE_EXT or a runtime-computed extension\n"
            "      (e.g. with compression suffix). Called by file_names().\n"
            "  file_names(chunk_num=None) \n"
            "      return a tuple of at least one filename string. Base \n "
            "      implementation returns the standard 5-tuple \n "
            "      (metadata, waveforms, medianbeats, ecg_data, figures); \n "
            "      derive names from FileNames constants + file_ext()\n"
            "      + optional chunk suffix. Use only the slots relevant to your\n"
            "      format and ignore the rest.\n"
            "\n"
            "WriteContext fields (passed to write()):\n"
            "  All fields are populated internally by ECGTable and provided \n"
            "  the writer class to optionally incorporate. The fields are \n"
            "  list here as FYI. \n"
            "\n"
            "  e_meta (bool) \n"
            "      include metadata in output\n"
            "  e_wave (bool) \n"
            "      include waveform signals in output\n"
            "  e_median (bool) \n"
            "      include median beat signals in output\n"
            "  key_list (list) \n"
            "      per-record unique identifiers (ECGTable's index); may be \n"
            "      used as row keys in outputs\n"
            "  target (str) \n"
            "      output directory path; write files here\n"
            "  chunk_num (int or None) \n"
            "      current chunk number (or None for single-chunk runs); \n"
            "      passed to file_names() for naming\n"
            "  skip_data (bool, default False) \n"
            "      if True, skip records\n"
            "      that fail during write; if False, raise on failure\n"
            "  failed_records (list, default []) \n"
            "      shared mutable list of (record_id, error_reason) tuples; \n"
            "      append failures here, never reassign the list or ECGTable \n"
            "      will not see them\n"
            "\n"
        )
        print(checklist)
    # /////////////////////////////////////////////////////////////////////////
    def _validate(self, writer: "type[BaseWriter] | BaseWriter") -> None:
        """
        Validate the supplied writer and raise if any violations found.
        
        Parameters
        ----------
        writer : `type` [`BaseWriter`] or `BaseWriter`
            The writer to validate.
        
        Raises
        ------
        InputValidationError
            If any contract violations are detected.
        """
        # #### CRITERION 1
        # #### resolve the class/instance forms (the documented routes)
        if isinstance(writer, type) and issubclass(writer, BaseWriter):
            cls = writer
            instance = None
        elif isinstance(writer, BaseWriter):
            cls = type(writer)
            instance = writer
        else:
            raise InputValidationError(Error_MSG.WRITER_INVALID.format(
                1, '- ' + Error_MSG.WRITER_NOT_WRITER.format(writer)))
        violations: list[str] = []
        # #### CRITERION 2
        # #### unimplemented abstract methods (class input only: a live
        # instance could not have been constructed with any remaining)
        abstract = getattr(cls, '__abstractmethods__', frozenset())
        if abstract:
            violations.append(
                Error_MSG.WRITER_ABSTRACT.format(', '.join(sorted(abstract))))
        # #### CRITERION 3
        # #### the write signature must bind the four data arguments
        # the placeholders stand in for (meta_list, wave_list, median_list,
        # ctx); `bind` accepts variadic and extra defaulted parameters
        placeholders = ([], [], [], None)
        try:
            if instance is not None:
                sig = inspect.signature(instance.write)
                sig.bind(*placeholders)
            else:
                # the unbound function keeps `self`; NoneType stands in
                sig = inspect.signature(cls.write)
                sig.bind(None, *placeholders)
        except (TypeError, ValueError):
            # bind()'s TypeError reads backwards; report the signature
            if instance is None:
                sig = sig.replace(
                    parameters=list(sig.parameters.values())[1:])
            violations.append(Error_MSG.WRITER_SIGNATURE.format(sig))
        # #### CRITERION 4
        # #### the class route requires bare instantiation (resolve_writer
        # calls `cls()`); skipped for abstract classes and instance input
        if instance is None and not abstract:
            try:
                instance = cls()
            # NOTE broad on purpose: probing an untrusted user constructor
            except Exception as err:
                violations.append(Error_MSG.WRITER_INIT.format(err))
        # #### CRITERION 5
        # #### FILE_EXT backs the standard filename derivation
        file_ext_attr = getattr(
            instance if instance is not None else cls, 'FILE_EXT', '')
        if not isinstance(file_ext_attr, str):
            violations.append(Error_MSG.WRITER_FILE_EXT_TYPE.format(
                type(file_ext_attr).__name__))
        elif file_ext_attr and not file_ext_attr.startswith('.'):
            violations.append(
                Error_MSG.WRITER_FILE_EXT_DOT.format(file_ext_attr))
        # #### CRITERION 6
        # #### probe the filename machinery on the instance; the calls are
        # guarded broadly so one failure does not hide the other checks
        if instance is not None:
            try:
                ext = instance.file_ext()
                if not isinstance(ext, str):
                    violations.append(Error_MSG.WRITER_EXT_RETURN.format(
                        type(ext).__name__))
            except Exception as err:
                violations.append(
                    Error_MSG.WRITER_CALL_RAISED.format('file_ext', err))
            # a non-str FILE_EXT already malforms the derived names; skip
            # the derived call instead of double-reporting
            if isinstance(file_ext_attr, str):
                try:
                    names = instance.file_names()
                    if not isinstance(names, tuple):
                        violations.append(
                            Error_MSG.WRITER_NAMES_RETURN.format(
                                type(names).__name__))
                    elif len(names) < 1:
                        violations.append(
                            Error_MSG.WRITER_NAMES_LEN.format(len(names)))
                    else:
                        for pos, name in enumerate(names):
                            if not isinstance(name, str):
                                violations.append(
                                    Error_MSG.WRITER_NAMES_STR.format(
                                        pos, type(name).__name__))
                except Exception as err:
                    violations.append(Error_MSG.WRITER_CALL_RAISED.format(
                        'file_names', err))
        # #### raise once, listing every violation
        if violations:
            raise InputValidationError(Error_MSG.WRITER_INVALID.format(
                len(violations),
                '\n'.join('- ' + violation for violation in violations)))
    # /////////////////////////////////////////////////////////////////////////

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class _CallableWriter(BaseWriter):
    """
    Adapter wrapping a bare callable as a :class:`BaseWriter`.
    
    The callable must accept `(meta_list, wave_list, median_list, ctx)`.
    """
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, func: Callable[..., Any]) -> None:
        """
        Initialise the adapter.
        
        Parameters
        ----------
        func : `Callable`
            The callable to delegate `write` calls to.
        """
        self._func = func
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Delegate the write call to the wrapped callable.
        
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
        """
        return self._func(meta_list, wave_list, median_list, ctx)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# helpers
def _meta_to_array(meta_list: list[dict[str, Any]], numeric_meta: bool,
                   ) -> tuple["np.ndarray", list[str]]:
    """
    Build a metadata array and its column header from a list of dicts.
    
    Parameters
    ----------
    meta_list : `list` [`dict` [`str`, `any`]]
        A list of per-record metadata dictionaries.
    numeric_meta : `bool`
        When True, non-numeric columns are dropped (with a warning) so the
        result is a purely numeric array.
    
    Returns
    -------
    array : `np.ndarray`
        The metadata as a 2D array.
    header : `list` [`str`]
        The retained column names, in array-column order.
    """
    tab = pd.DataFrame(meta_list)
    if numeric_meta:
        old_cols = set(tab.columns)
        tab = tab.select_dtypes(include=[np.number])
        drop_cols = old_cols - set(tab.columns)
        if len(drop_cols) > 0:
            _log.warning(Warn_MSG.DROP_NONE_NUMERIC, drop_cols)
    return tab.to_numpy(), list(tab.columns)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _write_metadata_header(target: str, header: list[str]) -> None:
    """
    Write the metadata column names to a `header_metadata.txt` sidecar.
    
    The array formats (`.npz`, `.tfrecord`) store metadata as a bare numeric
    array with no column labels, so the header is written alongside as a
    line-numbered lookup.
    
    Parameters
    ----------
    target : `str`
        The directory the header file is written to.
    header : `list` [`str`]
        The metadata column names, in array-column order.
    """
    with open(os.path.join(target, FileNames.META_HEADER), 'w') as file:
        # NOTE line numbering starts at 1 to match the sidecar convention.
        for line_number, head in enumerate(header, start=1):
            file.write(f"{line_number}\t{head}\n")
