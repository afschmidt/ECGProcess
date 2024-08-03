'''
Constants used by ECGProcess
'''

from dataclasses import dataclass
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

class ProcessDicomNames(object):
    '''
    Names used in the process_dicom module.
    '''
    MEDIAN_PRESENT        = 'MedianWaveformPresent'
    WAVE_ARRAY            = 'Raw_Waveforms'
    MEDIAN_ARRAY          = 'Raw_MedianWaveforms'
    LEAD_VOLTAGES         = 'Waveforms'
    LEAD_VOLTAGES2        = 'MedianWaveforms'
    LEAD_INFO             = 'lead_info_final'
    WAVE_FORM_SEQ         = 'WaveformSequence'
    CHANNEL_DEF_SEQ       = 'ChannelDefinitionSequence'
    CHANNEL_NUMBER        = 'ChannelNumber'
    CHANNEL_SOURCE_SEQ    = 'ChannelSourceSequence'
    CHANNEL_CODE_MEANING  = 'CodeMeaning'
    CHANNEL_SENS          = 'ChannelSensitivity'
    STUDY_DATE            = 'StudyDate'
    STUDY_TIME            = 'StudyTime'
    ACQUISITION_DATE      = 'AcquisitionDateTime'
    RESULTS_DICT          = 'GeneralInfo'
    SAMPLING_FREQ         = 'SamplingFrequency'
    SAMPLING_NUMBER       = 'NumberOfWaveformSamples'
    SF_ORIGINAL           = 'SamplingFrequencyOriginal'
    SF                    = 'sf'
    DURATION              = 'Duration'
    UNIT                  = 'Unit free'
    LEAD                  = 'Lead'
    LEAD_III              = 'III'
    LEAD_II               = 'II'
    LEAD_I                = 'I'
    LEAD_aVR              = 'aVR'
    LEAD_aVL              = 'aVL'
    LEAD_aVF              = 'aVF'
    OVERSAMPLED           = 'oversampled'
    ORIG_DCMREAD_INST     = 'DMCReadInstance'
    SOP_UID               = 'SOPinstanceUID'
    # INFO_L                = 'GeneralInfoList'
    # WAVE_L                = 'WaveformsList'
    # MEDIAN_L              = 'MedianWaveformsList'
    KEY_L                 = 'IndexList'
    INFO_T                = 'GeneralInfoTable'
    WAVE_T                = 'WaveFormsTable'
    MEDIAN_T              = 'MedianWaveTable'
    INFO_FILE             = 'GeneralInfoTable.tsv.gz'
    WAVE_FILE             = 'WaveFormsTable.tsv.gz'
    MEDIAN_FILE           = 'MedianWaveTable.tsv.gz'
    FAILED_FILE           = 'FailedFiles.txt'
    FPATH_L               = 'FailedPathList'
    RPATH_L               = 'RawPathList'
    CPATH_L               = 'CuratedPathList'
    SAMPLING_SEQ          = 'SamplingSequence'
    COL_LEAD              = 'Lead'
    COL_VOLTAGE           = 'Voltage'
    COL_WAVETYPE          = 'Waveform type'
    WAVETYPE_RHYTHM       = 'rhythm'
    WAVETYPE_MEDIAN       = 'median'
    WRITE_ECS_PATH        = 'target_path'
    PREVIOUS_HEADER       = 'previous_header'
    TABLE_CALLED          = 'table_called'
    ECG_INTERPERTATION    = 'WaveformAnnotationSequence'
    ECG_CONCEPTNAME       = 'ConceptNameCodeSequence'
    ECG_TRAIT_NAME        = 'CodeMeaning'
    ECG_TRAIT_VALUE       = 'NumericValue'


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
    WAVE_FORMS_LIST
        A dictionary describing the waveform data one wants to extract.
        The dictionary value contains a list with an object name (str) and
        element to extract.
    MEADIAN_BEATS_LIST
        A dictionary describing the median beats data one wants to extract.
        The dictionary value contains a list with an object name (str) and
        element to extract.
    RESULTS_LIST
        A list of instance attribute one wants to extract, should map
        predominantly to the keys in  `METADATA` and `WAVE_FROMS`.
        
    '''
    # /////////////////////////////////////////////////////////////////////////
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    METADATA = {
        ProcessDicomNames.SOP_UID : 'SOPInstanceUID',
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
        'TimeOffset'                      : 'MultiplexGroupTimeOffset',
        ProcessDicomNames.CHANNEL_NUMBER  : 'NumberOfWaveformChannels',
        ProcessDicomNames.SAMPLING_NUMBER : 'NumberOfWaveformSamples',
        'ChannelSensitivity'              : 'ChannelSensitivity',
        'ChannelBaseline'                 : 'ChannelBaseline',
        'ChannelSampleSkew'               : 'ChannelSampleSkew',
        'FilterLowFrequency'              : 'FilterLowFrequency',
        'FilterHighFrequency'             : 'FilterHighFrequency',
        'NotchFilterFrequency'            : 'NotchFilterFrequency',
        ProcessDicomNames.SF              : 'SamplingFrequency',
        ProcessDicomNames.SF_ORIGINAL     : 'SamplingFrequency',
    }
    # objects which cannot be extracted in a loop
    WAVE_FORMS_LIST = {
        ProcessDicomNames.WAVE_ARRAY    : ['waveform_array', 0],
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ECG_INTERPERTATION_LIST =[
        'QT Interval',
        'QTc Interval',
        'RR Interval',
        'VRate',
        'QRS Duration',
        'QRS Axis',
        'T Axis',
        'P Axis',
        'PR Interval',
    ]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MEDIAN_BEATS_LIST = {
        ProcessDicomNames.MEDIAN_ARRAY   : ['waveform_array', 1],
        ProcessDicomNames.LEAD_INFO      : ['lead_info', 1],
        ProcessDicomNames.LEAD_VOLTAGES2 : ['make_leadvoltages', 1]
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RESULTS_LIST = [
        ProcessDicomNames.SOP_UID,
        "SERIESinstanceUID",
        "STUDYinstanceUID",
        "PatientID",
        "PatientBirthDate",
        "PatientName",
        "PatientSex",
        "StudyDescription",
        "AcquisitionTimeZone",
        "AccessionNumber",
        ProcessDicomNames.SAMPLING_NUMBER,
        ProcessDicomNames.SAMPLING_FREQ,
        ProcessDicomNames.SF_ORIGINAL,
        ProcessDicomNames.DURATION,
        "ChannelNumber",
        "ChannelSensitivity",
        "ChannelBaseline",
        "ChannelSampleSkew",
        "FilterLowFrequency",
        "FilterHighFrequency",
        "NotchFilterFrequency",
        "Manufacturer",
        "ManufacturerModelName",
        "SoftwareVersions",
        "DataExportedBy",
    ] + ECG_INTERPERTATION_LIST
     


