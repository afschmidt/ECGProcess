import pytest
import ecgprocess.utils.config_tools as config
from ecgprocess.constants import (
    CoreData as Core,
    UtilsConfigData as ConfigNames,
)
from ecgprocess.errors import InputValidationError
from ecgprocess.example_data.examples import config_file
from tempfile import NamedTemporaryFile

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# constants
CMeta = Core.MetaData

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# fixtures

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestBaseExtraction(object):
    """
    Testing classses related to Extraction.
    """ # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_data(self):
        required = config.RequiredData()
        default = required.to_dict()
        # Update values for some keys
        updates = {
            CMeta.UID: "UniqueID123",
            CMeta.SF: "SamplingFrequency123",
        }
        required.update_values(**updates)
        # Verify the updated values
        for key, value in updates.items():
            assert required.to_dict()[key] == value
        # Verify other keys are still None
        for key in required.keys():
            if key not in updates:
                assert required.to_dict()[key] is default[key]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_data_multiple_intances(self):
        """Making sure multiple instances have unique content"""
        required1 = config.RequiredData()
        required2 = config.RequiredData()
        # Update values for some keys
        updates = {
            CMeta.UID: "UniqueID123",
            CMeta.SF: "SamplingFrequency123",
        }
        required1.update_values(**updates)
        # ensuring both dicts are distinct
        assert required1.to_dict().values() != required2.to_dict().values()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_data_invalid_keys(self):
        required = config.RequiredData()
        # Try updating an invalid key
        with pytest.raises(KeyError):
            required.update_values(InvalidKey="InvalidValue")
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_other_data(self):
        other_dict = {
            'key1': 'value1',
            'key2': 'value2',
        }
        other = config.OtherData()
        other.update_values(**other_dict)
        # verify the keys
        assert other.keys() == list(other_dict.keys())
        assert other.to_dict() == other_dict
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_datamap_default(self):
        mapper = config.DataMap()
        mapper.items()
        attr = [ConfigNames.WaveForms, ConfigNames.MedianBeats,
                ConfigNames.MetaData, ConfigNames.OtherData]
        assert mapper.get_attributes() == attr[:-1]
        assert mapper.get_attributes(all_=True) == attr
        assert len(mapper.keys(ConfigNames.MetaData)) > 0
        assert len(mapper.items(ConfigNames.MetaData)) > 0
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_datamap_supplied_data(self):
        ot_d = {'b': 'a'}
        mapper = config.DataMap(WaveForms={'test1':1}, MedianBeats={'test2':2},
                                MetaData={'a': 'b'}, OtherData=ot_d)
        attr = [ConfigNames.WaveForms, ConfigNames.MedianBeats,
                ConfigNames.MetaData, ConfigNames.OtherData]
        assert mapper.get_attributes() == attr
        assert mapper.get_attributes(all_=True) == attr
        assert mapper.keys(ConfigNames.OtherData) == ['b']
        assert mapper.items(ConfigNames.OtherData) == {'OtherData': ot_d}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_datamap_errors(self):
        with pytest.raises(InputValidationError):
            config.DataMap(1)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_config_parers(self):
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name)
            parser = config.ConfigParser(tmp_file.name)()
        assert len(parser._data) > 0
        assert len(parser.get_section('WaveForms')) == 2
        # add mapper
        mapped = parser.map(mapper=config.DataMap())
        meta = getattr(mapped, ConfigNames.MetaData)
        assert sum(1 for value in meta.values() if value is not None) == 3
        assert getattr(mapped, ConfigNames.WaveForms) !=\
            getattr(mapped, ConfigNames.MedianBeats)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_config_parers(self):
        wrong_config = {
            "WaveForms": [
                "I\tLead_I_name",
                "WRONG\tLead_II_name",
            ],
            "MetaData": [
                "sampling frequency (original)\tSamplingFrequency",
                "sampling number (waveforms)\tNumberOfWaveformSamples",
                "Birthdate\tPatientBirthDate",
            ]
        }
        with NamedTemporaryFile("w") as tmp_file:
            _ = config_file(path=tmp_file.name, text=wrong_config)
            parser = config.ConfigParser(tmp_file.name)()
        assert len(parser._data) > 0
        assert len(parser.get_section('WaveForms')) == 2
        # add mapper
        with pytest.raises(KeyError):
            _ = parser.map(mapper=config.DataMap())



