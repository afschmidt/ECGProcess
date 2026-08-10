"""
Error handling for ECGProcess.
"""
import os
import inspect
import warnings
import pandas as pd

from os import PathLike
from typing import Any, Type

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class InputValidationError(Exception):  # pragma: no cover
    """
    Exception raised when a function argument fails a type or value check.
    """

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_param_name(param:Any) -> str | None:
    '''
    Gets the name of `param` from the caller's local scope.

    Parameters
    ----------
    param : `Any`
        The object whose variable name is to be resolved.

    Returns
    -------
    name : `str` or `None`
        The variable name as a string, or `None` if it cannot be resolved.

    Notes
    -----
    `inspect.currentframe()` returns `None` on Python implementations
    without stack-frame support (e.g. PyPy), and `frame.f_back` returns
    `None` once the top of the call stack is reached. Each hop is
    guarded so a missing frame yields `None` rather than an
    `AttributeError`.
    '''
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back
    if frame is not None:
        frame = frame.f_back
    if frame is None:
        return None
    param_names =\
        [name for name, value in frame.f_locals.items() if value is param]
    return param_names[0] if param_names else None

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def is_type(param: Any, types: tuple[Type, ...] | Type,
            param_name: str | None=None) -> bool:
    """
    Checks if a given parameter matches any of the supplied types.
    
    Parameters
    ----------
    param : `Any`
        Object to test.
    types : `Type` or `tuple` [`Type`]
        Either a single type, or a tuple of types to test against.
    param_name : `str` or `None`, optional
        Name of the parameter, used in the error message. Resolved
        automatically from the caller's scope when not supplied.
    
    Returns
    -------
    result : `bool`
        `True` if the parameter is an instance of any of the given types.
    
    Raises
    ------
    InputValidationError
        If `param` is not an instance of any type in `types`.
    """
    if not isinstance(param, types):
        if param_name is None:
            param_name = get_param_name(param)
        raise InputValidationError(
            f"Expected any of [{types}], "
            f"got {type(param)}; Please see parameter: `{param_name}`."
        )
    return True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def is_df(df: Any) -> bool:  # pragma: no cover
    """
    Checks if object is a pd.DataFrame.
    
    Parameters
    ----------
    df: `Any`
    
    Returns
    -------
    True if the df is a pd.DataFrame. Raises InputValidationError otherwise.
    """
    return is_type(df, pd.DataFrame)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def is_series_type(column: pd.Series | pd.DataFrame,
                   types: tuple[Type] | Type,
                   ) -> bool:
    """
    Checks if a `pd.DataFrame` or `pd.Series` contains the supplied type.
    
    Parameters
    ----------
    column : `pd.Series` or `pd.DataFrame`
        The column or frame whose elements are to be tested.
    types : `Type` or `tuple` [`Type`]
        Either a single type, or a tuple of types to test against.
    
    Returns
    -------
    result : `bool`
        `True` if all elements match any of the given types.
    
    Raises
    ------
    InputValidationError
        If any element is not an instance of any type in `types`.
    
    Notes
    -----
    Tests each element individually rather than relying on dtype inference.
    """
    # check input
    is_type(column, (pd.DataFrame, pd.Series))
    # run tests
    if isinstance(column, pd.Series):
        [is_type(col, types) for col in column]
    elif isinstance(column, pd.DataFrame):
        for _, col in column.items():
            [is_type(co, types) for co in col]
    # return
    return True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def same_len(object1: Any, object2: Any,
             object_names:list[str] | None=None,
             ) -> bool:
    """
    Check if two objects have the same length.
    
    Parameters
    ----------
    object1, object2 : `Any`
        Any type of object with a `__len__` method.
    object_names : `list` [`str`] or `None`, optional
        Names of the two objects, included in the error message when
        lengths differ.
    
    Returns
    -------
    result : `bool`
        `True` if both objects have the same length.
    
    Raises
    ------
    ValueError
        If the lengths differ, or if `object_names` does not contain
        exactly two strings.
    """
    n1 = len(object1)
    n2 = len(object2)
    if object_names is None:
        object_names = ['object1', 'object2']
    elif len(object_names) !=2:
        raise ValueError('`object_names` should be `NoneType` or contain '
                         'two strings')
    # the actual test
    if n1 != n2:
        raise ValueError(
            "The length of `{0}`: {1}, does not match "
            "the length of `{2}`: {3}.".format(
                object_names[0], n1, object_names[1], n2)
        )
    return True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def are_columns_in_df(
    df: pd.DataFrame, expected_columns: list[str] | str,
    warning: bool=False
) -> bool:
    """
    Checks if all expected columns are present in a `pandas.DataFrame`.
    
    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to inspect.
    expected_columns : `list` [`str`] or `str`
        A single column name or a list of column names to check for.
    warning : `bool`, default `False`
        If `True`, issue a `UserWarning` instead of raising an error.
    
    Returns
    -------
    result : `bool`
        `True` if all expected columns are present; `False` if any are
        missing and `warning` is `True`.
    
    Raises
    ------
    InputValidationError
        If any expected columns are absent and `warning` is `False`.
    """
    # constant
    message = "The following columns are missing from the pandas.DataFrame: {}"
    res = True
    # tests
    expected_columns_set: set[str] = set(expected_columns) if isinstance(
        expected_columns, list
    ) else set([expected_columns])
    
    missing_columns = expected_columns_set - set(df.columns)
    # return
    if missing_columns:
        if warning == False:
            raise InputValidationError(
                message.format(missing_columns)
            )
        else:
            warnings.warn(
                message.format(missing_columns)
            )
            res = False
    return res

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def string_to_list(object:Any) -> Any | list[str]:
    '''
    Checks if `object` is a string and wraps this in a list, returns the
    original object if it is not a string.
    
    Parameters
    ----------
    object : `Any`
        Any object that might be a string.
    
    Returns
    -------
    string wrapped in a list or the original object type.
    '''
    if isinstance(object, str):
        return [object]
    else:
        return object

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _check_readable(path: str | PathLike) -> None:  # pragma: no cover
    """
    Do we have read access. Note this should work on a directory or file.
    
    Parameters
    ----------
    path: `str` or `PathLike`
        A path to a directory or file.
    """
    if os.access(path, os.R_OK) == False:
        raise PermissionError('You do not have read-access to: `{}`'.\
                              format(path))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _check_presence(path: str | PathLike) -> None:
    """
    Check if a directory path exists.
    
    Parameters
    ----------
    path : `str` or `PathLike`
        Path to a directory.
    
    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    NotADirectoryError
        If the path exists but is not a directory.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f'The path `{path}` does not exist.'
        )
    if not os.path.isdir(path):
        raise NotADirectoryError(
            f'The path `{path}` exists but is not a directory.'
        )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _check_is_file(path: str | PathLike) -> None:
    """
    Check if a file path exists.
    
    Parameters
    ----------
    path : `str` or `PathLike`
        Path to a file.
    
    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    IsADirectoryError
        If the path exists but is not a regular file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f'The file `{path}` does not exist.'
        )
    if not os.path.isfile(path):
        raise IsADirectoryError(
            f'The path `{path}` exists but is not a regular file.'
        )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# error messages
