'''
Tools to plot ECG signals.

ECGDrawing takes a called reader instance (ECGXMLReader or ECGDICOMReader)
and renders the lead-specific ECG signals on a GridSpec figure with
clinical ECG paper scaling.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# from __future__ import annotations
import logging
import numpy as np
import matplotlib.pylab as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator
from typing import Any, NamedTuple, Self
from ecgprocess.errors import InputValidationError, NotCalledError, is_type
from ecgprocess.constants import PlotNames as PDNames, CoreData
from ecgprocess.utils.general import _update_kwargs

# initiate the logger
_log = logging.getLogger(__name__)

# NOTE this may be better as a class attribute
_SOURCE_MAP: dict[str, str] = {
    'waveforms': CoreData.DataTypes.WaveForms,
    'median':    CoreData.DataTypes.MedianBeats,
}
_VALID_SHOW_AXES: frozenset[str | None] = frozenset({'x', 'y', 'b', None})
_VALID_CAL_PULSE_STYLES: frozenset[str] = frozenset({'square', 'line'})

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _minor_only_ticks(
    lo: float,
    hi: float,
    minor_step: float,
    major_step: float,
) -> np.ndarray:
    """
    Return minor tick positions that do not coincide with major ticks.
    
    Parameters
    ----------
    lo : `float`
        Lower axis limit.
    hi : `float`
        Upper axis limit.
    minor_step : `float`
        Minor tick spacing.
    major_step : `float`
        Major tick spacing.
    
    Returns
    -------
    ticks : `np.ndarray`
        Minor positions with major-coincident values removed.
    """
    tol = minor_step * 1e-6
    candidates = np.arange(
        np.ceil(lo / minor_step) * minor_step,
        hi + tol,
        minor_step,
    )
    remainder = candidates % major_step
    on_major = np.isclose(remainder, 0.0, atol=tol) | np.isclose(
        remainder, major_step, atol=tol,
    )
    return candidates[~on_major]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _resolve_lead_kwargs(
    kw_dict: dict | None,
    lead: str,
) -> dict:
    """
    Return the resolved kwargs dict for a single lead.
    
    Parameters
    ----------
    kw_dict : `dict` | `None`
        Either a flat dict (uniform across all leads), a dict of dicts
        (per-lead), or None.
    lead : `str`
        Lead name to resolve for.
    
    Returns
    -------
    resolved : `dict`
        Kwargs applicable to this lead. Empty dict when kw_dict is None or
        the lead is not listed in a per-lead mapping.
    
    Raises
    ------
    InputValidationError
        If kw_dict contains a mix of dict and non-dict values.
    """
    if not kw_dict:
        return {}
    vals = list(kw_dict.values())
    all_dicts = all(isinstance(v, dict) for v in vals)
    any_dicts = any(isinstance(v, dict) for v in vals)
    if all_dicts:
        return kw_dict.get(lead, {})
    if not any_dicts:
        return kw_dict
    raise InputValidationError(
        "Mixed dict/non-dict values in kwargs — pass either a flat dict "
        "(uniform) or a dict of dicts (per-lead)."
    )

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGStyle(NamedTuple):
    """
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
    major_grid_linewidth : `float`, default 0.3
        Line width of the major grid lines in points.
    minor_grid_linewidth : `float`, default 0.2
        Line width of the minor grid lines in points.
    trace_color : `str`, default 'black'
        ECG trace line colour.
    trace_linewidth : `float`, default 0.5
        ECG trace line width in points.
    paper_speed : `float`, default 25.0
        Paper speed in mm/s (standard clinical: 25 mm/s).
    mm_per_mv : `float`, default 10.0
        Voltage scaling in mm/mV (standard clinical: 10 mm/mV).
    clip_on_patch : `bool`, default False
        Whether the axes patch clips its contents to the axes boundary.
        False lets large deflections cross into adjacent panels.
    clip_on_trace : `bool`, default False
        Whether each ECG trace line is clipped to its axes boundary.
        False replicates the physical ECG paper look.
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
    """
    # #### figure output
    figsize: tuple[float, float] = (20.0, 10.0)
    dpi: int = 600
    # #### colours
    background_color: str = '#ffd6d6'
    major_grid_color: str = '#ff6666'
    minor_grid_color: str = '#ffaaaa'
    # #### grid line widths
    major_grid_linewidth: float = 0.3
    minor_grid_linewidth: float = 0.2
    # #### trace
    trace_color: str = 'black'
    trace_linewidth: float = 0.5
    # #### calibration
    # x-axis grid spacing is derived from paper_speed (mm/s)
    paper_speed: float = 25.0
    # y-axis grid spacing is derived from mm_per_mv (mm/mV)
    mm_per_mv: float = 10.0
    # #### layout
    clip_on_patch: bool = False
    clip_on_trace: bool = False
    # Zero spacing mimics continuous ECG paper; increase to separate panels
    hspace: float = 0.0
    wspace: float = 0.0
    # #### axis limits
    # None triggers auto-computation from n_samples / fs at render time
    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] = (-2.0, 2.0)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGDrawing:
    """
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
    """
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
        sampling_rate: float | None = None,
        show_lead_labels: bool = False,
        show_cal_pulse: bool = False,
        cal_pulse_style: str = 'square',
        kwargs_fig: dict | None = None,
        kwargs_gridspec: dict | None = None,
        kwargs_plot: dict | dict[str, dict] | None = None,
        kwargs_grid: dict | dict[str, dict] | None = None,
        kwargs_ticks: dict | dict[str, dict] | None = None,
        kwargs_background: dict | dict[str, dict] | None = None,
        kwargs_label: dict | dict[str, dict] | None = None,
        kwargs_cal_pulse: dict | dict[str, dict] | None = None,
    ) -> Self:
        """
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
        sampling_rate : `float` | `None`, optional
            Sampling frequency in Hz. When None, read from
            ``reader.MetaData[CoreData.MetaData.SF]``. Raises
            `InputValidationError` if neither source is available.
        show_lead_labels : `bool`, default False
            When True, each panel is annotated with its lead name in the
            top-left corner using the default label style.
        show_cal_pulse : `bool`, default False
            When True, prepends a standard 1 mV calibration pulse to each
            lead signal before rendering. The caller's data is not mutated.
        cal_pulse_style : {'square', 'line'}, default 'square'
            Shape of the calibration pulse. ``'square'`` draws the full
            rectangular pulse (0.1 s baseline → 0.2 s at 1 mV → 0.1 s
            baseline). ``'line'`` draws only a single vertical spike
            (0.1 s baseline → 3-sample rise/peak/fall → 0.1 s baseline),
            matching the convention used by some thermal-paper ECG machines.
        kwargs_fig : `dict` | `None`, optional
            Extra keyword arguments forwarded to ``plt.figure()``. Style
            fields (``figsize``, ``dpi``) are used as defaults and are
            overridden by any matching keys here.
        kwargs_gridspec : `dict` | `None`, optional
            Extra keyword arguments forwarded to ``GridSpec()``. Style
            fields (``hspace``, ``wspace``) are used as defaults and are
            overridden by any matching keys here.
        kwargs_plot : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.plot()``. Pass a flat
            dict to apply uniformly, or a dict of dicts for per-lead control.
        kwargs_grid : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.grid()``. Same
            uniform/per-lead convention as ``kwargs_plot``.
        kwargs_ticks : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.tick_params()``. Same
            uniform/per-lead convention as ``kwargs_plot``.
        kwargs_background : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.patch.set()``. Same
            uniform/per-lead convention as ``kwargs_plot``.
        kwargs_label : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.text()`` for lead
            labels. Only used when ``show_lead_labels=True``. Same
            uniform/per-lead convention as ``kwargs_plot``. Caller-supplied
            values override the defaults (fontsize=7, fontweight='bold',
            va='top', ha='left').
        kwargs_cal_pulse : `dict` | `dict` [`str`, `dict`] | `None`, optional
            Extra keyword arguments forwarded to ``ax.plot()`` for the
            calibration pulse trace. Only used when ``show_cal_pulse=True``.
            Same uniform/per-lead convention as ``kwargs_plot``.
        
        Returns
        -------
        self : ECGDrawing
            Returns the instance with populated figure, axes, and
            calibration attributes.
        """
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
        # #### validate show_axes
        if isinstance(show_axes, str):
            if show_axes not in _VALID_SHOW_AXES:
                raise InputValidationError(
                    f"show_axes must be 'x', 'y', 'b', or None, "
                    f"got {show_axes!r}."
                )
        elif isinstance(show_axes, dict):
            invalid = {v for v in show_axes.values() if v not in _VALID_SHOW_AXES}
            if invalid:
                raise InputValidationError(
                    f"show_axes dict contains invalid values: {invalid!r}."
                )
        elif show_axes is not None:
            raise InputValidationError(
                f"show_axes must be str, dict, or None, "
                f"got {type(show_axes).__name__!r}."
            )
        # #### validate cal_pulse_style
        if cal_pulse_style not in _VALID_CAL_PULSE_STYLES:
            raise InputValidationError(
                f"cal_pulse_style must be 'square' or 'line', "
                f"got {cal_pulse_style!r}."
            )
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
        # #### resolve sampling rate
        if sampling_rate is None:
            meta = getattr(reader, CoreData.DataTypes.MetaData, None) or {}
            sampling_rate = meta.get(CoreData.MetaData.SF)
        if sampling_rate is None:
            raise InputValidationError(
                "Sampling rate unavailable: pass sampling_rate= or ensure "
                f"MetaData[{CoreData.MetaData.SF!r}] is set."
            )
        # #### render leads
        self._render_leads(
            axes=axes,
            signals=signals,
            style=style,
            sampling_rate=float(sampling_rate),
            show_axes=show_axes,
            show_lead_labels=show_lead_labels,
            show_cal_pulse=show_cal_pulse,
            cal_pulse_style=cal_pulse_style,
            kwargs_plot=kwargs_plot,
            kwargs_grid=kwargs_grid,
            kwargs_ticks=kwargs_ticks,
            kwargs_background=kwargs_background,
            kwargs_label=kwargs_label,
            kwargs_cal_pulse=kwargs_cal_pulse,
        )
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
        """
        Build the GridSpec figure and per-lead axes from a mapper dict.
        
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
            ax.patch.set_clip_on(style.clip_on_patch)
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
    def _render_leads(
        self,
        axes: dict[str, plt.Axes],
        signals: dict,
        style: ECGStyle,
        sampling_rate: float,
        show_axes: dict[str, str | None] | str | None,
        show_lead_labels: bool,
        show_cal_pulse: bool,
        cal_pulse_style: str,
        kwargs_plot: dict | dict[str, dict] | None,
        kwargs_grid: dict | dict[str, dict] | None,
        kwargs_ticks: dict | dict[str, dict] | None,
        kwargs_background: dict | dict[str, dict] | None,
        kwargs_label: dict | dict[str, dict] | None,
        kwargs_cal_pulse: dict | dict[str, dict] | None,
    ) -> None:
        """
        Render each lead: trace, limits, background, grid, and tick visibility.
        
        Parameters
        ----------
        axes : `dict` [`str`, `plt.Axes`]
            Per-lead axes created by ``_build_figure``.
        signals : `dict`
            Signal data extracted from the reader.
        style : `ECGStyle`
            Style configuration.
        sampling_rate : `float`
            Sampling frequency in Hz used to build the time axis.
        show_axes : `dict` [`str`, `str` | `None`] | `str` | `None`
            Tick visibility spec; validated before this method is called.
        show_lead_labels : `bool`
            When True, annotate each panel with its lead name.
        show_cal_pulse : `bool`
            When True, prepend a calibration pulse.
        cal_pulse_style : `str`
            ``'square'`` or ``'line'``; validated before this method is called.
        kwargs_plot : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for ``ax.plot()``.
        kwargs_grid : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for ``ax.grid()``.
        kwargs_ticks : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for ``ax.tick_params()``.
        kwargs_background : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for ``ax.patch.set()``.
        kwargs_label : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for ``ax.text()`` lead annotations.
        kwargs_cal_pulse : `dict` | `dict` [`str`, `dict`] | `None`
            Extra kwargs for the calibration pulse ``ax.plot()`` call.
        """
        minor_x = getattr(self, PDNames.MINOR_STEP_X)
        major_x = getattr(self, PDNames.MAJOR_STEP_X)
        minor_y = getattr(self, PDNames.MINOR_STEP_Y)
        major_y = getattr(self, PDNames.MAJOR_STEP_Y)
        for lead, ax in axes.items():
            if lead not in signals:
                # blank axes already created and warned in _build_figure
                continue
            signal = signals[lead]
            # #### prepend calibration pulse (copy — caller data unchanged)
            if show_cal_pulse:
                n_pre  = round(0.1 * sampling_rate)
                n_post = round(0.1 * sampling_rate)
                if cal_pulse_style == 'square':
                    body = np.ones(round(0.2 * sampling_rate))
                else:
                    body = np.array([0.0, 1.0, 0.0])
                pulse = np.concatenate(
                    [np.zeros(n_pre), body, np.zeros(n_post)])
                signal = np.concatenate([pulse, signal])
            t = np.arange(len(signal)) / sampling_rate
            # #### resolve per-lead kwargs
            p_kw   = _resolve_lead_kwargs(kwargs_plot,       lead)
            g_kw   = _resolve_lead_kwargs(kwargs_grid,       lead)
            t_kw   = _resolve_lead_kwargs(kwargs_ticks,      lead)
            bg_kw  = _resolve_lead_kwargs(kwargs_background, lead)
            cp_kw  = _resolve_lead_kwargs(kwargs_cal_pulse,  lead)
            # #### trace
            ax.plot(
                t, signal,
                color=style.trace_color,
                lw=style.trace_linewidth,
                clip_on=style.clip_on_trace,
                zorder=3,
                **p_kw,
            )
            # #### axis limits
            ax.set_xlim(style.x_lim or (0.0, len(signal) / sampling_rate))
            ax.set_ylim(style.y_lim)
            # #### background
            ax.patch.set_facecolor(style.background_color)
            ax.patch.set_visible(True)
            if bg_kw:
                ax.patch.set(**bg_kw)
            # #### grid lines — minor first (behind), major second (in front)
            # ax.grid() does not reliably honour zorder across x/y axes;
            # vlines/hlines produce LineCollections that do.
            ax.xaxis.set_major_locator(MultipleLocator(major_x))
            ax.yaxis.set_major_locator(MultipleLocator(major_y))
            x_lo, x_hi = ax.get_xlim()
            y_lo, y_hi = ax.get_ylim()
            minor_xs = _minor_only_ticks(x_lo, x_hi, minor_x, major_x)
            minor_ys = _minor_only_ticks(y_lo, y_hi, minor_y, major_y)
            major_xs = np.arange(
                np.ceil(x_lo / major_x) * major_x,
                x_hi + major_x * 1e-6,
                major_x,
            )
            major_ys = np.arange(
                np.ceil(y_lo / major_y) * major_y,
                y_hi + major_y * 1e-6,
                major_y,
            )
            minor_kw = _update_kwargs(
                g_kw,
                color=style.minor_grid_color,
                linewidth=style.minor_grid_linewidth,
                zorder=1,
            )
            major_kw = _update_kwargs(
                g_kw,
                color=style.major_grid_color,
                linewidth=style.major_grid_linewidth,
                zorder=2,
            )
            ax.vlines(minor_xs, y_lo, y_hi, **minor_kw)
            ax.hlines(minor_ys, x_lo, x_hi, **minor_kw)
            ax.vlines(major_xs, y_lo, y_hi, **major_kw)
            ax.hlines(major_ys, x_lo, x_hi, **major_kw)
            # #### tick visibility
            lead_show = (
                show_axes.get(lead) if isinstance(show_axes, dict)
                else show_axes
            )
            ax.tick_params(
                axis='both', which='both',
                bottom=False, left=False,
                labelbottom=False, labelleft=False,
                **t_kw,
            )
            if lead_show in ('x', 'b'):
                ax.tick_params(axis='x', bottom=True, labelbottom=True)
            if lead_show in ('y', 'b'):
                ax.tick_params(axis='y', left=True, labelleft=True)
            # #### lead label
            if show_lead_labels:
                lbl_kw = _update_kwargs(
                    _resolve_lead_kwargs(kwargs_label, lead),
                    fontsize=7, fontweight='bold',
                    va='top', ha='left',
                    color=style.trace_color,
                    clip_on=False,
                )
                ax.text(0.02, 0.95, lead, transform=ax.transAxes, **lbl_kw)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def to_numpy(
        self,
        crop: bool = False,
        close: bool = True,
    ) -> np.ndarray:
        """
        Maps the matplotlib figure to a numpy array.
        
        Parameters
        ----------
        crop : `bool`, default False
            When True, applies tight layout before conversion, removing
            excess whitespace around the plot area.
        close : `bool`, default True
            Whether to close the figure after extraction.
        
        Returns
        -------
        array : np.ndarray
            3-dimensional array of shape (height, width, 4) in RGBA format.
        
        Raises
        ------
        NotCalledError
            If __call__ has not been invoked yet.
        """
        fig = getattr(self, PDNames.FIGURE)
        if fig is None:
            raise NotCalledError(
                "ECGDrawing must be called before to_numpy()."
            )
        if crop:
            fig.tight_layout(pad=0)
        fig.canvas.draw()
        arr = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).copy()
        h, w = fig.canvas.get_width_height()[::-1]
        arr = arr.reshape(h, w, 4)
        if close:
            plt.close(fig)
            setattr(self, PDNames.FIGURE, None)
            setattr(self, PDNames.AXES,   None)
        return arr

