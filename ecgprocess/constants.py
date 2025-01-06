'''
Constants used by ECGProcess
'''

from dataclasses import dataclass

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class CoreData:
    '''
    Core variable names which are used internally by various modules in
    `ECGProcess`.
    '''
    # /////////////////////////////////////////////////////////////////////////
    class DataTypes:
        '''
        Contains constants representing high-level data categories used
        in ECG processing, such as waveforms, median beats, and metadata.
        '''
        WaveForms   = 'WaveForms'
        MedianBeats = 'MedianBeats'
        MetaData    = 'MetaData'
        OtherData   = 'OtherData'
    # /////////////////////////////////////////////////////////////////////////
    class Leads:
        '''
        The interally used lead names.
        '''
        I   = 'I'
        II  = 'II'
        III = 'III'
        aVR = 'aVR'
        aVL = 'aVL'
        aVF = 'aVF'
        V1  = 'V1'
        V2  = 'V2'
        V3  = 'V3'
        V4  = 'V4'
        V5  = 'V5'
        V6  = 'V6'
    # /////////////////////////////////////////////////////////////////////////
    class MetaData:
        '''
        Contains constants representing metadata fields required for
        ECG processing.
        '''
        UID     = 'unique identifier'
        NLEADS  = 'number of leads'
        RES_U_W = 'resolution unit (waveforms)'
        RES_U_M = 'resolution unit (medianbeats)'
        RES_W   = 'resolution (waveforms)'
        RES_M   = 'resolution (medianbeats)'
        SF      = 'sampling frequency (original)'
        SF_U    = 'sampling frequency unit'
        SN_W    = 'sampling number (waveforms)'
        SN_M    = 'sampling number (medianbeats)'
    # /////////////////////////////////////////////////////////////////////////
    class ProcessingData:
        '''
        Contains constants for attributes and variables created by the process
        modules.
        '''
        TAGS      = 'tags'
        RAW       = 'raw_data'
        Duration  = 'duration (sec)'
        SF_NEW    = 'sampling frequency (processed)'
        RESAMPLE  = 'resample_500'
        AUG_LEADS = 'augment_leads'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class UtilsReaderNames(object):
    '''
    Names used in the Utils Reader Tools module.
    '''
    DICOM_WAVE_ARRAY     = 'waveform_array'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class UtilsGeneralNames(object):
    '''
    Names used in the Utils General module.
    '''
    LXML_ERROR         = 'expected'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class UtilsConfigData(object):
    '''
    Names used in the Utils Cofig Data module
    '''
    MetaData    = CoreData.DataTypes.MetaData
    OtherData   = CoreData.DataTypes.OtherData
    WaveForms   = CoreData.DataTypes.WaveForms
    MedianBeats = CoreData.DataTypes.MedianBeats
    path        = 'path'
    data        = '_data'
    MAPPER      = 'mapper'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class ProcessXMLNames(object):
    '''
    Names used in the process_xml module.
    '''
    RESAMPLE  = CoreData.ProcessingData.RESAMPLE
    AUG_LEADS = CoreData.ProcessingData.AUG_LEADS

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class ProcessDicomNames(object):
    RESAMPLE  = CoreData.ProcessingData.RESAMPLE
    AUG_LEADS = CoreData.ProcessingData.AUG_LEADS
    
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class FixedReaderNames(object):
    ORIG_DCMREAD_INST     = 'DMCReadInstance'
    WAVE_FORM_SEQ         = 'WaveformSequence'
    CHANNEL_DEF_SEQ       = 'ChannelDefinitionSequence'
    CHANNEL_NUMBER        = 'ChannelNumber'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class TabularNames(object):
    E_META         = 'extract_'+CoreData.DataTypes.MetaData
    E_WAVE         = 'extract_'+CoreData.DataTypes.WaveForms
    E_MEDIAN       = 'extract_'+CoreData.DataTypes.MedianBeats
    SKIP_PERM      = 'ignore_permission'
    SKIP_DATA      = 'ignore_data'
    SKIP_INVALID   = 'ignore_invalid'
    SCHEMA         = 'schema'
    RPATH_L        = 'raw_path_list'
    FPATH_L        = 'failed_path_list'
    CPATH_L        = 'curated_path_list'
    KEY_L          = 'key_list'
    NO_DATA_L      = 'no_data_list'
    INVALID_L      = 'invalid_list'
    TABLE_CALLED   = 'table_called'
    WRITE_TAB      = 'table'
    WRITE_NUMPY    = 'numpy'
    WRITE_TFLOW    = 'tensorflow'
    WRITE_ECG_PATH = 'target_path'
    WRITE_TYPE     = 'file_type'
    ID_START       = '_id_start_number'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@dataclass
