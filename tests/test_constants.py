from ecgprocess.constants import CoreData, PrivilegedNames

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class TestPrivilegedNames(object):
    """Tests for PrivilegedNames.__str__ and __repr__."""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_str_reports_actual_registry_size(self):
        """
        The counts printed in __str__ must match the live registry
        size, not a hardcoded number.
        """
        text = str(PrivilegedNames())
        n_leads = len(CoreData.Leads.values())
        n_metadata = len(CoreData.MetaData.values())
        assert f'Standard ECG Leads ({n_leads}):' in text
        assert f'Privileged Metadata Fields ({n_metadata}):' in text
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_repr_reports_actual_registry_size(self):
        """The counts in __repr__ must match the live registry size."""
        text = repr(PrivilegedNames())
        n_leads = len(CoreData.Leads.values())
        n_metadata = len(CoreData.MetaData.values())
        n_total = len(PrivilegedNames.ALL)
        assert f'leads={n_leads}' in text
        assert f'metadata={n_metadata}' in text
        assert f'total={n_total}' in text
