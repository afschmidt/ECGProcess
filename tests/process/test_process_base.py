import pytest
import numpy as np
import ecgprocess.process.process_base as pro_base
import ecgprocess.utils.config_tools as config_utils
from ecgprocess.constants import CoreData as Core
from ecgprocess.errors import MissingTagError, InputValidationError
from ecgprocess.example_data.examples import (
    config_file,
)

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# core names
CProc = Core.ProcessingData
CMeta = Core.MetaData
CTypes = Core.DataTypes
CLeads = Core.Leads

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# example: a flat tag dictionary, 2 s waveforms and 1 s median beats at 250 Hz
example_raw = {
    'rate': '250',
    'n_wave': 500,
    'n_median': 250,
    'patient': 'P001',
    **{f'wave_{l}': list(np.sin(np.linspace(0, 4 * np.pi, 500)) + i)
       for i, l in enumerate(CLeads.values())},
    **{f'median_{l}': list(np.sin(np.linspace(0, 2 * np.pi, 250)) + i)
       for i, l in enumerate(CLeads.values())},
}
example_meta = [
    "sampling frequency (original)\trate",
    "sampling number (waveforms)\tn_wave",
    "sampling number (medianbeats)\tn_median",
    "unique identifier\tpatient",
]
# resampling needs every lead declared: a lead without data is not resampled
config_all_leads = {
    "WaveForms": [f"{l}\twave_{l}" for l in CLeads.values()],
    "MedianBeats": [f"{l}\tmedian_{l}" for l in CLeads.values()],
    "MetaData": example_meta,
    "OtherData": ["absent\tnot_in_file"],
}
# only leads I and II, so the limb leads can be derived
config_two_leads = {
    "WaveForms": [f"{l}\twave_{l}" for l in (CLeads.I, CLeads.II)],
    "MedianBeats": [f"{l}\tmedian_{l}" for l in (CLeads.I, CLeads.II)],
    "MetaData": example_meta,
}

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# fixtures
class _StubReader(pro_base.BaseReader):
    """A minimal reader holding a hand-built flat tag dictionary."""
    def __init__(self, raw, **kwargs):
        """Store the raw tags and any reader options."""
        super().__init__(raw=raw)
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.fixture
def parse_config(tmp_path):
    """Return a function which writes, parses, and maps a config."""
    def _parse(text):
        path = str(tmp_path / 'config.txt')
        _ = config_file(path=path, text=text)
        parser = config_utils.ConfigParser(path)()
        parser.map(mapper=config_utils.DataMap())
        return parser
    return _parse

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestBaseReader(object):
    """Test ecgprocess.process.process_base.BaseReader"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract(self, parse_config):
        # #### class defaults: resample to 500 Hz, no lead augmentation
        reader = _StubReader(dict(example_raw))
        out = reader.extract(config=parse_config(config_all_leads))
        assert out is reader
        meta = getattr(out, CTypes.MetaData)
        wave = getattr(out, CTypes.WaveForms)
        median = getattr(out, CTypes.MedianBeats)
        # numeric strings are parsed and missing tags become None
        assert meta[CMeta.SF] == 250
        assert meta[CMeta.UID] == 'P001'
        assert getattr(out, CTypes.OtherData)['absent'] is None
        # durations derive from sampling number over frequency
        assert meta[CProc.Duration_W] == 2.0
        assert meta[CProc.Duration_M] == 1.0
        assert meta[CProc.SF_NEW_W] == 500
        assert meta[CProc.SF_NEW_M] == 500
        assert isinstance(wave[CLeads.I], np.ndarray)
        assert len(wave[CLeads.V6]) == 1000
        assert len(median[CLeads.II]) == 500
        # #### instance options override the class defaults
        reader = _StubReader(dict(example_raw), augment_leads=True,
                             resample_500=False)
        reader.extract(config=parse_config(config_two_leads))
        meta = getattr(reader, CTypes.MetaData)
        wave = getattr(reader, CTypes.WaveForms)
        median = getattr(reader, CTypes.MedianBeats)
        assert meta[CProc.SF_NEW_W] is None
        assert len(wave[CLeads.I]) == 500
        # the limb leads are derived from leads I and II
        for lead in (CLeads.III, CLeads.aVR, CLeads.aVL, CLeads.aVF):
            assert wave[lead] is not None
            assert median[lead] is not None
        np.testing.assert_allclose(
            wave[CLeads.III], wave[CLeads.II] - wave[CLeads.I])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('bits', [np.int16, np.float32])
    def test_extract_bits(self, parse_config, bits):
        # resampling and lead augmentation both run, and every signal must
        # still come back in the requested storage type
        config = parse_config(config_two_leads)
        reader = _StubReader(dict(example_raw), augment_leads=True)
        reader.extract(config=config, bits=bits)
        wave = getattr(reader, CTypes.WaveForms)
        median = getattr(reader, CTypes.MedianBeats)
        for signals in (wave, median):
            for lead in (CLeads.I, CLeads.II, CLeads.III, CLeads.aVR,
                         CLeads.aVL, CLeads.aVF):
                assert signals[lead].dtype == bits
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract_errors(self, parse_config):
        config = parse_config(config_all_leads)
        # resampling needs the original sampling frequency
        raw = dict(example_raw)
        del raw['rate']
        with pytest.raises(KeyError):
            _StubReader(raw).extract(config=config)
        # a missing tag raises when empty tags may not be skipped
        with pytest.raises(MissingTagError):
            _StubReader(dict(example_raw)).extract(
                config=config, skip_empty=False)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestResampleHelpers(object):
    """
    Testing the per-source resampling helpers: the derived durations and
    the independent gate which lets one source resample when the other
    cannot.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_signal_duration(self):
        assert pro_base._signal_duration(600, 500) == 1.2
        assert pro_base._signal_duration(5000, 500) == 10.0
        # an absent sampling number or frequency is not an error: the
        # duration is simply unknown
        assert pro_base._signal_duration(None, 500) is None
        assert pro_base._signal_duration(600, None) is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resample_source_gates_on_own_duration(self):
        # 1.2 s at 250 Hz resamples to the 500 Hz target
        signals = {'I': np.sin(np.linspace(0, 2 * np.pi, 300))}
        out, sf_new = pro_base._resample_source(
            signals, 1.2, 'median beat', skip_empty=True)
        assert len(out['I']) == 600
        assert sf_new == 500
        # without its own duration the source is left untouched and
        # reports no processed rate, rather than blocking the other
        # source or being silently rescaled
        out, sf_new = pro_base._resample_source(
            signals, None, 'median beat', skip_empty=True)
        assert len(out['I']) == 300
        assert sf_new is None
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_resample_source_without_data(self):
        # an absent source is not resampled; skip_empty governs whether
        # that is an error
        signals = {'I': None}
        out, sf_new = pro_base._resample_source(
            signals, 1.2, 'median beat', skip_empty=True)
        assert out == signals
        assert sf_new == 500
        with pytest.raises(AttributeError):
            pro_base._resample_source(
                signals, 1.2, 'median beat', skip_empty=False)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_cast_signals(self):
        signals = {'I': np.array([12.7, -0.6, 2.4]), 'II': None}
        # integer types round to the nearest whole number; None is kept
        res = pro_base._cast_signals(signals, np.int16)
        assert res['I'].dtype == np.int16
        assert res['I'].tolist() == [13, -1, 2]
        assert res['II'] is None
        # float types keep the decimals
        res = pro_base._cast_signals(signals, np.float32)
        assert res['I'].dtype == np.float32
        assert [round(float(v), 1) for v in res['I']] == [12.7, -0.6, 2.4]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestExtractPattern(object):
    """Test ecgprocess.process.process_base.extract_pattern"""
    # three measurement groups, each named by its Code Meaning tag, plus a
    # tag outside every group
    data = {
        'Measurement_1.Code Meaning': 'QRS Duration',
        'Measurement_1.Numeric Value': '96',
        'Measurement_1.Units': 'ms',
        'Measurement_2.Code Meaning': 'QT Interval',
        'Measurement_2.Numeric Value': 402.5,
        'Measurement_3.Code Meaning': 'Axis',
        'Measurement_3.Values': '10,20',
        'Unrelated': 'ignored',
    }
    pattern = {
        'Measurement_1.': 'Code Meaning',
        'Measurement_2.': 'Code Meaning',
        'Measurement_3.': 'Code Meaning',
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract_pattern(self):
        res = pro_base.extract_pattern(self.data, self.pattern)
        # keys are renamed, numbers parsed, text kept, and a multi-value
        # string stays a list
        assert res == {
            'QRS Duration (Numeric Value)': 96,
            'QRS Duration (Units)': 'ms',
            'QT Interval (Numeric Value)': 402.5,
            'Axis (Values)': [10, 20],
        }
        assert isinstance(res['QRS Duration (Numeric Value)'], int)
        assert isinstance(res['QT Interval (Numeric Value)'], float)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_extract_pattern_no_parse(self):
        res = pro_base.extract_pattern(
            self.data, self.pattern, parse_numeric=False)
        # every value is cast to a string, including the raw float
        assert res == {
            'QRS Duration (Numeric Value)': '96',
            'QRS Duration (Units)': 'ms',
            'QT Interval (Numeric Value)': '402.5',
            'Axis (Values)': '10,20',
        }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @pytest.mark.parametrize('kwargs', [
        {'data': ['not', 'a', 'dict']},
        {'pattern': 'Measurement_1.'},
        {'substitute': [r'_[0-9]', ' ']},
        {'character_trim': '0'},
        {'skip_empty': 1},
        {'parse_numeric': 'yes'},
        {'verbose': None},
    ])
    def test_extract_pattern_errors(self, kwargs):
        args = {'data': self.data, 'pattern': self.pattern, **kwargs}
        with pytest.raises(InputValidationError):
            pro_base.extract_pattern(**args)
