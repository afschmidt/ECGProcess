'''
Constants used by ECGProcess
'''

import numpy as np


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
    RESULTS_DICT          = 'general_info'
    SAMPLING_FREQ         = 'samplingfrequency'
    SF_ORIGINAL           = 'sf_original'
    SF                    = 'sf'
    UNIT                  = 'Unit free'
    LEAD                  = 'Lead'
    LEAD_III              = 'III'
    LEAD_II               = 'II'
    LEAD_I                = 'I'
    LEAD_aVR              = 'aVR'
    LEAD_aVL              = 'aVL'
    LEAD_aVF              = 'aVF'
    OVERSAMPLED           = 'oversampled'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class DICOMTags(object):
    '''
    The DICOM tags ECGDICOMReader will look for.
    
    This simply is a collection of dictionary with the keys representing the
    `target` (new) name and the values the `source` (old) names.
    
    Attributes
    ----------
    METATDATA
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
    RESULTS_DICTIONARY
        A dicionary describing the non-array results extracted from `METADATA`
        and `WAVE_FROMS`. Here the values should match the keys in METATDATA
        and WAVE_FORMS, with the `RESULTS_DICTIONARY` keys matching the
        updated names.
        
    '''
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self):
        '''
        Initialises the DICOMTags class.
        '''
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.METATDATA = {
            'SOPinstanceUID'        : 'SOPInstanceUID',
            'SERIESinstanceUID'     : 'SeriesInstanceUID',
            'STUDYinstanceUID'      : 'StudyInstanceUID',
            'PatientID'             : 'PatientID',
            'StudyDate'             : 'StudyDate',
            'StudyTime'             : 'StudyTime',
            'AccessionNumber'       : 'AccessionNumber',
            'PatientBirthDate'      : 'PatientBirthDate',
            'PatientName'           : 'PatientName',
            'PatientSex'            : 'PatientSex',
            'StudyDescription'      : 'StudyDescription',
            'AcquisitionDateTime'   : 'AcquisitionDateTime',
            'AcquisitionTimeZone'   : 'TimezoneOffsetFromUTC',
            'Manufacturer'          : 'Manufacturer',
            'ManufacturerModelName' : 'ManufacturerModelName',
            'SoftwareVersions'      : 'SoftwareVersions',
            'DataExportedBy'        : 'IssuerOfPatientID',
        }
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.WAVE_FORMS = {
                'TimeOffset'                     : 'MultiplexGroupTimeOffset',
                ProcessDicomNames.CHANNEL_NUMBER : 'NumberOfWaveformChannels',
                'ChannelSensitivity'             : 'ChannelSensitivity',
                'ChannelBaseline'                : 'ChannelBaseline',
                'ChannelSampleSkew'              : 'ChannelSampleSkew',
                'FilterLowFrequency'             : 'FilterLowFrequency',
                'FilterHighFrequency'            : 'FilterHighFrequency',
                'NotchFilterFrequency'           : 'NotchFilterFrequency',
                ProcessDicomNames.SF             : 'SamplingFrequency',
                ProcessDicomNames.SF_ORIGINAL    : 'SamplingFrequency',
        }
        # objects which cannot be extracted in a loop
        self.WAVE_FORMS_LIST = {
            # ProcessDicomNames.LEAD_INFO     : ['lead_info', 0],
            # ProcessDicomNames.LEAD_VOLTAGES : ['make_leadvoltages', 0],
            ProcessDicomNames.WAVE_ARRAY    : ['waveform_array', 0],
        }
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.MEDIAN_BEATS_LIST = {
            ProcessDicomNames.MEDIAN_ARRAY   : ['waveform_array', 1],
            ProcessDicomNames.LEAD_INFO      : ['lead_info', 1],
            ProcessDicomNames.LEAD_VOLTAGES2 : ['make_leadvoltages', 1]
        }
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.RESULTS_DICTIONARY = {
            "SOPinstanceUID"           : "SOPinstanceUID",
            "SERIESinstanceUID"        : "SERIESinstanceUID",
            "STUDYinstanceUID"         : "STUDYinstanceUID",
            "PatientID"                : "PatientID",
            "PatientBirthDate"         : "PatientBirthDate",
            "PatientName"              : "PatientName",
            "PatientSex"               : "PatientSex",
            "StudyDescription"         : "StudyDescription",
            "AcquisitionTimeZone"      : "AcquisitionTimeZone",
            "AccessionNumber"          : "AccessionNumber",
            "SamplingFrequency"        : ProcessDicomNames.SAMPLING_FREQ,
            "OriginalSamplingFrequency": ProcessDicomNames.SF_ORIGINAL,
            "ChannelNumber"            : "ChannelNumber",
            "ChannelSensitivity"       : "ChannelSensitivity",
            "ChannelBaseline"          : "ChannelBaseline",
            "ChannelSampleSkew"        : "ChannelSampleSkew",
            "FilterLowFrequency"       : "FilterLowFrequency",
            "FilterHighFrequency"      : "FilterHighFrequency",
            "NotchFilterFrequency"     : "NotchFilterFrequency",
            "Manufacturer"             : "Manufacturer",
            "ManufacturerModelName"    : "ManufacturerModelName",
            "SoftwareVersions"         : "SoftwareVersions",
            "DataExportedBy"           : "DataExportedBy",
            # "Waveforms"                : ProcessDicomNames.LEAD_VOLTAGES,
            # "MedianWaveforms"          : ProcessDicomNames.LEAD_VOLTAGES2,
        }