class DICOMTags(object):
    '''
    The DICOM tags ECGDICOMReader will look for.
    
    This simply is a collection of dictionary with the keys representing the
    `target` (new) name and the values the `source` (old) names.
    
    Attributes
    ----------
    METADATA
        A dictionary describing the metadata one wants to extract from a
        DICOM.
    WAVE_FORMS
        A dictionary describing the waveform data one wants to extract.
    ECG_INTERPERTATION_DICT
    A dictionary describing the ECG traits one wants to extract from the
        `WaveformAnnotationSequence` pydicom attribute. The keys will be used
        as the target attribute against which values are assigned. The values
        are expected to be lists and can contain multiple strings (synonyms)
        against which case-insensitive matching is performed.
        
    '''
    # /////////////////////////////////////////////////////////////////////////
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    METADATA = {
        CoreData.MetaData.UID : 'SOPInstanceUID',
        'SERIESinstanceUID'       : 'SeriesInstanceUID',
        'STUDYinstanceUID'        : 'StudyInstanceUID',
        'PatientID'               : 'PatientID',
        'StudyDate'               : 'StudyDate',
        'StudyTime'               : 'StudyTime',
        'AccessionNumber'         : 'AccessionNumber',
        'PatientBirthDate'        : 'PatientBirthDate',
        'PatientName'             : 'PatientName',
        'PatientSex'              : 'PatientSex',
        'StudyDescription'        : 'StudyDescription',
        'AcquisitionDateTime'     : 'AcquisitionDateTime',
        'AcquisitionTimeZone'     : 'TimezoneOffsetFromUTC',
        'Manufacturer'            : 'Manufacturer',
        'ManufacturerModelName'   : 'ManufacturerModelName',
        'SoftwareVersions'        : 'SoftwareVersions',
        'DataExportedBy'          : 'IssuerOfPatientID',
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    WAVE_FORMS = {
        'TimeOffset'                : 'MultiplexGroupTimeOffset',
        FixedReaderNames.CHANNEL_NUMBER : 'NumberOfWaveformChannels',
        CoreData.MetaData.SN_W      : 'NumberOfWaveformSamples',
        CoreData.MetaData.SF        : 'SamplingFrequency',
        'ChannelSensitivity'        : 'ChannelSensitivity',
        'ChannelBaseline'           : 'ChannelBaseline',
        'ChannelSampleSkew'         : 'ChannelSampleSkew',
        'FilterLowFrequency'        : 'FilterLowFrequency',
        'FilterHighFrequency'       : 'FilterHighFrequency',
        'NotchFilterFrequency'      : 'NotchFilterFrequency',
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ECG_INTERPERTATION_DICT ={
        'QT Interval' : ['QT Interval'],
        'QTc Interval': ['QTc Interval'],
        'QTc Bazett' : ['QTc Bazett'],
        'QRS Duration': ['QRS Duration'],
        'QRS Axis': ['QRS Axis'],
        'RR Interval': ['RR Interval'],
        'VRate': ['VRate', 'Ventricular Heart Rate'],
        'ARate': ['Atrial Heart Rate'],
        'T Axis': ['T Axis'],
        'P Axis': ['P Axis'],
        'R Axis': ['R Axis'],
        'P Onset': ['P Onset'],
        'P Offset': ['P Offset'],
        'T Offset': ['T Offset'],
        'PR Interval': ['PR Interval'],
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MEDIAN_BEATS = {
        'TimeOffset'                      : 'MultiplexGroupTimeOffset',
        FixedReaderNames.CHANNEL_NUMBER  : 'NumberOfWaveformChannels',
        CoreData.MetaData.SN_M : 'NumberOfWaveformSamples',
        'ChannelSensitivity'              : 'ChannelSensitivity',
        'ChannelBaseline'                 : 'ChannelBaseline',
        'ChannelSampleSkew'               : 'ChannelSampleSkew',
        'FilterLowFrequency'              : 'FilterLowFrequency',
        'FilterHighFrequency'             : 'FilterHighFrequency',
        'NotchFilterFrequency'            : 'NotchFilterFrequency',
    }
    MEDIAN_BEATS = {
        (k if ' (medianbeats)' in k else f'{k} (medianbeats)'): v
        for k, v in MEDIAN_BEATS.items()
    }


