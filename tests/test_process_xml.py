import pytest
import numpy as np
import ecgprocess.process_xml as pro_xml
import ecgprocess.utils.config_tools as config_utils
from tempfile import NamedTemporaryFile
from ecgprocess.constants import CoreData as Core
from ecgprocess.errors import InputValidationError, MissingTagError
from ecgprocess.example_data.examples import (
    config_file,
    list_xml_paths,
)

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# core names
CProc = Core.ProcessingData

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# example
example_config = {
    "WaveForms": [
        "I\tStripData.WaveformData_0.#text",
    ],
    "MedianBeats": [
        "aVF\tRestingECGMeasurements.MedianSamples.WaveformData_5.#text",
        "V1\tRestingECGMeasurements.MedianSamples.WaveformData_6.#text",
        "V2\tRestingECGMeasurements.MedianSamples.WaveformData_60.#text",
    ],
    "MetaData": [
        "unique identifier\t\t\tUID.DICOMStudyUID",
        "number of leads\t\t\t\tRestingECGMeasurements.MedianSamples.NumberOfLeads",
        "resolution unit (waveforms)\t\tStripData.Resolution.@units",
        "resolution (waveforms)\t\t\tStripData.Resolution.#text",
        "resolution unit (medianbeats)\t\tRestingECGMeasurements.MedianSamples.Resolution.@units",
        "resolution (medianbeats)\t\tRestingECGMeasurements.MedianSamples.Resolution.#text",
        "sampling frequency (original)\t\tRestingECGMeasurements.MedianSamples.SampleRate.#text",
        "sampling frequency unit\t\t\tRestingECGMeasurements.MedianSamples.SampleRate.@units",
        "sampling number (waveforms)\t\tStripData.ChannelSampleCountTotal",
        "sampling number (medianbeats)\t\tRestingECGMeasurements.MedianSamples.ChannelSampleCountTotal",
        "observation hour\t\t\tObservationDateTime.Hour",
        "observation minute\t\t\tObservationDateTime.Minute",
        "observation second\t\t\tObservationDateTime.Second",
        "observation day\t\t\t\tObservationDateTime.Day",
        "observation month\t\t\tObservationDateTime.Month",
        "observation year\t\t\tObservationDateTime.Year",
    ]
}


# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EXGXMLReader
class TestECGXMLReader(object):
    """Test ecgprocess.process_xml.ECGXMLReader"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecgxmlreader_init(self):
        reader = pro_xml.ECGXMLReader(augment_leads=True, resample_500=False)
        assert reader.augment_leads is True
        assert reader.resample_500 is False
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecgxmlreader_error(self):
        reader = pro_xml.ECGXMLReader()
        # Invalid path type
        with pytest.raises(InputValidationError):
            reader(123, schema=None, verbose=False)
        # Invalid schema type
        with pytest.raises(InputValidationError):
            reader("valid_path.xml", schema=123, verbose=False)
        # Invalid verbose type
        with pytest.raises(InputValidationError):
            reader("valid_path.xml", schema=None, verbose="True")
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecgxmlreader_call(self):
        # get example XML and XSD
        path = list_xml_paths()['example_1']
        schema = list_xml_paths()['example_1_schema']
        # run reader
        reader = pro_xml.ECGXMLReader()
        parsed_xml1 = reader(path, schema, verbose=False)
        # without schema
        parsed_xml2 = reader(path,  verbose=False)
        # NOTE verbose is directly piped to reader_tools.validate_xml so should
        # be tested there.
        assert len(parsed_xml1.raw_data) > 0
        assert len(
            parsed_xml2.raw_data['RestingECGMeasurements.MedianSamples.WaveformData_3.#text']
        ) > 0
        with pytest.raises(AttributeError):
            parsed_xml2.raw_data = 0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ecgxmlreader_extract(self):
        n_leads = 'number of leads'
        # adding the mapper.
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=example_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)() # examples
        parsed_confg.map(mapper=config_utils.DataMap())
        # adding the file and schema path.
        path = list_xml_paths()['example_1']
        schema = list_xml_paths()['example_1_schema']
        # #### run
        reader = pro_xml.ECGXMLReader()
        parsed_xml = reader(path=path, schema=schema, verbose=True)
        # extraction 1
        with pytest.warns(UserWarning):
            extract = parsed_xml.extract(config=parsed_confg, skip_empty=True)
        assert extract.MetaData[n_leads] == 12
        assert extract.WaveForms['I'].ndim == 1
        # extraction 2
        with pytest.raises(MissingTagError):
            parsed_xml.extract(config=parsed_confg, skip_empty=False)
        # extraction 3
        parsed_xml = reader(path=path, schema=schema, verbose=False)
        extract = parsed_xml.extract(config=parsed_confg, parse_numeric=False)
        assert extract.MetaData[n_leads] == '12'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_leads_raises_when_src_missing(self):
        """KeyError raised when derived leads absent and source leads missing.
        
        Augmentation is both needed (III, aVR, aVL, aVF absent from
        wave_data) and impossible (I or II also absent). get_limb_leads()
        raises KeyError in this case.
        
        Test data: ``example_config`` — WaveForms contains only lead I
        (``StripData.WaveformData_0``). Lead II is not mapped so its value
        is None in wave_data, satisfying both aug_missing=True and
        src_available=False conditions that trigger the KeyError.
        """
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=example_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)()
        parsed_confg.map(mapper=config_utils.DataMap())
        path = list_xml_paths()['example_1']
        schema = list_xml_paths()['example_1_schema']
        reader = pro_xml.ECGXMLReader(augment_leads=True, resample_500=False)
        parsed_xml = reader(path=path, schema=schema, verbose=False)
        with pytest.raises(KeyError):
            parsed_xml.extract(config=parsed_confg, skip_empty=True)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_augment_leads_derives_missing_leads(self):
        """Derived leads are computed when src leads present but aug leads absent.
        
        With augment_leads=True, when I and II are mapped and return data but
        III, aVR, aVL, aVF are not in the config, get_limb_leads() is called
        and the four derived leads must be present in the result.
        
        Test data: WaveForms and MedianBeats each map only I
        (``WaveformData_0`` / ``MedianSamples.WaveformData_0``) and II
        (``WaveformData_1`` / ``MedianSamples.WaveformData_1``). III, aVR,
        aVL, aVF are absent from both sections so aug_missing=True with
        source leads available, triggering augmentation for both datasets.
        """
        aug_config = {
            "WaveForms": [
                "I\tStripData.WaveformData_0.#text",
                "II\tStripData.WaveformData_1.#text",
            ],
            "MedianBeats": [
                "I\tRestingECGMeasurements.MedianSamples.WaveformData_0.#text",
                "II\tRestingECGMeasurements.MedianSamples.WaveformData_1.#text",
            ],
            "MetaData": example_config["MetaData"],
        }
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=aug_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)()
        parsed_confg.map(mapper=config_utils.DataMap())
        path = list_xml_paths()['example_1']
        schema = list_xml_paths()['example_1_schema']
        reader = pro_xml.ECGXMLReader(augment_leads=True, resample_500=False)
        parsed_xml = reader(path=path, schema=schema, verbose=False)
        extract = parsed_xml.extract(config=parsed_confg, skip_empty=True)
        for lead in ('III', 'aVR', 'aVL', 'aVF'):
            assert lead in extract.WaveForms, f"derived lead {lead!r} missing"
            assert extract.WaveForms[lead] is not None


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestResampleMetadata(object):
    """
    Testing the per-source resampling bookkeeping: the derived
    durations, the per-source processed sampling frequencies, and the
    independent gate which lets one source resample when the other
    cannot.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_per_source_durations_and_rates(self):
        # the example is stored at 500 Hz: no resampling is needed, but
        # both sources are known to be at the target
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=example_config)
            parsed_confg = config_utils.ConfigParser(tmp_file.name)()
        parsed_confg.map(mapper=config_utils.DataMap())
        reader = pro_xml.ECGXMLReader(resample_500=True)
        parsed_xml = reader(path=list_xml_paths()['example_1'],
                            verbose=False)
        extract = parsed_xml.extract(config=parsed_confg, skip_empty=True)
        meta = extract.MetaData
        # 5000 samples / 500 Hz and 600 samples / 500 Hz
        assert meta[CProc.Duration_W] == 10.0
        assert meta[CProc.Duration_M] == 1.2
        assert meta[CProc.SF_NEW_W] == 500
        assert meta[CProc.SF_NEW_M] == 500
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_signal_duration(self):
        assert pro_xml._signal_duration(600, 500) == 1.2
        assert pro_xml._signal_duration(5000, 500) == 10.0
        # an absent sampling number or frequency is not an error: the
        # duration is simply unknown
        assert pro_xml._signal_duration(None, 500) is None
        assert pro_xml._signal_duration(600, None) is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resample_source_gates_on_own_duration(self):
        # 1.2 s at 250 Hz resamples to the 500 Hz target
        signals = {'I': np.sin(np.linspace(0, 2 * np.pi, 300))}
        out, sf_new = pro_xml._resample_source(
            signals, 1.2, 'median beat', skip_empty=True)
        assert len(out['I']) == 600
        assert sf_new == 500
        # without its own duration the source is left untouched and
        # reports no processed rate, rather than blocking the other
        # source or being silently rescaled
        out, sf_new = pro_xml._resample_source(
            signals, None, 'median beat', skip_empty=True)
        assert len(out['I']) == 300
        assert sf_new is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resample_source_without_data(self):
        # an absent source is not resampled; skip_empty governs whether
        # that is an error
        signals = {'I': None}
        out, sf_new = pro_xml._resample_source(
            signals, 1.2, 'median beat', skip_empty=True)
        assert out == signals
        assert sf_new == 500
        with pytest.raises(AttributeError):
            pro_xml._resample_source(
                signals, 1.2, 'median beat', skip_empty=False)
