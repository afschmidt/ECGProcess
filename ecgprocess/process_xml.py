'''
A module to extract, metadata, median beats and raw waveforms from ECG XMLs.
'''
import pathlib
import warnings
import numpy as np
import ecgprocess.utils.reader_tools as reader_utils
import ecgprocess.utils.ecg_tools as ecg_utils
from lxml import etree
from ecgprocess.utils.reader_tools import(
    BaseReader,
)
from dataclasses import dataclass, field
from typing import (
    Optional, Self, Any, Literal,
)
from ecgprocess.utils.general import(
    ManagedProperty,
)
from ecgprocess.utils.config_tools import(
    ConfigParser,
)
from ecgprocess.errors import (
    is_type,
    _check_readable,
    Warn_MSG,
    Error_MSG,
)
from ecgprocess.constants import (
    UtilsReaderNames as RNames,
    ProcessXMLNames as PXMLNam,
    CoreData as Core,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# constants
CTypes = Core.DataTypes
CLeads = Core.Leads
CMeta = Core.MetaData
CProc = Core.ProcessingData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class ECGXMLReader(BaseReader):
    """
    Processes an XML file containing ECG data and extracts the metadata,
    median beats, and raw waveforms.
    
    Parameters
    ----------
    augment_leads : `bool`, default `False`
        Whether the augmented leads should be calculated if these are not
        already available in the source file.
    resample : `bool`, default `True`
        Whether to resample the ECG to a frequency of 500 Hertz.
    
    Attributes
    ----------
    augment_leads : `bool`
        Whether the augmented leads were calculated if these were unavailable.
    resample : `bool`
        Whether the ECG was resampled to a 500 Hertz frequency.
    
    Methods
    -------
    extract(config, skip_empty, parse_numeric, **kwargs)
        Processes the XML file content applying optional lead augmentation and
        resampling. The XML content will be mapped to class attributes.
    
    """
    # #### properties
    xml_tags = ManagedProperty(PXMLNam.XML_TAGS, list)
    raw_data = ManagedProperty(CProc.RAW, dict)
    _as_array:bool = True
    # #### parameters, with defaults
    augment_leads:bool = field(default=False)
    resample_500:bool = field(default=True)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __post_init__(self):
        """Validating inputs."""
        is_type(getattr(self, PXMLNam.AUG_LEADS), bool)
        is_type(getattr(self, PXMLNam.RESAMPLE), bool)
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def __call__(self, path:str, schema:str | None = None,
                 verbose:bool=False,
                 **kwargs:Optional[Any],
                 ) -> Self:
        """
        Reads an `.xml` file containing ECG readings, optionally validates this
        based on a .xsd schema, and map the XML file to a flat dictionary.
        
        Parameters
        ----------
        path : `str`
            The path to the .xml file.
        schema : `str`, default `NoneType`
            A path to an XML schema which will be used to valudate the XML file
            against.
        verbose : `bool`, default `False`
            Whether warnings and process info should be printed.
        **kwargs : any
            keyword arguments passed to flatten_dict.
        
        Attributes
        ----------
        xml_tags : `list` [`str`]
            A list of strings with parsed xml tags matching the `raw_data` keys.
        raw_data : `dict` [`str`, `any`]
            The raw parsed XML data.
        
        Returns
        -------
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes including the
            extracted XML data.
        """
        # #### check input
        is_type(path, (pathlib.PosixPath, pathlib.WindowsPath, str))
        is_type(schema, (type(None), pathlib.PosixPath, pathlib.WindowsPath,
                           str))
        is_type(verbose, bool)
        # #### assign to self
        self.verbose = verbose
        # #### confirm file is readable
        _check_readable(path)
        # #### validate XML
        if not schema is None:
            _check_readable(schema)
            parsed_xml = reader_utils.validate_xml(
                xml_path=path, xsd_path=schema, verbose=verbose)
        else:
            with open(path, 'rb') as xml:
                parsed_xml = etree.parse(xml)
        # map to flatten_dict
        xml_dict = reader_utils.flatten_dict(
            reader_utils.xml_to_dict(parsed_xml),
            **kwargs,
        )
        # ### store keys and data
        getattr(type(self), CProc.RAW).set_with_setter(self, xml_dict)
        getattr(type(self), PXMLNam.XML_TAGS).set_with_setter(
            self, list(xml_dict.keys()))
        # ### return
        return self
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    def extract(self, config:ConfigParser, bits:np.dtype | None=None,
                skip_empty:bool=True, parse_numeric:bool=True,
                **kwargs:Optional[Any]) -> Self:
        """
        Processes the raw ECG data and assign these to class attributes
        performing resampling and lead augmentation if requested.
        
        Parameters
        ----------
        config : `ConfigParser`
            A class instance of a parsed configuration file, mapping the XML
            content to class attributes. Specifically this should include
            dictionary attributes `MetaData`, `WaveForms`, `MedianBeats`,
            `OtherData`. The `MetaData` includes some privileged  keys including
            essential information to describe an ECG instance, as well as
            non-privileged  information. The difference between `OtherData` and
            `MetaData` is the way it is processed by other functions or methods
            with the `OtherData` processed without strong checks on its content.
            `WaveForms` and `MedianBeats` simply include the lead mappings.
            Please refer to the `constants.CoreData` class for the specifics
        parse_numeric : bool, default `True`
            Whether to check for numeric data accidentally recorded as string and
            try to parse these to int or float depending on the presence of a
            decimal separator.
        skip_empty : `bool`, default `True`
            Whether empty tags should be skipped or throw an error.
        bits : `np.dtype`, default `None`
            np.array bits passed to numpy.array dtype.
        **kwargs
            The keyword arguments for reader_tools.get_ecg_data.
            For the waveforms and medianbeats as_array and bits are hard coded
            so these will raise an error if supplied as kwargs.
        
        Attributes
        ----------
        MetaData : `dict` [`str`, `any`]
            ECG metadata.
        Waveforms : `dict` [`str`, `np.array`]
            The lead specific ECG waveforms.
        MedianBeats : `dict` [`str`, `np.array`]
            The lead specific ECG median beats.
        OtherData : `dict` [`str`, `any`]
            Other data.
        
        Returns
        -------
        self : `ECGXMLReader` instance
            Returns the class instance with updated attributes including the
            extracted XML data.
        """
        is_type(config, ConfigParser)
        is_type(skip_empty, bool)
        is_type(parse_numeric, bool)
        # update kwargs
        kwargs = {**{'parse_numeric': parse_numeric,
                     'skip_empty': skip_empty,
                     }, **kwargs}
        # #### get the configs
        md_cnf = config.get_section(CTypes.MetaData)
        wf_cnf = config.get_section(CTypes.WaveForms)
        mb_cnf = config.get_section(CTypes.MedianBeats)
        od_cnf = config.get_section(CTypes.OtherData)
        # #### extract metadata
        meta_data, meta_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=md_cnf,
                **kwargs,
            )
        # #### extract waveforms
        wave_data, wave_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=wf_cnf,
                as_array=self._as_array,
                bits=bits,
                **kwargs,
            )
        # #### extract median beats
        median_data, median_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=mb_cnf,
                as_array=self._as_array,
                bits=bits,
                **kwargs,
            )
        # #### extract other data
        other_data, other_missing = \
            reader_utils.get_ecg_data(
                getattr(self, CProc.RAW),
                config=od_cnf,
                **kwargs,
            )
        # #### resample to 500hz
        # first calculate the duration
        try:
            meta_data[CProc.Duration] =\
                (meta_data[CMeta.SN_W]/meta_data[CMeta.SF]
            )
        except TypeError:
            meta_data[CProc.Duration] = None
        # only run when the parameter is True, SF is not 500 and there
        # is a duration
        meta_data[CProc.SF_NEW] = None
        if getattr(self, PXMLNam.RESAMPLE) == True:
            # confirm SF is present
            if not CMeta.SF in meta_data or meta_data[CMeta.SF] is None:
                raise KeyError(f'`{CMeta.SF}` is necessary to resample '
                               'the ECG signal.')
            # if it is, check whether there is a need to resample the signals.
            if int(meta_data[CMeta.SF]) != 500 and\
                    not meta_data[CProc.Duration] is None:
                # set the new SF
                meta_data[CProc.SF_NEW] = 500
                # confirm there is waveform data
                if len(wave_missing) == 12:
                    if skip_empty == False:
                        raise AttributeError(
                            Error_MSG.MISSING_SIGNAL.format('waveform'))
                else:
                    wave_data = ecg_utils.resampling_500hz(
                        wave_data, duration=meta_data[CProc.Duration])
                # confirm there is median beats data
                if len(median_missing) == 12:
                    if skip_empty == False:
                        raise AttributeError(
                            Error_MSG.MISSING_SIGNAL.format('median beat'))
                else:
                    median_data = ecg_utils.resampling_500hz(
                        median_data, median=True)
        # ### See if we need to get the augmented leads
        if getattr(self, PXMLNam.AUG_LEADS) == True and len(wave_missing) > 0:
            wave_data = ecg_utils.get_limb_leads(wave_data)
            median_data = ecg_utils.get_limb_leads(median_data)
        # ### do we print missing tags
        if self.verbose == True:
            missing_tags = [tag for tag in (
                meta_missing + wave_missing + median_missing + other_missing
            ) if tag is not None]
            if len(missing_tags)>0:
                warnings.warn(Warn_MSG.MISSING_TAG.format(missing_tags))
        # #### assing stuff to attributes
        setattr(self, CTypes.MetaData, meta_data)
        setattr(self, CTypes.OtherData, other_data)
        setattr(self, CTypes.WaveForms, wave_data)
        setattr(self, CTypes.MedianBeats, median_data)
        # #### return stuff
        return self

