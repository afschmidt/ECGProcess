Privileged and Reserved Names
==============================

Overview
--------

ECGProcess reserves certain names for internal use in config files, data
extraction, and processing. These names cannot be used as custom metadata
field names.

The authoritative list is in ``ecgprocess.PrivilegedNames``, derived from
``ecgprocess.constants.CoreData`` and stays in sync automatically.

Programmatic Access
--------------------

Import the registry and check if a name is reserved:

.. code-block:: python
   
    from ecgprocess import PrivilegedNames
    
    # Check if a name is reserved
    if not PrivilegedNames.is_reserved('V7'):
        print("V7 is not one of the standard 12 leads")
    
    if PrivilegedNames.is_reserved('I'):
        print("I is reserved (standard lead)")
    
    # View all reserved names
    print(PrivilegedNames.LEADS)      
    print(PrivilegedNames.METADATA)  

Standard Lead Names (12)
------------------------

Standard 12-lead ECG names. These cannot be overridden:

**Limb leads (6):** I, II, III, aVR, aVL, aVF

**Precordial leads (6):** V1, V2, V3, V4, V5, V6

Privileged Metadata Field Names (10)
-------------------------------------

the following Metadata fields are used in config files and data extraction.
These cannot be overridden as custom field names:

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

To use custom lead names beyond the standard 12, set ``extra_leads=True``
on ``DataMap`` before parsing the config file.
Any ``[WaveForms]`` or ``[MedianBeats]`` key in the config file that is 
not one of the standard 12 is then accepted automatically:

.. code-block:: python

    from ecgprocess.utils.config_tools import ConfigParser, DataMap
    
    mapper = DataMap(extra_leads=True)
    parser = ConfigParser(path='config.cnf')()
    parser.map(mapper=mapper)

