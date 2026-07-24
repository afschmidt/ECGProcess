import os
import pytest
import matplotlib.pyplot as plt
from ecgprocess.constants import (
    CoreData as Core,
)
from ecgprocess.errors import InputValidationError
from ecgprocess.plot_ecgs import ECGDrawing
from ecgprocess.writer import (
    FigureWriter,
)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# core names
CMeta = Core.MetaData

# the PNG file signature (first 8 bytes of any valid PNG)
_PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestFigureWriter(object):
    """
    Testing the plotting-specific behaviour of the per-record image
    writer: the default clinical layout (3x4 grid plus full-width
    rhythm strip), per-UID image files, format selection, source
    selection, and figure cleanup.
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default_mapper(self):
        # the built-in layout is the clinical 3x4 grid, column order
        # (I II III) (aVR aVL aVF) (V1 V2 V3) (V4 V5 V6), plus a
        # full-width lead II rhythm strip on its own bottom row
        mapper = FigureWriter.DEFAULT_MAPPER
        assert mapper['I'] == (0, slice(0, 1))
        assert mapper['II'] == (1, slice(0, 1))
        assert mapper['aVR'] == (0, slice(1, 2))
        assert mapper['V6'] == (2, slice(3, 4))
        assert mapper['II strip'] == (3, slice(0, 4))
        assert len(mapper) == 13
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_one_png_per_uid(self, tmp_path, make_context,
                             make_figure_records, leads_12, small_style):
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        FigureWriter(kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
        for name in ('a.png', 'b.png'):
            with open(tmp_path / name, 'rb') as fh:
                assert fh.read(8) == _PNG_MAGIC
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_image_format_svg(self, tmp_path, make_context,
                              make_figure_records, leads_12, small_style):
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        FigureWriter(image_format='svg',
                     kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.svg', 'b.svg'}
        with open(tmp_path / 'a.svg') as fh:
            assert '<svg' in fh.read(1024)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_dual_source_raises(self, tmp_path, make_context,
                                make_figure_records):
        # the writer renders exactly one source; extracting both would
        # silently drop one and collide on the <UID> filenames
        meta, wave = make_figure_records(['I'])
        _, median = make_figure_records(['I'], length=60)
        ctx = make_context(tmp_path)
        with pytest.raises(InputValidationError):
            FigureWriter().write(meta, wave, median, ctx)
        # fail-fast: nothing is written
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_median_source(self, tmp_path, make_context,
                           make_figure_records, leads_12, small_style):
        # a median beat is a single short beat; tiling would slice it
        # into meaningless column windows, so tile_x is disabled
        meta, median = make_figure_records(leads_12, length=60)
        ctx = make_context(tmp_path, e_wave=False)
        FigureWriter(source='median', tile_x=False,
                     kwargs_call={'style': small_style}).write(
            meta, [], median, ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_figures_closed_after_write(self, tmp_path, make_context,
                                        make_figure_records, leads_12,
                                        small_style):
        open_before = plt.get_fignums()
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        FigureWriter(kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert plt.get_fignums() == open_before

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestFigureWriterAnnotate(object):
    """
    Testing the metadata-driven annotation option: per-record template
    resolution, the metadata-extraction guard, and the skip-and-record
    error path governed by `ctx.skip_data`.
    """
    # a literal annotation needing no metadata
    _SPEC_LIT = [{'text': 'HELLOMARK', 'xy': (0.5, 0.99)}]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_bad_spec_raises_at_init(self):
        # a malformed spec is systematic; it must fail at construction,
        # not mid-batch
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=[{'xy': (0.5, 0.5)}])
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=[{'text': 'x', 'xy': (0.5,)}])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_annotate_forwarded_per_record(self, tmp_path, monkeypatch,
                                           make_context, make_figure_records,
                                           leads_12, small_style):
        calls = []
        original = ECGDrawing.annotate
        def _spy(self, annotations):
            calls.append(annotations)
            return original(self, annotations)
        monkeypatch.setattr(ECGDrawing, 'annotate', _spy)
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        FigureWriter(annotate=self._SPEC_LIT,
                     kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert calls == [self._SPEC_LIT, self._SPEC_LIT]
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_template_resolves_per_record(self, tmp_path, make_context,
                                          make_figure_records, leads_12,
                                          small_style):
        # svg keeps text as text (with fonttype 'none'), so the resolved
        # per-record annotation is observable in the output file
        meta, wave = make_figure_records(leads_12)
        meta[0][CMeta.UID] = 'rec1'
        meta[1][CMeta.UID] = 'rec2'
        spec = [{'text': 'ECG {' + CMeta.UID + '}', 'xy': (0.5, 0.99)}]
        ctx = make_context(tmp_path, e_median=False)
        with plt.rc_context({'svg.fonttype': 'none'}):
            FigureWriter(annotate=spec, image_format='svg',
                         kwargs_call={'style': small_style}).write(
                meta, wave, [], ctx)
        with open(tmp_path / 'a.svg') as fh:
            assert 'ECG rec1' in fh.read()
        with open(tmp_path / 'b.svg') as fh:
            assert 'ECG rec2' in fh.read()
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_template_needs_meta_guard(self, tmp_path, make_context,
                                       make_figure_records, leads_12,
                                       small_style):
        # a template without extracted metadata is a configuration
        # error: fail before any file is written
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_meta=False, e_median=False)
        spec = [{'text': '{' + CMeta.UID + '}', 'xy': (0.5, 0.5)}]
        with pytest.raises(InputValidationError):
            FigureWriter(annotate=spec,
                         kwargs_call={'style': small_style}).write(
                meta, wave, [], ctx)
        assert os.listdir(tmp_path) == []
        # literal annotations do not need metadata; without extracted
        # metadata the sampling rate must be supplied explicitly
        FigureWriter(annotate=self._SPEC_LIT,
                     kwargs_call={'style': small_style,
                                  'sampling_rate': 100.0}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'a.png', 'b.png'}
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_missing_key_raises_with_uid(self, tmp_path, make_context,
                                         make_figure_records, leads_12,
                                         small_style):
        meta, wave = make_figure_records(leads_12)
        ctx = make_context(tmp_path, e_median=False)
        spec = [{'text': '{absent}', 'xy': (0.5, 0.5)}]
        with pytest.raises(InputValidationError, match="record 'a'"):
            FigureWriter(annotate=spec,
                         kwargs_call={'style': small_style}).write(
                meta, wave, [], ctx)
        assert os.listdir(tmp_path) == []
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_skip_data_records_failure(self, tmp_path, make_context,
                                       make_figure_records, leads_12,
                                       small_style):
        # only record 'b' carries the referenced key; with skip_data the
        # failing record is skipped, recorded, and the batch continues
        open_before = plt.get_fignums()
        meta, wave = make_figure_records(leads_12)
        meta[1]['extra'] = 'X'
        spec = [{'text': '{extra}', 'xy': (0.5, 0.5)}]
        ctx = make_context(tmp_path, e_median=False, skip_data=True)
        FigureWriter(annotate=spec,
                     kwargs_call={'style': small_style}).write(
            meta, wave, [], ctx)
        assert set(os.listdir(tmp_path)) == {'b.png'}
        assert len(ctx.failed_records) == 1
        uid, cause = ctx.failed_records[0]
        assert uid == 'a'
        assert 'Annotation failed' in cause
        assert plt.get_fignums() == open_before
