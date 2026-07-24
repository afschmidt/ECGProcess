import os
import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ecgprocess.constants import (
    TabularNames as TabNames,
)
from ecgprocess.errors import InputValidationError
from ecgprocess.plot_ecgs import ECGDrawing
from ecgprocess.writer import (
    FigureWriter,
    PixelWriter,
    WRITERS,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestPixelWriter(object):
    """
    Testing the pixel-tensor writer: NHWC stacking, channel variants,
    dtype casting, metadata row alignment, and the uniform-size guard.
    """
    # the expected canvas size: small_style figsize (4, 2) at dpi 40
    _H, _W = 80, 160
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_registered(self):
        assert WRITERS[TabNames.WRITE_PIXEL] is PixelWriter
        assert issubclass(PixelWriter, FigureWriter)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_stacked_tensor_and_metadata(self, tmp_path, make_context,
                                         make_figure_records, leads_12,
                                         small_style):
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        PixelWriter(kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'figures.npy', 'metadata.tsv'}
        stack = np.load(tmp_path / 'figures.npy')
        # one NHWC slice per record, RGBA by default, float32 by default
        assert stack.shape == (2, self._H, self._W, 4)
        assert stack.dtype == np.float32
        # rows align with the tensor slices, UIDs as index
        meta_tab = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t',
                               index_col=0)
        assert list(meta_tab.index) == ['a', 'b']
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_channel_variants(self, tmp_path, make_context,
                              make_figure_records, leads_12, small_style):
        meta, wave = make_figure_records(leads_12)
        for channels, depth in (('rgb', 3), ('gray', 1)):
            out = tmp_path / channels
            out.mkdir()
            ctx = make_context(out, e_meta=False, e_median=False)
            PixelWriter(channels=channels,
                        kwargs_call={'style': small_style,
                                     'sampling_rate': 100.0}).write(
                meta, wave, [], ctx)
            stack = np.load(out / 'figures.npy')
            # grayscale keeps the channel axis: uniform NHWC rank
            assert stack.shape == (2, self._H, self._W, depth)
        # an unknown channel format is systematic: fail at construction
        with pytest.raises(InputValidationError):
            PixelWriter(channels='cmyk')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_dtype_cast(self, tmp_path, make_context, make_figure_records,
                        leads_12, small_style):
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        PixelWriter(dtype=np.uint8,
                    kwargs_call={'style': small_style,
                                 'sampling_rate': 100.0}).write(
            meta, wave, [], ctx)
        stack = np.load(tmp_path / 'figures.npy')
        assert stack.dtype == np.uint8
        # the white figure background keeps the native 0-255 range
        assert stack.max() == 255
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_size_mismatch_raises(self, tmp_path, monkeypatch, make_context,
                                  make_figure_records, leads_12, small_style):
        # stacking requires a shared (height, width) across the chunk;
        # simulate per-record canvas drift and expect a loud failure
        shapes = iter([(10, 20, 4), (12, 20, 4)])
        monkeypatch.setattr(
            ECGDrawing, 'to_numpy',
            lambda self, crop=False, close=True: np.zeros(
                next(shapes), dtype=np.uint8))
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        with pytest.raises(InputValidationError, match='height'):
            PixelWriter(kwargs_call={'style': small_style,
                                     'sampling_rate': 100.0}).write(
                meta, wave, [], ctx)
        # fail-fast: nothing is written
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_skip_data_keeps_alignment(self, tmp_path, make_context,
                                       make_figure_records, leads_12,
                                       small_style):
        # only record 'b' carries the referenced key; with skip_data the
        # failing record is dropped from BOTH the tensor and the
        # metadata rows, so row i still matches slice i
        open_before = plt.get_fignums()
        meta, wave = make_figure_records(leads_12)
        meta[1]['extra'] = 7.0
        spec = [{'text': '{extra}', 'xy': (0.5, 0.5)}]
        ctx = make_context(tmp_path, e_median=False, skip_data=True)
        PixelWriter(annotate=spec,
                    kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        stack = np.load(tmp_path / 'figures.npy')
        meta_tab = pd.read_csv(tmp_path / 'metadata.tsv', sep='\t',
                               index_col=0)
        assert stack.shape[0] == 1
        # only the surviving record 'b' remains, keeping the alignment
        assert list(meta_tab.index) == ['b']
        uid, cause = ctx.failed_records[0]
        assert uid == 'a'
        assert 'Annotation failed' in cause
        assert plt.get_fignums() == open_before
