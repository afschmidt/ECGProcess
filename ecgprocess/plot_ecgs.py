'''
Tools to plot ECG signals.

ECGDrawing takes a called reader instance (ECGXMLReader or ECGDICOMReader)
and renders the lead-specific ECG signals on a GridSpec figure with
clinical ECG paper scaling.
'''
from __future__ import annotations

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
import logging
import numpy as np
import matplotlib.pylab as plt
from matplotlib.gridspec import GridSpec
from typing import Any, NamedTuple, Self
from ecgprocess.errors import InputValidationError, NotCalledError, is_type
from ecgprocess.constants import PlotNames as PDNames, CoreData
from ecgprocess.utils.general import _update_kwargs

_log = logging.getLogger(__name__)

# NOTE this may be better as a class attribute
_SOURCE_MAP: dict[str, str] = {
    'waveforms': CoreData.DataTypes.WaveForms,
    'median':    CoreData.DataTypes.MedianBeats,
}


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGStyle(NamedTuple):
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
    clip_on : `bool`, default False
        Whether to clip traces to their individual axes boundaries.
        False allows large deflections to cross into adjacent panels.
    hspace : `float`, default 0.0
        Vertical spacing between GridSpec rows. Zero mimics continuous ECG
        paper; increase to visually separate panels.
    wspace : `float`, default 0.0
        Horizontal spacing between GridSpec columns. Zero mimics continuous
        ECG paper; increase to visually separate panels.
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
    figsize: tuple[float, float] = (20.0, 10.0)
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
    # False lets large deflections cross panel borders
    # (physical ECG paper look)
    clip_on: bool = False
    # Zero spacing mimics continuous ECG paper; increase to separate panels
    hspace: float = 0.0
    wspace: float = 0.0
    # #### axis limits
    # None triggers auto-computation from n_samples / fs at render time
    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] = (-2.0, 2.0)

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
    
    1. ECGStyle — ECG-specific pre-render settings.
    2. **kwargs on __call__ — forwarded to plt.figure().
    3. drawing.figure / drawing.axes — full matplotlib API post-render.
    '''
    # /////////////////////////////////////////////////////////////////////////
    # __slots__ mirrors BaseReader convention: eliminates per-instance __dict__,
    # reducing memory overhead and making the public attribute surface explicit.
    __slots__ = (
        PDNames.DEFAULT_LEADS,
        PDNames.FIGURE, PDNames.AXES, PDNames.LAYOUT_MAPPER, PDNames.STYLE,
        PDNames.MINOR_STEP_X, PDNames.MAJOR_STEP_X,
        PDNames.MINOR_STEP_Y, PDNames.MAJOR_STEP_Y,
        PDNames.PAPER_SPEED, PDNames.MM_PER_MV,
    )
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
        cl = CoreData.Leads
        setattr(self, PDNames.DEFAULT_LEADS, leads or [
            cl.I, cl.II, cl.III,
            cl.aVR, cl.aVL, cl.aVF,
            cl.V1, cl.V2, cl.V3, cl.V4, cl.V5, cl.V6,
        ])
        setattr(self, PDNames.FIGURE,        None)
        setattr(self, PDNames.AXES,          None)
        setattr(self, PDNames.LAYOUT_MAPPER, None)
        setattr(self, PDNames.STYLE,         None)
        setattr(self, PDNames.MINOR_STEP_X,  None)
        setattr(self, PDNames.MAJOR_STEP_X,  None)
        setattr(self, PDNames.MINOR_STEP_Y,  None)
        setattr(self, PDNames.MAJOR_STEP_Y,  None)
        setattr(self, PDNames.PAPER_SPEED,   None)
        setattr(self, PDNames.MM_PER_MV,     None)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __str__(self) -> str:
        """Return human-readable string representation."""
        CLASS_NAME = type(self).__name__
        leads = getattr(self, PDNames.DEFAULT_LEADS)
        return f"{CLASS_NAME} instance with leads={leads}."
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self) -> str:
        """Return unambiguous string representation."""
        CLASS_NAME = type(self).__name__
        leads = getattr(self, PDNames.DEFAULT_LEADS)
        return f"{CLASS_NAME}(leads={leads!r})"
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(
        self,
        reader: Any,
        mapper: dict | None = None,
        source: str = 'waveforms',
        style: ECGStyle | None = None,
        show_axes: dict[str, str | None] | str | None = None,
        kwargs_fig: dict | None = None,
        kwargs_gridspec: dict | None = None,
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
        mapper : `dict` | `None`
            Layout dict mapping lead names to ``(row_index, col_slice)``.
            Required — raises `InputValidationError` if None. Dict insertion
            order determines plotting order; grid dimensions are derived from
            the mapper values. Mismatch warnings (missing or unrequested leads)
            are emitted at WARNING level via the ``ecgprocess.plot_ecgs`` logger.
        source : {'waveforms', 'median'}, default 'waveforms'
            Whether to plot WaveForms or MedianBeats signals.
        style : `ECGStyle` | `None`, optional
            Style configuration. Uses defaults when None.
        show_axes : `dict` [`str`, `str` | `None`] | `str` | `None`, optional
            Which axis ticks and labels to show per lead. A string value
            applies uniformly: ``'x'`` x-axis only, ``'y'`` y-axis only,
            ``'b'`` both, ``None`` hides all. A dict maps individual lead
            names to these same string values, leaving unlisted leads hidden.
        kwargs_fig : `dict` | `None`, optional
            Extra keyword arguments forwarded to ``plt.figure()``. Style
            fields (``figsize``, ``dpi``) are used as defaults and are
            overridden by any matching keys here.
        kwargs_gridspec : `dict` | `None`, optional
            Extra keyword arguments forwarded to ``GridSpec()``. Style
            fields (``hspace``, ``wspace``) are used as defaults and are
            overridden by any matching keys here.
        
        Returns
        -------
        self : ECGDrawing
            Returns the instance with populated figure, axes, and
            calibration attributes.
        '''
        # #### resolve style
        style = style or ECGStyle()
        # #### validate source and extract signals
        if source not in _SOURCE_MAP:
            raise InputValidationError(
                f"source must be 'waveforms' or 'median', got {source!r}."
            )
        signals = getattr(reader, _SOURCE_MAP[source], None)
        if signals is None or len(signals) == 0:
            raise InputValidationError(
                f"Reader has no data for source={source!r}."
            )
        # #### check for NaN in every lead
        for lead, arr in signals.items():
            if np.any(np.isnan(arr)):
                raise InputValidationError(
                    f"Signal for lead {lead!r} contains NaN values."
                )
        # #### store style and calibration attributes
        setattr(self, PDNames.STYLE,        style)
        setattr(self, PDNames.PAPER_SPEED,  style.paper_speed)
        setattr(self, PDNames.MM_PER_MV,    style.mm_per_mv)
        # grid steps: mm / (mm/s) = s  and  mm / (mm/mV) = mV
        setattr(self, PDNames.MINOR_STEP_X,
                PDNames.MINOR_GRID_MM / style.paper_speed)
        setattr(self, PDNames.MAJOR_STEP_X,
                PDNames.MAJOR_GRID_MM / style.paper_speed)
        setattr(self, PDNames.MINOR_STEP_Y,
                PDNames.MINOR_GRID_MM / style.mm_per_mv)
        setattr(self, PDNames.MAJOR_STEP_Y,
                PDNames.MAJOR_GRID_MM / style.mm_per_mv)
        # #### validate mapper and build figure
        if mapper is None:
            raise InputValidationError(
                "mapper is required — pass a dict mapping lead names to "
                "(row_index, col_slice)."
            )
        fig, axes = self._build_figure(
            signals, mapper, style,
            kwargs_fig=kwargs_fig,
            kwargs_gridspec=kwargs_gridspec,
        )
        setattr(self, PDNames.FIGURE,        fig)
        setattr(self, PDNames.AXES,          axes)
        setattr(self, PDNames.LAYOUT_MAPPER, mapper)
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _build_figure(
        self,
        signals: dict,
        mapper: dict,
        style: ECGStyle,
        kwargs_fig: dict | None = None,
        kwargs_gridspec: dict | None = None,
    ) -> tuple[plt.Figure, dict[str, plt.Axes]]:
        """Build the GridSpec figure and per-lead axes from a mapper dict.
        
        Parameters
        ----------
        signals : `dict`
            Signal data extracted from the reader.
        mapper : `dict`
            Lead name to ``(row_index, col_slice)`` mapping. Dict insertion
            order determines plotting order. Both n_rows and n_cols are
            derived from the mapper — no assumptions about grid size are made.
        style : `ECGStyle`
            Style configuration.
        kwargs_fig : `dict` | `None`, optional
            Extra keyword arguments for ``plt.figure()``. None is treated
            as an empty dict.
        kwargs_gridspec : `dict` | `None`, optional
            Extra keyword arguments for ``GridSpec()``. None is treated
            as an empty dict.
        
        Returns
        -------
        figure : `plt.Figure`
            The created figure.
        axes : `dict` [`str`, `plt.Axes`]
            Mapping of lead name to axes.
        """
        # #### derive grid dimensions from mapper — no hardcoded assumptions
        n_rows = max(row for row, _ in mapper.values()) + 1
        n_cols = max(col.stop for _, col in mapper.values())
        # #### style values are defaults — caller dicts take precedence
        kwargs_fig = kwargs_fig or {}
        kwargs_gridspec = kwargs_gridspec or {}
        fig_kwargs = _update_kwargs(
            update_dict=kwargs_fig,
            figsize=style.figsize, dpi=style.dpi,
        )
        gs_kwargs = _update_kwargs(
            update_dict=kwargs_gridspec,
            hspace=style.hspace, wspace=style.wspace,
        )
        fig = plt.figure(**fig_kwargs)
        gs = GridSpec(n_rows, n_cols, figure=fig, **gs_kwargs)
        # #### create one axes per mapper entry in insertion order
        axes: dict[str, plt.Axes] = {}
        for lead, (row, col) in mapper.items():
            if lead not in signals:
                _log.warning(
                    "Lead %r not found in signal data — axes left blank.", lead
                )
            ax = fig.add_subplot(gs[row, col])
            # clip_on=False allows traces to overplot into adjacent panels
            if not style.clip_on:
                ax.patch.set_visible(False)
            axes[lead] = ax
        # #### warn about signal data keys the mapper did not request
        for lead in signals:
            if lead not in mapper:
                _log.warning(
                    "Lead %r is in signal data but not requested in "
                    "mapper.", lead,
                )
        return fig, axes
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