class Error_MSG(object):  # pragma: no cover
    '''
    A collection of error messages.
    '''
    MISSING_SIGNAL = 'There is no `{}` data available.'
    MISSING_DICOM='`{}` not found in DICOM file.'
    MISSING_XML='`{}` not found in XML file.'
    MISSING_KEY='key `{}` not found in object `{}`.'
    MISSING_LEADS=(
        "record {!r} has a partially-extracted lead set: at least one "
        "configured lead is present but the following configured lead(s) "
        "were not extracted (None): {}. Set `ignore_missing_leads=True` "
        "on the ECGTable call to skip such records instead of raising."
    )
    MISSING_ATTR='attribute `{}` not found in object `{}`.'
    CHOICE_PARM='`{}` is constrained to `{}`.'
    CHUNK_NOT_POSITIVE=(
        '`chunk` must be a positive `int` or `NoneType`, got `{}`.'
    )
    MISSING_PATH_INSTANCE="Please supply either `path` or `{}`, but not both."
    MISSING_TENSORFLOW=(
        "TensorFlow is required for the `tensorflow` writer. Install it "
        "with `pip install ecgprocess[tensorflow]` or "
        "`conda install tensorflow`."
    )
    SOURCE_NOT_EXTRACTED=(
        "{} source={!r} requires the corresponding source to be "
        "extracted; enable extract_wave/extract_median accordingly."
    )
    DUAL_SOURCE=(
        "{} requires a single signal source, but both WaveForms "
        "and MedianBeats are extracted. Disable one extraction flag "
        "(extract_wave/extract_median) or run write_ecg once per source."
    )
    MISSING_WFDB=(
        "wfdb is required for the `wfdb` writer. Install it with "
        "`pip install ecgprocess[wfdb]` or `conda install wfdb`."
    )
    WFDB_MISSING_SF=(
        "WFDBWriter requires the processed sampling frequency metadata "
        "`{}`; run the reader with resampling enabled "
        "(`resample_500=True`) so this field is populated, or use a "
        "different writer."
    )
    WFDB_MISSING_LEAD=(
        "WFDBWriter requires every lead in record {!r} to be present "
        "(no None values); missing lead(s): {}."
    )
    WFDB_UNEQUAL_LENGTH=(
        "WFDBWriter requires every lead in record {!r} to share one "
        "sample length; got lengths {}."
    )
    ANNOTATE_SPEC=(
        "each annotation spec requires 'text' (`str`) and 'xy' (a 2-item "
        "tuple of numbers); got {!r}."
    )
    ANNOTATE_MISSING_KEY=(
        'annotation template {!r} references metadata key {!r} which is '
        'missing or None.'
    )
    ANNOTATE_NEEDS_META=(
        'FigureWriter annotate templates reference MetaData, but metadata '
        'extraction is disabled; enable metadata extraction or use literal '
        'annotation strings.'
    )
    ANNOTATE_RECORD='record {!r}: {}'
    PIXEL_SHAPE_MISMATCH=(
        'PixelWriter stacking requires every rendered figure in a chunk '
        'to share the same (height, width); got shapes {}. Render all '
        'records with one fixed figure size '
        '(`ECGStyle(figsize=..., dpi=...)`). '
    )
    XML_SOURCE_CASING=(
        'XMLWriter template leaf {} reads {!r}, whose prefix {!r} differs '
        'only in case from the data source {!r}. Correct the casing to '
        'reference that source; if the value was meant as a literal '
        'string, change it so its prefix no longer resembles a source '
        'name (only {} are recognised).'
    )
    XML_NO_TEMPLATE=(
        'XMLWriter requires a template; pass one to the constructor '
        '(`XMLWriter(template=...)`) instead of selecting the writer by '
        'its registry key alone.'
    )
    XML_MISSING_FIELD=(
        'template leaf {} references {!r}, which is absent from this '
        "record's {} data."
    )
    XML_SOURCE_NOT_EXTRACTED=(
        'XMLWriter template references the source(s) {}, which were not '
        'extracted; enable the corresponding extract_meta/extract_wave/'
        'extract_median flag(s), or drop those references from the '
        'template.'
    )
    WRITER_INVALID=(
        'the supplied writer failed validation with {} violation(s):\n{}'
    )
    WRITER_NOT_WRITER='`{}` is not a `BaseWriter` subclass or instance.'
    WRITER_ABSTRACT='abstract methods are not implemented: {}.'
    WRITER_SIGNATURE=(
        '`write` should accept four arguments (meta_list, '
        'wave_list, median_list, ctx); found signature `{}` instead.'
    )
    WRITER_SIGNATURE_UNAVAILABLE=(
        "`write`'s signature could not be inspected ({}); it should "
        'accept four arguments (meta_list, wave_list, median_list, ctx).'
    )
    WRITER_INIT='the class cannot be instantiated without arguments: {}.'
    WRITER_FILE_EXT_TYPE='`FILE_EXT` must be a `str`, not `{}`.'
    WRITER_FILE_EXT_DOT=(
        'a non-empty `FILE_EXT` must start with a dot; got `{}`.'
    )
    WRITER_CALL_RAISED='`{}()` raised during validation: {}.'
    WRITER_EXT_RETURN='`file_ext()` must return a `str`, not `{}`.'
    WRITER_NAMES_RETURN='`file_names()` must return a `tuple`, not `{}`.'
    WRITER_NAMES_LEN='`file_names()` must return at least 1 filename, got {}.'
    WRITER_NAMES_STR='`file_names()` element {} must be a `str`, not `{}`.'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class Warn_MSG(object):  # pragma: no cover
    '''
    A collection of warning messages.
    '''
    MISSING_TAG='The following tags could not be found: {}.'
    NUMB_IS_NONE = '`{}` is NoneType, cannot convert to numerical.'
    DROP_NONE_NUMERIC = ('The following non-numerical columns were '
                         'dropped when converting data to numpy '
                         'arrays: %s.')
    RESAMPLE_NO_DURATION = (
        'Resampling to 500 Hz was requested but the {} duration could '
        'not be calculated (its sampling number or the sampling '
        'frequency is None); resampling skipped for this source.'
    )
    ANNOTATE_SKIPPED = ('record %s was skipped and recorded due to a '
                        'failed annotation: %s')
    PIXEL_EMPTY_CHUNK = ('all records in the chunk were skipped; no '
                         'pixel tensor was written.')
    XML_SKIPPED = ('record %s was skipped and recorded due to a failed '
                   'XML export: %s')
    XML_NOT_IN_XSD = ('the written XML is valid, ignoring elements not '
                      'present in the supplied XSD (strict=False).')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# error messages
