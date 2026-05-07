'''
Constants used by ECGProcess
'''

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
        The internally used lead names.
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
    Names used in the Utils Config Data module
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
    """Names used in the process_dicom module."""
    RESAMPLE  = CoreData.ProcessingData.RESAMPLE
    AUG_LEADS = CoreData.ProcessingData.AUG_LEADS
    
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class TabularNames(object):
    """Configuration key names used in the tabular module."""
    E_META         = 'extract_'+CoreData.DataTypes.MetaData
    E_WAVE         = 'extract_'+CoreData.DataTypes.WaveForms
    E_MEDIAN       = 'extract_'+CoreData.DataTypes.MedianBeats
    ENG_META       = 'engineer_'+CoreData.DataTypes.MetaData
    ENG_WAVE       = 'engineer_'+CoreData.DataTypes.WaveForms
    ENG_MEDIAN     = 'engineer_'+CoreData.DataTypes.MedianBeats
    META_DICT      = 'meta_dict'
    SKIP_PERM      = 'ignore_permission'
    SKIP_DATA      = 'ignore_data'
    SKIP_INVALID   = 'ignore_invalid'
    CONFIRM_META   = 'confirm_meta'
    CONFIRM_WAVE   = 'confirm_wave'
    CONFIRM_MEDIAN = 'confirm_median'
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
    KEY            = 'key'
    FILENAM        = 'filename'
    SIG_LEN_W      = 'signal_length_w'
    SIG_LEN_M      = 'signal_length_m'
    PAD_VALUE      = 'pad_value'
    SN_W_PADDED    = 'sampling number padded (waveforms)'
    SN_M_PADDED    = 'sampling number padded (medianbeats)'
    DURATION_PADDED = 'duration padded (sec)'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class PlotNames:
    '''
    Constants used by the ECGDrawing plotting module.
    '''
    MILLIVOLT       = 'millivolt'
    MICROVOLT       = 'microvolt'
    LEAD_VOLTAGES   = 'lead_voltages'
    START_POS_FIRST = 'first'
    # #### standard ECG paper grid dimensions (mm)
    MINOR_GRID_MM   = 1.0
    MAJOR_GRID_MM   = 5.0
    # #### ECGDrawing slot names
    DEFAULT_LEADS   = '_default_leads'
    FIGURE          = 'figure'
    AXES            = 'axes'
    LAYOUT_MAPPER   = 'layout_mapper'
    STYLE           = 'style'
    MINOR_STEP_X    = 'minor_step_x'
    MAJOR_STEP_X    = 'major_step_x'
    MINOR_STEP_Y    = 'minor_step_y'
    MAJOR_STEP_Y    = 'major_step_y'
    PAPER_SPEED     = 'paper_speed'
    MM_PER_MV       = 'mm_per_mv'
