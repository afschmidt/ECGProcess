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
    ORIG_DCMREAD_INST     = 'dmcread_instance'

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
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
    def __init__(self):
        '''
        Initialises the DICOMTags class.
        '''
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.METADATA = {
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
        self.RESULTS_LIST = [
             "SOPinstanceUID",
             "SERIESinstanceUID",
             "STUDYinstanceUID",
             "PatientID",
             "PatientBirthDate",
             "PatientName",
             "PatientSex",
             "StudyDescription",
             "AcquisitionTimeZone",
             "AccessionNumber",
             ProcessDicomNames.SAMPLING_FREQ,
             ProcessDicomNames.SF_ORIGINAL,
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
             # ProcessDicomNames.LEAD_VOLTAGES,
             # ProcessDicomNames.LEAD_VOLTAGES2,
        ]
