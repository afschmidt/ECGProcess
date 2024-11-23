"""Provides centralised access to example data sets that can be used in tests
and also in example code and/or jupyter notebooks.

Notes
-----
Data can be "added" either through functions that generate the data on the fly
or via functions that load the data from a static file located in the
``example_data`` directory. The data files being added  should be as small as
possible (i.e. kilobyte/megabyte range). The dataset functions should be
decorated with the ``@dataset`` decorator, so the example module knows about
them. If the function is loading a dataset from a file in the package, it
should look for the path in ``_ROOT_DATASETS_DIR``.

Examples
--------

Registering a function as a dataset providing function:

>>> @dataset
>>> def dummy_data(*args, **kwargs):
>>>     \"\"\"A dummy dataset function that returns a small list.
>>>
>>>     Returns
>>>     -------
>>>     data : `list`
>>>         A list of length 3 with ``['A', 'B', 'C']``
>>>
>>>     Notes
>>>     -----
>>>     This function is called ``dummy_data`` and has been decorated with a
>>>     ``@dataset`` decorator which makes it available with the
>>>     `example_data.get_data(<NAME>)` function and also
>>>     `example_data.help(<NAME>)` functions.
>>>     \"\"\"
>>>     return ['A', 'B', 'C']

The dataset can then be used as follows:

>>> from ecgprocess.example_data import examples
>>> examples.get_data('dummy_data')
>>> ['A', 'B', 'C']

A dataset function that loads a dataset from file, these functions should load
 from the ``_ROOT_DATASETS_DIR``:

>>> @dataset
>>> def dummy_load_data(*args, **kwargs):
>>>     \"\"\"A dummy dataset function that loads a string from a file.
>>>
>>>     Returns
>>>     -------
>>>     str_data : `str`
>>>         A string of data loaded from an example data file.
>>>
>>>     Notes
>>>     -----
>>>     This function is called ``dummy_data`` and has been decorated with a
>>>     ``@dataset`` decorator which makes it available with the
>>>     `example_data.get_data(<NAME>)` function and also
>>>     `example_data.help(<NAME>)` functions. The path to this dataset is
>>>     built from ``_ROOT_DATASETS_DIR``.
>>>     \"\"\"
>>>     load_path = os.path.join(_ROOT_DATASETS_DIR, "string_data.txt")
>>>     with open(load_path) as data_file:
>>>         return data_file.read().strip()

The dataset can then be used as follows:

>>> from ecgprocess.example_data import examples
>>> examples.get_data('dummy_load_data')
>>> 'an example data string'
"""
import os
import re
import pandas as pd
import numpy as np

# The name of the example datasets directory
_EXAMPLE_DATASETS = "example_datasets"
"""The example dataset directory name (`str`)
"""

_ROOT_DATASETS_DIR = os.path.join(os.path.dirname(__file__), _EXAMPLE_DATASETS)
"""The root path to the dataset files that are available (`str`)
"""

