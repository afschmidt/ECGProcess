'''
Constants used by ECGProcess
'''

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
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
        The internally used lead names (standard 12-lead ECG).
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
        # #### Capture all lead values (excludes private attributes and methods)
        _ALL = tuple(v for k, v in vars().items()
                     if not k.startswith('_') and not callable(v))
        
        @classmethod
        def values(cls):
            '''Return all lead names in standard order.'''
            return cls._ALL
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
        # #### Capture all metadata field values (excludes private attributes and methods)
        _ALL = tuple(v for k, v in vars().items()
                     if not k.startswith('_') and not callable(v))
        
        @classmethod
        def values(cls):
            '''Return all metadata field names in standard order.'''
            return cls._ALL
    # /////////////////////////////////////////////////////////////////////////
    class ProcessingData:
        '''
        Contains constants for attributes and variables created by the process
        modules.
        '''
        TAGS      = 'tags'
        RAW       = 'raw_data'
        # sampling number / sampling frequency (original)
        Duration_W = 'duration (waveforms, sec)'
        Duration_M = 'duration (medianbeats, sec)'
        # the rate of each stored source: the target when at it, else None
        SF_NEW_W  = 'sampling frequency (processed, waveforms)'
        SF_NEW_M  = 'sampling frequency (processed, medianbeats)'
        RESAMPLE  = 'resample_500'
        AUG_LEADS = 'augment_leads'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class PrivilegedNames(object):
    '''
    Registry of names that users cannot freely override in config files
    or when extending the system (e.g., extra_leads).
    
    Names are derived from CoreData so this registry stays in sync
    automatically.
    
    Examples
    --------
    >>> PrivilegedNames.is_reserved('I')
    True
    >>> PrivilegedNames.is_reserved('V7')
    False
    >>> len(PrivilegedNames.LEADS) == len(CoreData.Leads.values())
    True
    >>> len(PrivilegedNames.METADATA) == len(CoreData.MetaData.values())
    True
    '''
    # #### Standard ECG lead names, count derived from CoreData.Leads
    LEADS = CoreData.Leads.values()
    # #### Privileged metadata field names, count derived from MetaData
    METADATA = CoreData.MetaData.values()
    # #### All reserved names (union for quick lookup)
    ALL = frozenset(LEADS + METADATA)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def is_reserved(cls, name: str) -> bool:
        '''
        Check if a name is reserved/privileged.
        
        Parameters
        ----------
        name : `str`
            Name to check.
        
        Returns
        -------
        `bool`
            `True` if the name is reserved, `False` otherwise.
        '''
        return name in cls.ALL
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self) -> str:
        '''User-friendly string representation of reserved names.'''
        lines = ['Privileged & Reserved Names', '=' * 27, '']
        lines.append(f'Standard ECG Leads ({len(self.LEADS)}):')
        lines.append('  ' + ', '.join(self.LEADS))
        lines.append('')
        lines.append(f'Privileged Metadata Fields ({len(self.METADATA)}):')
        for i, field in enumerate(self.METADATA, 1):
            lines.append(f'  {i:2d}. {field}')
        return '\n'.join(lines)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self) -> str:
        '''Developer-friendly representation.'''
        return (f"PrivilegedNames(leads={len(self.LEADS)}, "
                f"metadata={len(self.METADATA)}, "
                f"total={len(self.ALL)})")

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class UtilsReaderNames(object):
    '''
    Names used in the Utils Reader Tools module.
    '''
    DICOM_WAVE_ARRAY     = 'waveform_array'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class UtilsGeneralNames(object):
    '''
    Names used in the Utils General module.
    '''
    LXML_ERROR         = 'expected'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
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

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ProcessXMLNames(object):
    '''
    Names used in the process.process_xml module.
    '''
    RESAMPLE  = CoreData.ProcessingData.RESAMPLE
    AUG_LEADS = CoreData.ProcessingData.AUG_LEADS

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ProcessDicomNames(object):
    """Names used in the process.process_dicom module."""
    RESAMPLE  = CoreData.ProcessingData.RESAMPLE
    AUG_LEADS = CoreData.ProcessingData.AUG_LEADS
    
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
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
    SKIP_MISSING   = 'ignore_missing_leads'
    CHUNK_STRICT   = 'chunk_strict'
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
    FAILED_REC_L   = 'failed_record_list'
    TABLE_CALLED   = 'table_called'
    WRITE_TAB      = 'table'
    # NOTE 'numpy' is a legacy `file_type` alias for 'npz'; it is removed
    # together with the deprecated `file_type` parameter
    WRITE_NUMPY    = 'numpy'
    WRITE_NPZ      = 'npz'
    WRITE_TFLOW    = 'tensorflow'
    WRITE_NPY      = 'npy'
    WRITE_FIGURE   = 'figure'
    WRITE_PIXEL    = 'pixel'
    WRITE_WFDB     = 'wfdb'
    WRITE_XML      = 'xml'
    WRITE_ECG_PATH = 'target_path'
    ROW_ORDER_SAMPLE = 'sample'
    ROW_ORDER_LEAD = 'lead'
    ID_START       = '_id_start_number'
    KEY            = 'key'
    FILENAM        = 'filename'
    SIG_LEN_W      = 'signal_length_w'
    SIG_LEN_M      = 'signal_length_m'
    PAD_VALUE      = 'pad_value'
    SN_W_PADDED    = 'sampling number padded (waveforms)'
    SN_M_PADDED    = 'sampling number padded (medianbeats)'
    DURATION_PADDED = 'duration padded (sec)'
    # FailedFiles.txt cause label for the strictly-partial missing-lead
    # skip; kept distinct from the all-None `"No data"` cause.
    # Controlled by: ignore_missing_leads
    MISSING_LEAD_CAUSE = 'Missing lead(s): {} [ignore_missing_leads]'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class FileNames(object):
    """
    Filenames written by `ECGTable.write_ecg` and the writer module.
    """
    # /////////////////////////////////////////////////////////////////////////
    # #### per-chunk data-file base names
    # the `_N` chunk suffix and the writer-owned extension are appended
    # by `BaseWriter.file_names`
    METADATA     = 'metadata'
    WAVEFORMS    = 'waveforms'
    MEDIANBEATS  = 'medianbeats'
    ECG_DATA     = 'ecg_data'
    FIGURES      = 'figures'
    # /////////////////////////////////////////////////////////////////////////
    # #### bookkeeping files (fixed names, no chunk suffix)
    META_HEADER  = 'header_metadata.txt'
    CHUNK_RECORD = 'chunkrecord.txt'
    FAILED_FILES = 'FailedFiles.txt'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class WriteNames(object):
    """Names and messages used by the writer module."""
    # /////////////////////////////////////////////////////////////////////////
    # NOTE REMOVE after file_type is removed in ECGTable
    REMOVAL_VERSION = '2.0.0'
    # /////////////////////////////////////////////////////////////////////////
    # deprecation message template: {name}, {version}, {replacement}
    DEPRECATED = ('`{}` is deprecated and will be removed in v{}; '
                  'use `{}` instead.')
    # /////////////////////////////////////////////////////////////////////////
    # the FailedFiles.txt cause for a write-stage annotation failure:
    # Controlled by: ignore_data
    ANNOT_CAUSE = 'Annotation failed (ignore_data): {}'
    # /////////////////////////////////////////////////////////////////////////
    # the FailedFiles.txt cause for a write-stage XML export failure:
    # Controlled by: ignore_data
    XML_CAUSE = 'XML export failed (ignore_data): {}'
    # /////////////////////////////////////////////////////////////////////////
    # the pixel writer channel formats
    RGBA = 'rgba'
    RGB  = 'rgb'
    GRAY = 'gray'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
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
    # #### annotation spec-dict keys
    ANNOT_TEXT      = 'text'
    ANNOT_XY        = 'xy'
    # #### ECGDrawing slot names
    DEFAULT_LEADS   = '_default_leads'
    META_DATA       = '_meta_data'
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
