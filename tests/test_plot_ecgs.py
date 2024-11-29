import pytest
from ecgprocess.constants import ProcessDicomNames as PDNames
from ecgprocess.errors import NotCalledError
from ecgprocess.process_dicoms import (
    ECGDICOMReader,
)
from ecgprocess.plot_ecgs import (
    ECGDrawing,
)
from ecgprocess.example_data.examples import (
    list_dicom_paths as list_data_paths,
)
import matplotlib.lines as mlines
import matplotlib.text as mtext
import matplotlib.pylab as plt

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Relevant paths
dicom_file_path = list_data_paths()['example_dicom_1']

# constants
NUMTICKS = 'numticks'
MEDIAN='median'
LAYOUT=[
    ['II', 'aVL', 'V3'],
]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def ecgdicomreader_fixture():
    '''
    Returns a called ecgdicomreader instance.
    
    Returns
    -------
    callable
        A function that takes parameters path, skip_empty, and verbose to
        return an ECGDICOMReader instance initialized with those parameters.
    '''
    def _create_ecgdicomreader(path, skip_empty=True, verbose=False):
        ecgdicomreader = ECGDICOMReader()
        return ecgdicomreader(path=path, skip_empty=skip_empty, verbose=verbose)
    return _create_ecgdicomreader

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ECGDrawing
class TestECGDrawing(object):
    """
    Testing ECGDrawing
    """
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_default(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader)
        ax = getattr(artist, PDNames.PLOT_AXES)
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
        # check the gridlines were not updated by confirming the locator does
        # not have numticks
        assert not hasattr(ax.xaxis.get_minor_locator(), NUMTICKS)
        assert not hasattr(ax.xaxis.get_major_locator(), NUMTICKS)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_add_grid(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader, add_grid=True)
        ax = getattr(artist, PDNames.PLOT_AXES)
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
        # check the gridlines were updated by confirming the locator does
        # have numticks
        assert hasattr(ax.xaxis.get_minor_locator(), NUMTICKS)
        assert hasattr(ax.xaxis.get_major_locator(), NUMTICKS)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_minor_axis(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader, add_grid=True, minor_axis=False)
        ax = getattr(artist, PDNames.PLOT_AXES)
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
        # no minor axis, but with major axis.
        assert not hasattr(ax.xaxis.get_minor_locator(), NUMTICKS)
        assert hasattr(ax.xaxis.get_major_locator(), NUMTICKS)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wave_type(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader, wave_type=MEDIAN)
        ax = getattr(artist, PDNames.PLOT_AXES)
        # check the wave type
        assert getattr(artist, PDNames.WAVE_TYPE) == MEDIAN
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_layout(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader, image_layout=LAYOUT)
        ax = getattr(artist, PDNames.PLOT_AXES)
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
        # check the leads are printed
        text = [c for c in ax.get_children() if isinstance(c, mtext.Text)]
        text = [t.get_text() for t in text if t.get_text().strip() != '']
        # using [0], if needed can flatten the list
        assert all(t in LAYOUT[0] for t in text) == True
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ax(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        _, axes = plt.subplots(figsize=(2,2))
        artist = ECGDrawing()(ecgreader, ax=axes)
        ax = getattr(artist, PDNames.PLOT_AXES)
        fig = getattr(artist, PDNames.PLOT_FIG)
        # check there are lines and text children
        assert any(isinstance(child, mlines.Line2D) for
                   child in ax.get_children())
        assert any(isinstance(child, mtext.Text) for child in ax.get_children())
        # check figure dim
        assert list(fig.get_size_inches() ) == [2.0, 2.0]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_to_numpy(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        artist = ECGDrawing()(ecgreader)
        arr = artist.to_numpy()
        # need to get a new figure, numpy closes the fig
        artist = ECGDrawing()(ecgreader)
        arr2 = artist.to_numpy(crop=True)
        assert len(arr.shape) == 3
        assert len(arr2.shape) == 3
        assert arr.shape[0:2] > arr2.shape[0:2]
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_wave_type(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        with pytest.raises(ValueError):
            _ = ECGDrawing()(ecgreader, wave_type='wrong')
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_wrong_layout(self, ecgdicomreader_fixture):
        ecgreader=ecgdicomreader_fixture(path=dicom_file_path)
        with pytest.raises(KeyError):
            _ = ECGDrawing()(ecgreader, image_layout=['wrong'])
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_notcallederror(self, ecgdicomreader_fixture):
        # not calling the instance
        ecgreader=ecgdicomreader_fixture
        with pytest.raises(NotCalledError):
            _ = ECGDrawing()(ecgreader)
        # without calling _set_canvas
        with pytest.raises(NotCalledError):
            _ = ECGDrawing()._draw_signal(LAYOUT)
        # without calling _draw_signal
        with pytest.raises(NotCalledError):
            _ = ECGDrawing().to_numpy()

