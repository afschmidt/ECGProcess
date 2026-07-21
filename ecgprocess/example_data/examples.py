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
import ecgprocess.utils.config_tools as config_utils
from tempfile import NamedTemporaryFile
from ecgprocess.constants import CoreData as Core
CLeads = Core.Leads
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
def list_dicom_paths():
    """
    Returns the paths to the available DICOM example datasets.
    
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
def list_xml_paths():
    """
    Returns the paths to available XML and XSD schema paths.
    
    Returns
    -------
    paths: dict
        The data names (keys) and paths (values) available in ECGProcess.
    """
    FILENAME='example-XML1'
    # paths dictionary
    paths_dict = {
        'example_1': os.path.join(
            _ROOT_DATASETS_DIR, FILENAME+'.xml'),
        'example_1_schema': os.path.join(
            _ROOT_DATASETS_DIR, FILENAME+'.xsd'),
        'example_1_schema_error': os.path.join(
            _ROOT_DATASETS_DIR, FILENAME+'_error.xsd'),
    }
    # return
    return paths_dict

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def config_file(path=None, text:None | dict[str, list[str]]=None) -> str:
    """
    Returns a toy example of a data configuration file as a string or uses
    user-supplied text if provided in dictionary format.
    
    Parameters
    ----------
    path : `str`, default None
        An optional path to write the text to disk. Uses utf-8 file encoding.
    user_text : `dict` [`str`, `list` [`str`]], default None
        Configuration content specified as a dictionary. Each key represents a
        header (enclosed in square brackets in the output), and the
        corresponding value is a list of attributes or entries. Tab characters
        in list items are preserved, enabling target-source assignments in the
        generated file.
    
    Returns
    -------
    str
        The formatted configuration file.
    
    Examples
    --------
        >>> custom_text = {
        ...     "CustomSection1": ["CustomAttribute1", "CustomAttribute2"],
        ...     "MetaData": ["CustomData\tCustomValue"],
        ...     "AdditionalInfo": ["Info1", "Info2"],
        ... }
        >>> print(data_configuration(user_text=custom_text))
        [CustomSection1]
        CustomAttribute1
        CustomAttribute2
        [MetaData]
        CustomData	CustomValue
        [AdditionalInfo]
        Info1
        Info2
    """
    # Default configuration
    default_text = {
        "WaveForms": [
            "I\tLead_I_name",
            "aVF\tLead_aVF_name",
        ],
        "MedianBeats": [
            "II\tLead_II_name",
        ],
        "MetaData": [
            "sampling frequency (original)\tSamplingFrequency",
            "sampling number (waveforms)\tNumberOfWaveformSamples",
            "Birthdate\tPatientBirthDate",
        ],
        "OtherData": [
            "ChannelSampleSkew\tChannelSampleSkew",
        ],
    }
    # Use default text if user_text is not provided
    config = text or default_text
    # Generate the formatted text
    text_lines = []
    for header, attributes in config.items():
        text_lines.append(f"[{header}]")
        text_lines.extend(attributes)
    text = "\n".join(text_lines)
    # If a file path is provided, write the text to the file
    if path:
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
    return text


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataset
def parsed_config():
    """
    Returns a dict of parsed and mapped config files.
    """
    # #### XML config file
    config_xml = {
        "WaveForms": [
            "I\tStripData.WaveformData_0.#text",
            "II\tStripData.WaveformData_1.#text",
        ],
        "MetaData": [
            "unique identifier\tUID.DICOMStudyUID",
            "number of leads\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
            "resolution unit (waveforms)\tStripData.Resolution.@units",
            "resolution (waveforms)\tStripData.Resolution.#text",
            "resolution unit (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.@units",
            "resolution (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.#text",
            "sampling frequency (original)\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
            "sampling frequency unit\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
            "sampling number (waveforms)\tStripData.ChannelSampleCountTotal",
            "sampling number (medianbeats)\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
            "age\tPatientInfo.Age.#text",
            "gender\tPatientInfo.Gender",
            "birthday day\tPatientInfo.BirthDateTime.Day",
            "birthday month\tPatientInfo.BirthDateTime.Month",
            "birthday year\tPatientInfo.BirthDateTime.Year",
            "sysbp unit\tPatientVisit.SysBP.@units",
            "diabpb unit\tPatientVisit.DiaBP.@units",
            "sysbp\tPatientVisit.SysBP.@text",
            "diabpb\tPatientVisit.DiaBP.@text",
            "pacemaker\tPatientInfo.PaceMaker",
        ]
    }
    with NamedTemporaryFile("w") as tmp_file:
        _ = config_file(path=tmp_file.name, text=config_xml)
        parser_xml = config_utils.ConfigParser(tmp_file.name)()
    # adding the mapper
    parser_xml.map(mapper=config_utils.DataMap())
    
    # #### XML config file 2
    config_xml2 = {
        "WaveForms": [
            "I\tStripData.WaveformData_0.#text",
            "II\tStripData.WaveformData_1.#text",
        ],
        "MetaData": [
            "number of leads\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
            "resolution unit (waveforms)\tStripData.Resolution.@units",
            "resolution (waveforms)\tStripData.Resolution.#text",
            "resolution unit (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.@units",
            "resolution (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.#text",
            "sampling frequency (original)\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
            "sampling frequency unit\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
            "sampling number (waveforms)\tStripData.ChannelSampleCountTotal",
            "sampling number (medianbeats)\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
            "age\tPatientInfo.Age.#text",
            "gender\tPatientInfo.Gender",
            "birthday day\tPatientInfo.BirthDateTime.Day",
            "birthday month\tPatientInfo.BirthDateTime.Month",
            "birthday year\tPatientInfo.BirthDateTime.Year",
            "sysbp unit\tPatientVisit.SysBP.@units",
            "diabpb unit\tPatientVisit.DiaBP.@units",
            "sysbp\tPatientVisit.SysBP.@text",
            "diabpb\tPatientVisit.DiaBP.@text",
            "pacemaker\tPatientInfo.PaceMaker",
        ]
    }
    with NamedTemporaryFile("w") as tmp_file:
        _ = config_file(path=tmp_file.name, text=config_xml2)
        parser_xml2 = config_utils.ConfigParser(tmp_file.name)()
    # adding the mapper
    parser_xml2.map(mapper=config_utils.DataMap())

    # #### XML config file 3 (no leads declared, for testing empty extraction)
    config_xml3 = {
        "WaveForms": [],
        "MedianBeats": [],
        "MetaData": [
            "number of leads\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
            "resolution unit (waveforms)\tStripData.Resolution.@units",
            "resolution (waveforms)\tStripData.Resolution.#text",
            "resolution unit (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.@units",
            "resolution (medianbeats)\tRestingECGMeasurements.MedianSamples.Resolution.#text",
            "sampling frequency (original)\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
            "sampling frequency unit\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
            "sampling number (waveforms)\tStripData.ChannelSampleCountTotal",
            "sampling number (medianbeats)\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
        ]
    }
    with NamedTemporaryFile("w") as tmp_file:
        _ = config_file(path=tmp_file.name, text=config_xml3)
        parser_xml3 = config_utils.ConfigParser(tmp_file.name)()
    # adding the mapper
    parser_xml3.map(mapper=config_utils.DataMap())

    # #### DICOM config file
    leads = CLeads.values()
    config_dicom = {
        "WaveForms": [
            f"{lead}\tWaveformData.ECG_Leads_{idx}"
            for idx, lead in enumerate(leads)],
        "MedianBeats": [
            f"{lead}\tWaveformData.Median_Beats_{idx}"
            for idx, lead in enumerate(leads)],
        "MetaData": [
            "unique identifier\tSOP Instance UID",
            "number of leads\tWaveform Sequence_0.Number of Waveform Channels",
            "resolution unit (waveforms)\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
            "resolution (waveforms)\tWaveform Sequence_0.Channel Definition Sequence_0.Channel Sensitivity",
            "resolution unit (medianbeats)\tWaveform Sequence_1.Channel Definition Sequence_0.Channel Sensitivity Units Sequence_0.Code Value",
            "resolution (medianbeats)\tWaveform Sequence_1.Channel Definition Sequence_0.Channel Sensitivity",
            "sampling frequency (original)\tWaveform Sequence_0.Sampling Frequency",
            "sampling number (waveforms)\tWaveform Sequence_0.Number of Waveform Samples",
            "sampling number (medianbeats)\tWaveform Sequence_1.Number of Waveform Samples",
            "Softwave version\tSoftware Versions",
            "Manufacturer\tManufacturer",
            "Model name\tManufacturer's Model Name",
        ] +\
        [
            f"wave_channel_sens_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Sensitivity" for idx, _ in enumerate(leads)] +\
        [
            f"wave_channel_correctionfactor_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Sensitivity Correction Factor" for idx, _ in enumerate(leads)] +\
        [
            f"wave_channel_baseline_{idx}\tWaveform Sequence_0.Channel Definition Sequence_{idx}.Channel Baseline" for idx, _ in enumerate(leads)]
    }
    with NamedTemporaryFile("w") as tmp_file:
        _ = config_file(path=tmp_file.name, text=config_dicom)
        parser_dicom = config_utils.ConfigParser(tmp_file.name)()
    # adding the mapper
    parser_dicom.map(mapper=config_utils.DataMap())
    
    # return
    return {'parsed_dicom1': parser_dicom,
            'parsed_xml1' : parser_xml,
            'parsed_xml2' : parser_xml2,
            'parsed_xml3' : parser_xml3,
            }

