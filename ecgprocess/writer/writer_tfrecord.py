"""
The lazily-imported TensorFlow TFRecord writer.
"""

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# imports
from __future__ import annotations
import os
from types import ModuleType
from typing import Any
import numpy as np
from ecgprocess.constants import (
    CoreData as Core,
    TabularNames as TabNames,
)
from ecgprocess.errors import Error_MSG, is_type
from ecgprocess.utils.ecg_tools import (
    signal_dicts_to_numpy_array,
)
from ecgprocess.writer.writer_base import (
    BaseWriter,
    WriteContext,
    register_writer,
    _meta_to_array,
    _write_metadata_header,
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# constants
CTypes = Core.DataTypes

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
@register_writer(TabNames.WRITE_TFLOW)
class TFRecordWriter(BaseWriter):
    """
    Writes ECG data to a single `.tfrecord`.
    
    Parameters
    ----------
    numeric_meta : `bool`, default `True`
        Whether non-numeric metadata columns are dropped before writing.
    """
    # /////////////////////////////////////////////////////////////////////////
    FILE_EXT = '.tfrecord'
    # /////////////////////////////////////////////////////////////////////////
    def __init__(self, numeric_meta: bool = True) -> None:
        """Initialise the tfrecord writer."""
        is_type(numeric_meta, bool)
        self.numeric_meta = numeric_meta
    # /////////////////////////////////////////////////////////////////////////
    @staticmethod
    def _import_tensorflow() -> ModuleType:
        """
        Lazily import tensorflow.
        
        TensorFlow is an optional dependency: it is imported here, per
        `write` call, rather than at module import time, so that the rest
        of the package works without it.
        
        Returns
        -------
        tf : `ModuleType`
            The imported tensorflow module.
        
        Raises
        ------
        ImportError
            If tensorflow is not installed, naming the install route.
        """
        try:
            # filtering out TF warnings
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
            import tensorflow as tf
        except ImportError as exc:
            raise ImportError(Error_MSG.MISSING_TENSORFLOW) from exc
        return tf
    # /////////////////////////////////////////////////////////////////////////
    def write(self, meta_list: list[dict[str, Any]],
              wave_list: list[dict[str, "np.ndarray"]],
              median_list: list[dict[str, "np.ndarray"]],
              ctx: WriteContext,
              ) -> None:
        """
        Write a chunk of ECG data to a single `.tfrecord`.
        
        The enabled sources are stored as flattened `tf.train.Feature`
        float lists in one `tf.train.Example`; the metadata column names
        are written to a `header_metadata.txt` sidecar.
        
        Parameters
        ----------
        meta_list : `list` [`dict` [`str`, `any`]]
            A list of dictionaries containing metadata.
        wave_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing waveform signals.
        median_list : `list` [`dict` [`str`, `np.ndarray`]]
            A list of dictionaries containing median beat signals.
        ctx : `WriteContext`
            The context carrying export flags, target path, and helpers.
        
        Raises
        ------
        ImportError
            If tensorflow is not installed.
        """
        # #### import tensorflow lazily before any file is written
        tf = self._import_tensorflow()
        # #### set the filename
        _, _, _, ECG_FILE, _ = self.file_names(chunk_num=ctx.chunk_num)
        # #### assemble the features for the enabled sources
        res_dict = {}
        header = None
        if ctx.e_meta:
            array, header = _meta_to_array(meta_list, self.numeric_meta)
            res_dict[CTypes.MetaData] = tf.train.Feature(
                float_list=tf.train.FloatList(value=array.flatten()))
        if ctx.e_wave:
            res_dict[CTypes.WaveForms] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        wave_list, padding=False).flatten()))
        if ctx.e_median:
            res_dict[CTypes.MedianBeats] = tf.train.Feature(
                float_list=tf.train.FloatList(
                    value=signal_dicts_to_numpy_array(
                        median_list, padding=False).flatten()))
        # #### write the record and the metadata header sidecar
        with tf.io.TFRecordWriter(
                os.path.join(ctx.target, ECG_FILE)) as record_writer:
            record_writer.write(
                tf.train.Example(
                    features=tf.train.Features(feature=res_dict)
                ).SerializeToString())
        # NOTE header is not None exactly when metadata was exported
        if header is not None:
            _write_metadata_header(ctx.target, header)
