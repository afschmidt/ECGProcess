'''
Constants used by ECGProcess
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class ProcessDicomNames(object):
    '''
    Names used in the process_dicom module.
    '''

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
        A dictionary describing the wavefrom data one wants to extract.
    MEADIAN_BEATS
        A dictionary describing the median beats data one wants to extract.
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
        }
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.MEADIAN_BEATS = {
        }


