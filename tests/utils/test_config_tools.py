import pytest
import ecgprocess.utils.config_tools as config
from ecgprocess.constants import (
    CoreData as CDNames,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestBaseExtraction(object):
    """
    Testing classses related to Extraction.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_required_data(self):
        required = config.RequiredData()
        default = required.to_dict()
        # Update values for some keys
        updates = {
            CDNames.MD_UID: "UniqueID123",
            CDNames.MD_SF: "SamplingFrequency123",
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
            CDNames.MD_UID: "UniqueID123",
            CDNames.MD_SF: "SamplingFrequency123",
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
        other = config.OtherData(data=other_dict)
        # verify the keys
        assert other.keys() == list(other_dict.keys())
        assert other.to_dict() == other_dict
        # confirm error
        with pytest.raises(NotImplementedError):
            other.update_values()
