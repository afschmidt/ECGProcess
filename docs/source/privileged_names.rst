Privileged and Reserved Names
==============================

Overview
--------

ECGProcess reserves certain names for internal use in config files, data
extraction, and processing. These names cannot be used in ``extra_leads``
declarations or as custom metadata field names.

The authoritative list is in ``ecgprocess.PrivilegedNames``, derived from
``ecgprocess.constants.CoreData`` and stays in sync automatically.

Programmatic Access
--------------------

Import the registry and check if a name is reserved:

.. code-block:: python
   
    from ecgprocess import PrivilegedNames
    
    # Check if a name is reserved
    if not PrivilegedNames.is_reserved('V7'):
        print("V7 is not reserved; can use in extra_leads")
    
    if PrivilegedNames.is_reserved('I'):
        print("I is reserved (standard lead)")
    
    # View all reserved names
    print(PrivilegedNames.LEADS)       # 12 standard leads
    print(PrivilegedNames.METADATA)    # 10 privileged metadata fields

Standard Lead Names (12)
------------------------

Standard 12-lead ECG names. These cannot be overridden:

**Limb leads (6):** I, II, III, aVR, aVL, aVF

**Precordial leads (6):** V1, V2, V3, V4, V5, V6

Privileged Metadata Field Names (10)
-------------------------------------

Metadata fields used in config files and data extraction. These cannot
be overridden as custom field names:

- unique identifier
- number of leads
- resolution unit (waveforms)
- resolution unit (medianbeats)
- resolution (waveforms)
- resolution (medianbeats)
- sampling frequency (original)
- sampling frequency unit
- sampling number (waveforms)
- sampling number (medianbeats)

Using Custom Lead Names
-----------------------

To use custom lead names beyond the standard 12, declare them via
``DataMap`` before parsing the config file:

.. code-block:: python

    from ecgprocess.utils.config_tools import ConfigParser, DataMap
    
    # Custom lead names must not collide with reserved names
    mapper = DataMap(extra_leads=('V7', 'V8', 'V3R'))
    parser = ConfigParser(path='config.cnf')()
    parser.map(mapper=mapper)

Custom metadata field names can be placed in the ``[OtherData]`` section
of the config file and do not require declarations.