class STDOUT_MSG(object):  # pragma: no cover
    '''
    A collection of stdout messages.
    '''
    PROCESSING_PATH = 'Processing file: {}'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class MissingTagError(Exception):  # pragma: no cover
    '''
    Raises an error identifying the missing DICOM tag.
    '''
    def __init__(self, tag_name, message: str | None = None):
        """
        Initialise MissingTagError.
        
        Parameters
        ----------
        tag_name : `str`
            Name of the DICOM tag that could not be found.
        message : `str` or `None`, optional
            A fully-formed error message. When supplied it is used
            verbatim instead of the default ``"Tag '<tag_name>' is
            missing."`` template, allowing callers to name a record and its
            missing leads.
        """
        self.tag_name = tag_name
        super().__init__(
            message if message is not None else f"Tag '{tag_name}' is missing."
        )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class NotCalledError(Exception):  # pragma: no cover
    """
    Exception raised when a required __call__ method has not been used.
    """
    def __init__(self, message="__call__ method has not been invoked."):
        """
        Initialise NotCalledError.
        
        Parameters
        ----------
        message : `str`, optional
            Human-readable description of the error.  Defaults to a
            message indicating that the ``__call__`` method was not invoked.
        """
        self.message = message
        super().__init__(self.message)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class FileValidationError(Exception):  # pragma: no cover
    '''
    General exception raised when a file was not valid
    '''
    def __init__(self, message="File failed to validate."):
        """
        Initialise FileValidationError.
        
        Parameters
        ----------
        message : `str`, optional
            Human-readable description of the error.  Defaults to a
            generic file-validation failure message.
        """
        self.message = message
        super().__init__(self.message)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class XMLValidationError(FileValidationError):
    """
    Exception raised when the XML and XSD file are incompatible.
    """
    def __init__(self, errors: list[str]):
        """
        Initialise XMLValidationError.
        
        Parameters
        ----------
        errors : `list` [`str`]
            Validation error messages reported by the XSD validator.
        
        Raises
        ------
        XMLValidationError
            Always raised; carries a combined error message built from
            the supplied ``errors`` list.
        """
        custom_message = (
            "XML validation failed due to the following issues:\n"
            + "\n".join(errors)
        )
        super().__init__(custom_message)
