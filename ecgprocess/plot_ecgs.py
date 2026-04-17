'''
Tools to plot ECG signals.

ECGDrawing takes a called reader instance (ECGXMLReader or ECGDICOMReader)
and renders the lead-specific ECG signals on a GridSpec figure with
clinical ECG paper scaling.
'''
from __future__ import annotations

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
import numpy as np
import matplotlib.pylab as plt
from dataclasses import dataclass, field
from typing import Any, Self
from ecgprocess.errors import NotCalledError, is_type
from ecgprocess.constants import PlotNames as PDNames, CoreData

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@dataclass
class ECGStyle:
    '''
    Pre-render style configuration for ECGDrawing.
    
    Attributes
    ----------
    figsize : `tuple` [`float`, `float`], default (20.0, 10.0)
        Figure width and height in inches.
    dpi : `int`, default 600
        Figure resolution in dots per inch.
    background_color : `str`, default '#ffd6d6'
        Axes background fill colour (ECG paper pink).
    major_grid_color : `str`, default '#ff6666'
        Colour of the major grid lines.
    minor_grid_color : `str`, default '#ffaaaa'
        Colour of the minor grid lines.
    trace_color : `str`, default 'black'
        ECG trace line colour.
    trace_linewidth : `float`, default 0.8
        ECG trace line width in points.
    paper_speed : `float`, default 25.0
        Paper speed in mm/s (standard clinical: 25 mm/s).
    mm_per_mv : `float`, default 10.0
        Voltage scaling in mm/mV (standard clinical: 10 mm/mV).
    n_cols : `int`, default 4
        Number of GridSpec columns used when building the figure.
    clip_on : `bool`, default False
        Whether to clip traces to their individual axes boundaries.
        False allows large deflections to cross into adjacent panels.
    x_lim : `tuple` [`float`, `float`] | `None`, default None
        X-axis limits in seconds. None auto-computes from n_samples / fs.
    y_lim : `tuple` [`float`, `float`], default (-2.0, 2.0)
        Y-axis limits in mV applied to every lead panel.
    
    Notes
    -----
    Paper speed and mm_per_mv drive the minor/major grid step sizes using the
    standard clinical ECG paper mapping:
    
    * x minor = 1 / paper_speed  (s)    e.g. 0.04 s at 25 mm/s
    * x major = 5 / paper_speed  (s)    e.g. 0.20 s at 25 mm/s
    * y minor = 1 / mm_per_mv    (mV)   e.g. 0.1 mV at 10 mm/mV
    * y major = 5 / mm_per_mv   (mV)   e.g. 0.5 mV at 10 mm/mV
    
    Settings not covered here can be applied after rendering via
    ``drawing.figure`` / ``drawing.axes`` (standard matplotlib), or passed
    as ``**kwargs`` to ``ECGDrawing.__call__`` which forwards them to
    ``plt.figure()``.
    '''
    # #### figure output
    # default_factory prevents the mutable tuple default being shared across
    # instances
    figsize: tuple[float, float] = field(default_factory=lambda: (20.0, 10.0))
    dpi: int = 600
    # #### colours
    background_color: str = '#ffd6d6'
    major_grid_color: str = '#ff6666'
    minor_grid_color: str = '#ffaaaa'
    # #### trace
    trace_color: str = 'black'
    trace_linewidth: float = 0.8
    # #### calibration
    # x-axis grid spacing is derived from paper_speed (mm/s)
    paper_speed: float = 25.0
    # y-axis grid spacing is derived from mm_per_mv (mm/mV)
    mm_per_mv: float = 10.0
    # #### layout
    n_cols: int = 4
    # False lets large deflections cross panel borders
    # (physical ECG paper look)
    clip_on: bool = False
    # #### axis limits
    # None triggers auto-computation from n_samples / fs at render time
    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] = field(default_factory=lambda: (-2.0, 2.0))

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGDrawing:
    '''
    Takes a called reader instance and plots lead-specific ECG signals.
    
    After calling, the instance exposes the rendered figure and per-lead axes
    so the caller can apply further matplotlib customisation directly.
    
    Attributes
    ----------
    figure : plt.Figure
        The matplotlib figure.
    axes : dict[str, plt.Axes]
        Dict mapping lead name to its Axes.
    layout_mapper : dict
        The resolved mapper dict used for this render.
    style : ECGStyle
        The ECGStyle instance used.
    minor_step_x : float
        Minor x-axis step in seconds (1 / paper_speed).
    major_step_x : float
        Major x-axis step in seconds (5 / paper_speed).
    minor_step_y : float
        Minor y-axis step in mV (1 / mm_per_mv).
    major_step_y : float
        Major y-axis step in mV (5 / mm_per_mv).
    paper_speed : float
        Resolved paper speed in mm/s.
    mm_per_mv : float
        Resolved voltage scaling in mm/mV.
    
    Methods
    -------
    to_numpy(crop, close)
        Renders the figure to a 3-D numpy array (RGBA).
    
    Notes
    -----
    Customisation operates at three levels:
    
    1. ECGStyle dataclass — ECG-specific pre-render settings.
    2. **kwargs on __call__ — forwarded to plt.figure().
    3. drawing.figure / drawing.axes — full matplotlib API post-render.
    '''
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(
        self,
        leads: list[str] | None = None,
    ) -> None:
        '''
        Initialises a new instance of ECGDrawing.
        
        Parameters
        ----------
        leads : list[str] | None, optional
            Lead names to plot by default. Uses the standard 12-lead list
            when None.
        '''
        pass
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self) -> str:
        return type(self).__name__
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self) -> str:
        return f'{type(self).__name__}()'
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(
        self,
        reader: Any,
        source: str = 'waveforms',
        leads: list[str] | None = None,
        mapper: dict | str | None = None,
        style: Any | None = None,
        show_axes: str | None = None,
        **kwargs: Any,
    ) -> Self:
        '''
        Creates an ECG figure from a called reader instance.
        
        Parameters
        ----------
        reader : Any
            A called ECGXMLReader or ECGDICOMReader instance.
        source : {'waveforms', 'median'}, default 'waveforms'
            Whether to plot WaveForms or MedianBeats signals.
        leads : list[str] | None, optional
            Lead names to plot. Overrides the constructor default.
        mapper : dict | str | None, optional
            Layout mapper dict or registry key (e.g. '12lead'). A mapper
            dict has the form ``{lead_name: (row_slice, col_slice)}``.
        style : ECGStyle | None, optional
            Style configuration dataclass. Uses defaults when None.
        show_axes : {'x', 'y', 'b', None}, optional
            Which axis labels and ticks to show. None hides all.
        **kwargs
            Forwarded to plt.figure().
        
        Returns
        -------
        self : ECGDrawing
            Returns the instance with populated figure, axes, and
            calibration attributes.
        '''
        raise NotImplementedError(
            "ECGDrawing.__call__ pending Stage 3–5 implementation."
        )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def to_numpy(
        self,
        crop: bool = False,
        close: bool = True,
    ) -> np.ndarray:
        '''
        Maps the matplotlib figure to a numpy array.
        
        Parameters
        ----------
        crop : bool, default False
            When True, expands the axes to cover the entire figure before
            conversion, effectively cropping to the plot area.
        close : bool, default True
            Whether to close the figure after extraction.
        
        Returns
        -------
        array : np.ndarray
            3-dimensional array of shape (height, width, 4) in RGBA format.
        
        Raises
        ------
        NotCalledError
            If __call__ has not been invoked yet.
        '''
        raise NotImplementedError(
            "ECGDrawing.to_numpy pending Stage 5 implementation."
        )