_DATASETS = dict()
"""This will hold the registered dataset functions (`dict`)
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def dataset(func):
    """Register a dataset generating function. This function should be used as
    a decorator.
    
    Parameters
    ----------
    func : `function`
        The function to register as a dataset. It is registered as under the
        function name.
    
    Returns
    -------
    func : `function`
        The function that has been registered.

    Raises
    ------
    KeyError
        If a function of the same name has already been registered.

    Notes
    -----
    The dataset function should accept ``*args`` and ``**kwargs`` and should be
    decorated with the ``@dataset`` decorator.

    Examples
    --------
    Create a dataset function that returns a dictionary.

    >>> @dataset
    >>> def get_dict(*args, **kwargs):
    >>>     \"\"\"A dictionary to test or use as an example.
    >>>
    >>>     Returns
    >>>     -------
    >>>     test_dict : `dict`
    >>>         A small dictionary of string keys and numeric values
    >>>     \"\"\"
    >>>     return {'A': 1, 'B': 2, 'C': 3}
    >>>
    
    The dataset can then be used as follows:

    >>> from ecgprocess.example_data import examples
    >>> examples.get_data('get_dict')
    >>> {'A': 1, 'B': 2, 'C': 3}
    
    """
    try:
        _DATASETS[func.__name__]
        raise KeyError("function already registered")
    except KeyError:
        pass

    _DATASETS[func.__name__] = func
    return func


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_data(name, *args, **kwargs):
    """Central point to get the datasets.

    Parameters
    ----------
    name : `str`
        A name for the dataset that should correspond to a registered
        dataset function.
    *args
        Arguments to the data generating functions
    **kwargs
        Keyword arguments to the data generating functions

    Returns
    -------
    dataset : `Any`
        The requested datasets
    """
    try:
        return _DATASETS[name](*args, **kwargs)
    except KeyError as e:
        raise KeyError("dataset not available: {0}".format(name)) from e


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def list_datasets():
    """List all the registered datasets.
    
    Returns
    -------
    datasets : `list` of `tuple`
        The registered datasets. Element [0] for each tuple is the dataset name
        and element [1] is a short description captured from the docstring.
    """
    datasets = []
    for d in _DATASETS.keys():
        desc = re.sub(
            r'(Parameters|Returns).*$', '', _DATASETS[d].__doc__.replace(
                '\n', ' '
            )
        ).strip()
        datasets.append((d, desc))
    return datasets


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def help(name):
    """Central point to get help for the datasets.
    
    Parameters
    ----------
    name : `str`
        A name for the dataset that should correspond to a unique key in the
        DATASETS module level dictionary.
    
    Returns
    -------
    help : `str`
        The docstring for the function
    """
    docs = ["Dataset: {0}\n{1}\n\n".format(name, "-" * (len(name) + 9))]
    try:
        docs.extend(
            ["{0}\n".format(re.sub(r"^\s{4}", "", i))
             for i in _DATASETS[name].__doc__.split("\n")]
        )
        return "".join(docs)
    except KeyError as e:
        raise KeyError("dataset not available: {0}".format(name)) from e


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def dummy_data():
    """A dummy dataset function that returns a small list.

    Returns
    -------
    data : `list`
        A list of length 3 with ``['A', 'B', 'C']``

    Notes
    -----
    This function is called ``dummy_data`` and has been decorated with a
    ``@dataset`` decorator which makes it available with the
    `example_data.get_data(<NAME>)` function and also
    `example_data.help(<NAME>)` functions.
    """
    return ['A', 'B', 'C']

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def dummy_load_data():
    """A dummy dataset function that loads a string from a file.

    Returns
    -------
    str_data : `str`
        A string of data loaded from an example data file.

    Notes
    -----
    This function is called ``dummy_data`` and has been decorated with a
    ``@dataset`` decorator which makes it available with the
    `example_data.get_data(<NAME>)` function and also
    `example_data.help(<NAME>)` functions. The path to this dataset is built
    from ``_ROOT_DATASETS_DIR``.
    """
    load_path = os.path.join(_ROOT_DATASETS_DIR, "string_data.txt")
    with open(load_path) as data_file:
        return data_file.read().strip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def list_data_paths():
    """
    Returns the paths to the available example datasets.
    
    Returns
    -------
    paths: dict
        The data names (keys) and paths (values) available in ECGProcess.
    """
    # paths dictionary
    paths_dict = {
        'example_dicom_1': os.path.join(
            _ROOT_DATASETS_DIR, 'example-DICOM1.dcm'),
        'example_dicom_2': os.path.join(
            _ROOT_DATASETS_DIR, 'example-DICOM2.dcm'),
    }
    # return
    return paths_dict

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def data_configuration(path=None) -> str:
    """
    Returns a toy example of a data configuration file as string.
    
    Parameters
    ----------
    path : str, default None
        An optional path to write the text to disk.

    Return
    str :
        The formatted configuration file.
    """
    text = (
        "[WaveForms]\n"
        "Attribute1\n"
        "[MedianBeats]\n"
        "Attribute2\n"
        "[MetaData]\n"
        "sampling frequency (original)\tSamplingFrequency\n"
        "sampling number (waveforms)\tNumberOfWaveformSamples\n"
        "Birthdate\tPatientBirthDate\n"
        "[OtherData]\n"
        "ChannelSampleSkew\tChannelSampleSkew"
    )
    # If a file path is provided, write the text to the file
    if path:
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    
    return text
