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
    LEAD_UNITS            = 'WaveformUnits'
    LEAD_UNITS2           = 'MedianWaveformUnits'
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
    CHANNEL_SENS_UNIT     = 'ChannelSensitivityUnitsSequence'
    STUDY_DATE            = 'StudyDate'
    STUDY_TIME            = 'StudyTime'
    ACQUISITION_DATE      = 'AcquisitionDateTime'
    RESULTS_DICT          = 'GeneralInfo'
    SAMPLING_FREQ         = 'SamplingFrequency'
    SAMPLING_NUMBER       = 'NumberOfWaveformSamples'
    SAMPLING_NUMBER_M     = 'NumberOfWaveformSamples (MEDIAN)'
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
    CODE_MEANING          = 'CodeMeaning'
    ECG_TRAIT_VALUE       = 'NumericValue'
    ECG_TRAIT_QT          = 'QT Interval'
    ECG_TRAIT_QT_U        = 'QT Interval UNIT'
    ECG_TRAIT_QRS_D       = 'QRS Duration'
    ECG_UNIT              = 'MeasurementUnitsCodeSequence'
    ECG_UNIT_STRING       = ' UNIT'
    WAVE_SCALING          = 'mm_mv'
    MICROVOLT             = 'microvolt'
    MILLIVOLT             = 'millivolt'
    ECG_SIGNAL            = 'ecg_signal'
    WAVE_TYPE             = 'wave_type'
    PLOT_LAYOUT           = 'image_layout'
    PLOT_HEIGHT           = 'height'
    PLOT_WIDTH            = 'width'
    PAPER_HEIGHT          = 'paper_h'
    PAPER_WIDTH           = 'paper_w'
    PLOT_UNIT             = 'ecg_unit'
    PLOT_AXES             = 'ax'
    PLOT_FIG              = 'fig'
    PLOT_FIGSIZE          = 'figsize'
    ECG_READER            = 'ECG_READER'


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
    WAVE_FORMS_DICT
        A dictionary describing the median beats data one wants to extract
        from the 'WaveformSequence' or 'ChannelDefinitionSequence' attributes.
        The dictionary value contains a list with an object name (str) and
        element to extract.
    MEDIAN_BEATS_DICT
        A dictionary describing the median beats data one wants to extract
        from the 'WaveformSequence' or 'ChannelDefinitionSequence' attributes.
        The dictionary value contains a list with an object name (str) and
        element to extract.
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
    WAVE_FORMS_DICT = {
        ProcessDicomNames.WAVE_ARRAY    : ['waveform_array', 0],
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ECG_INTERPERTATION_DICT ={
        'QT Interval' : ['QT Interval'],
        'QTc Interval': ['QTc Interval'],
        'RR Interval': ['RR Interval'],
        'VRate': ['VRate', 'Ventricular Heart Rate'],
        'QRS Duration': ['QRS Duration'],
        'QRS Axis': ['QRS Axis'],
        'T Axis': ['T Axis'],
        'P Axis': ['P Axis'],
        'PR Interval': ['PR Interval'],
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MEDIAN_BEATS = {
        'TimeOffset'                      : 'MultiplexGroupTimeOffset',
        ProcessDicomNames.CHANNEL_NUMBER  : 'NumberOfWaveformChannels',
        ProcessDicomNames.SAMPLING_NUMBER : 'NumberOfWaveformSamples',
        'ChannelSensitivity'              : 'ChannelSensitivity',
        'ChannelBaseline'                 : 'ChannelBaseline',
        'ChannelSampleSkew'               : 'ChannelSampleSkew',
        'FilterLowFrequency'              : 'FilterLowFrequency',
        'FilterHighFrequency'             : 'FilterHighFrequency',
        'NotchFilterFrequency'            : 'NotchFilterFrequency',
    }
    MEDIAN_BEATS = {k + ' (MEDIAN)': v for k, v in MEDIAN_BEATS.items()}
    MEDIAN_BEATS_DICT = {
        ProcessDicomNames.MEDIAN_ARRAY   : ['waveform_array', 1],
        ProcessDicomNames.LEAD_INFO      : ['lead_info', 1],
        ProcessDicomNames.LEAD_VOLTAGES2 : ['make_leadvoltages', 1]
    }
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # RESULTS_LIST = [
    #     ProcessDicomNames.SOP_UID,
    #     "SERIESinstanceUID",
    #     "STUDYinstanceUID",
    #     "PatientID",
    #     "PatientBirthDate",
    #     "PatientName",
    #     "PatientSex",
    #     "StudyDescription",
    #     "AcquisitionTimeZone",
    #     "AccessionNumber",
    #     ProcessDicomNames.SAMPLING_NUMBER,
    #     ProcessDicomNames.SAMPLING_FREQ,
    #     ProcessDicomNames.SF_ORIGINAL,
    #     ProcessDicomNames.DURATION,
    #     "ChannelNumber",
    #     "ChannelSensitivity",
    #     "ChannelBaseline",
    #     "ChannelSampleSkew",
    #     "FilterLowFrequency",
    #     "FilterHighFrequency",
    #     "NotchFilterFrequency",
    #     "Manufacturer",
    #     "ManufacturerModelName",
    #     "SoftwareVersions",
    #     "DataExportedBy",
    # ] + ECG_INTERPERTATION_LIST
     


