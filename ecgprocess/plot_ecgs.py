'''
Tools to plot ECG signals.

ECGDrawing takes a called reader instance (ECGXMLReader or ECGDICOMReader)
and renders the lead-specific ECG signals on a GridSpec figure with
clinical ECG paper scaling.
'''

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# from __future__ import annotations
import logging
import string
import numpy as np
import matplotlib.pylab as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator
from typing import Any, NamedTuple, Self, Literal
from ecgprocess.errors import (
    InputValidationError, NotCalledError, is_type, Error_MSG,
)
from ecgprocess.constants import PlotNames as PDNames, CoreData
from ecgprocess.utils.general import _update_kwargs

# initiate the logger
_log = logging.getLogger(__name__)

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
    # Small epsilon to keep np.arange inclusive at hi and to absorb
    # floating-point noise when testing whether a tick falls on a major line.
    tol = minor_step * 1e-6
    # get minor tick locations
    tick_loc = np.arange(
        np.ceil(lo / minor_step) * minor_step,
        hi + tol,
        minor_step,
    )
    remainder = tick_loc % major_step
    # which tick to remove
    on_major = np.isclose(remainder, 0.0, atol=tol) | np.isclose(
        remainder, major_step, atol=tol,
    )
    # return
    return tick_loc[~on_major]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _resolve_lead_kwargs(
    kw_dict: dict[str, Any] | None,
    lead: str,
) -> dict[str, Any]:
    """
    Return the resolved kwargs dict for a single lead.
    
    Parameters
    ----------
    kw_dict : `dict[str, Any]` | `None`
        Either a flat dict (uniform across all leads), a dict of dicts
        (per-lead), or None.
    lead : `str`
        Lead name to resolve for.
    
    Returns
    -------
    resolved : `dict[str, Any]`
        Kwargs applicable to this lead. Empty dict when kw_dict is None or
        the lead is not listed in a per-lead mapping.
    
    Raises
    ------
    InputValidationError
        If kw_dict contains a mix of dict and non-dict values.
    
    Examples
    --------
    Uniform, same kwargs applied to every lead:
    
    >>> _resolve_lead_kwargs({'color': 'red', 'linewidth': 1.5}, 'I')
    {'color': 'red', 'linewidth': 1.5}
    
    Per-lead, different kwargs per lead:
    
    >>> _resolve_lead_kwargs({
            'I': {'color': 'red'},
            'II': {'color': 'blue'}
            }, lead = 'I')
    {'color': 'red'}
    """
    # return empty dict if None
    if not kw_dict:
        return {}
    vals = list(kw_dict.values())
    all_dicts = all(isinstance(v, dict) for v in vals)
    any_dicts = any(isinstance(v, dict) for v in vals)
    if all_dicts:
        # return the lead specific dict
        return kw_dict.get(lead, {})
    if not any_dicts:
        # if there are no dicts, that means the original dict should be
        # applied to each lead
        return kw_dict
    # if mixed dicts raise an error
    raise InputValidationError(
        "Mixed dict/non-dict values in kwargs, either pass a flat dict "
        "(uniform) or a dict of dicts (per-lead)."
    )

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _annotation_fields(text: str) -> list[str]:
    """
    Return the replacement-field names in an annotation template.

    Parameters
    ----------
    text : `str`
        An annotation template, e.g. ``'ECG {unique identifier}'``.

    Returns
    -------
    fields : `list` [`str`]
        The field names referenced by the template, in order of
        appearance; empty for a literal string.

    Raises
    ------
    ValueError
        If the template contains malformed replacement fields (e.g. a
        single unmatched ``'{'``).
    """
    return [
        field for _, field, _, _ in string.Formatter().parse(text)
        if field is not None
    ]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _split_annotation_spec(
    spec: dict[str, Any],
) -> tuple[str, tuple[float, float], dict[str, Any]]:
    """
    Validate an annotation spec dict and split it into its parts.

    Parameters
    ----------
    spec : `dict` [`str`, `any`]
        One annotation spec with the required keys ``'text'`` (`str`)
        and ``'xy'`` (a 2-item tuple/list of numbers); all remaining
        keys are treated as `matplotlib.figure.Figure.text` kwargs.

    Returns
    -------
    text : `str`
        The annotation template string.
    xy : `tuple` [`float`, `float`]
        The figure-fraction position.
    extras : `dict` [`str`, `any`]
        The remaining fig.text keyword arguments.

    Raises
    ------
    InputValidationError
        If required keys are absent or of the wrong type.
    """
    is_type(spec, dict)
    if PDNames.ANNOT_TEXT not in spec or PDNames.ANNOT_XY not in spec:
        raise InputValidationError(Error_MSG.ANNOTATE_SPEC.format(spec))
    text = spec[PDNames.ANNOT_TEXT]
    xy = spec[PDNames.ANNOT_XY]
    if not isinstance(text, str) or not (
            isinstance(xy, (tuple, list)) and len(xy) == 2
            and all(isinstance(v, (int, float)) for v in xy)):
        raise InputValidationError(Error_MSG.ANNOTATE_SPEC.format(spec))
    extras = {k: v for k, v in spec.items()
              if k not in (PDNames.ANNOT_TEXT, PDNames.ANNOT_XY)}
    return text, (float(xy[0]), float(xy[1])), extras

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _resolve_annotation(text: str, meta: Any) -> str:
    """
    Resolve ``'{key}'`` placeholders in a template from metadata.

    Parameters
    ----------
    text : `str`
        The annotation template. Literal strings (no placeholders) pass
        through unchanged apart from ``'{{'``/``'}}'`` brace unescaping.
    meta : mapping or `None`
        The metadata mapping (supports ``.get``) the field names are
        resolved against.

    Returns
    -------
    resolved : `str`
        The template with every placeholder substituted.

    Raises
    ------
    InputValidationError
        If a referenced metadata key is missing or None.
    """
    fields = _annotation_fields(text)
    if not fields:
        # unescape any literal '{{' / '}}' braces
        return text.format_map({})
    values = {}
    for field in fields:
        value = meta.get(field) if meta is not None else None
        if value is None:
            raise InputValidationError(
                Error_MSG.ANNOTATE_MISSING_KEY.format(text, field))
        values[field] = value
    return text.format_map(values)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGStyle(NamedTuple):
    """
    Style configuration for ECGDrawing.
    
    Attributes
    ----------
    figsize : `tuple` [`float`, `float`], default (20.0, 10.0)
        Figure width and height in inches.
    dpi : `int`, default 600
        Figure resolution in dots per inch.
    background_colour : `str`, default '#ffd6d6'
        Axes background fill colour (ECG paper pink).
    major_grid_colour : `str`, default '#ff6666'
        Colour of the major grid lines.
    minor_grid_colour : `str`, default '#ffaaaa'
        Colour of the minor grid lines.
    major_grid_linewidth : `float`, default 0.3
        Line width of the major grid lines in points.
    minor_grid_linewidth : `float`, default 0.2
        Line width of the minor grid lines in points.
    trace_colour : `str`, default 'black'
        ECG trace line colour.
    trace_linewidth : `float`, default 0.4
        ECG trace line width in points.
    paper_speed : `float`, default 25.0
        Paper speed in mm/s (standard clinical: 25 mm/s).
    mm_per_mv : `float`, default 10.0
        Voltage scaling in mm/mV (standard clinical: 10 mm/mV).
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
        Y-axis limits in applied to every lead panel. The default would be fine
        for mV, for μV simply multiply by 1,000.
    label_coordinates : `tuple` [`float`, `float`], default (0.02, 0.95)
        Lead label position as ``(x, y)`` in axes coordinates (0–1).
    
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
    background_colour: str = '#ffd6d6'
    major_grid_colour: str = '#ff6666'
    minor_grid_colour: str = '#ffaaaa'
    # #### grid line widths
    major_grid_linewidth: float = 0.3
    minor_grid_linewidth: float = 0.2
    # #### trace
    trace_colour: str = 'black'
    trace_linewidth: float = 0.4
    # #### calibration
    # x-axis grid spacing is derived from paper_speed (mm/s)
    paper_speed: float = 25.0
    # y-axis grid spacing is derived from mm_per_mv (mm/mV)
    mm_per_mv: float = 10.0
    # #### layout
    clip_on_trace: bool = False
    # Zero spacing mimics continuous ECG paper; increase to separate panels
    hspace: float = 0.0
    wspace: float = 0.0
    # #### axis limits
    # None triggers auto-computation from n_samples / fs at render time
    x_lim: tuple[float, float] | None = None
    y_lim: tuple[float, float] = (-2.0, 2.0)
    # #### lead label
    label_coordinates: tuple[float, float] = (0.02, 0.95)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class ECGDrawing:
    """
    Takes a called reader instance and plots lead-specific ECG signals.
    
    After calling, the instance exposes the rendered figure and per-lead axes
    so the caller can apply further matplotlib customisation directly.
    
    Parameters
    ----------
    leads : `list` [`str`] | `None`, default None
        Lead names to plot by default. Uses the standard 12-lead list when
        None.
    
    Attributes
    ----------
    figure : plt.Figure
        The matplotlib figure.
    axes : dict[str, plt.Axes]
        Dict mapping lead name to its Axes.
    layout_mapper : dict[str, tuple[int, slice]]
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
    default_leads : list[str]
        Lead names plotted by default. Set at init; overridable per call.
    
    Methods
    -------
    tile_x_axis(xlims)
        Tiles each column's x-axis to an equal slice of the full signal,
        mimicking continuous ECG paper. Per-lead overrides via ``xlims``.
    annotate(annotations)
        Adds free-form templated text annotations to the figure;
        ``'{key}'`` placeholders resolve from the captured MetaData.
    to_numpy(crop, close)
        Renders the figure to a 3-D numpy array (RGBA).
    
    """
    # /////////////////////////////////////////////////////////////////////////
    # class attributes
    SOURCE_MAP: dict[str, str] = {
        'waveforms': CoreData.DataTypes.WaveForms,
        'median':    CoreData.DataTypes.MedianBeats,
    }
    _VALID_SHOW_AXES: frozenset[str | None] = frozenset({'x', 'y', 'b', None})
    _VALID_CAL_PULSE_STYLES: frozenset[str] = frozenset({'square', 'line'})
    # /////////////////////////////////////////////////////////////////////////
    # __slots__
    # reducing memory overhead and making the public attribute surface explicit.
    __slots__ = (
        PDNames.DEFAULT_LEADS, PDNames.META_DATA,
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
        """
        Initialises a new instance of ECGDrawing.
        """
        lead_default = [
            v for v in vars(CoreData.Leads).values()
            if isinstance(v, str) and not v.startswith("_")
        ][2:]
        # set to leads or the CoreData.Leads
        setattr(self, PDNames.DEFAULT_LEADS, leads or lead_default)
        setattr(self, PDNames.META_DATA,     None)
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
    def _build_figure(
        self,
        signals: dict[str, np.ndarray],
        mapper: dict[str, tuple[int, slice]],
        style: ECGStyle,
        kwargs_fig: dict[str, Any] | None = None,
        kwargs_gridspec: dict[str, Any] | None = None,
    ) -> tuple[plt.Figure, dict[str, plt.Axes]]:
        """
        Build the GridSpec figure and per-lead axes from a mapper dict.
        
        Parameters
        ----------
        signals : `dict[str, np.ndarray]`
            Signal data extracted from the reader.
        mapper : `dict[str, tuple[int, slice]]`
            Lead name to ``(row_index, col_slice)`` mapping. Dict insertion
            order determines plotting order. Both n_rows and n_cols are
            derived from the mapper — no assumptions about grid size are made.
        style : `ECGStyle`
            Style configuration.
        kwargs_fig : `dict[str, Any]` | `None`, optional
            Extra keyword arguments for ``plt.figure()``. None is treated
            as an empty dict.
        kwargs_gridspec : `dict[str, Any]` | `None`, optional
            Extra keyword arguments for ``GridSpec()``. None is treated
            as an empty dict.
        
        Returns
        -------
        figure : `plt.Figure`
            The created figure.
        axes : `dict` [`str`, `plt.Axes`]
            Mapping of lead name to axes.
        """
        # #### derive grid dimensions from mapper
        n_rows = max(row for row, _ in mapper.values()) + 1
        n_cols = max(col.stop for _, col in mapper.values())
        # #### style values are defaults
        kwargs_fig = kwargs_fig or {}
        kwargs_gridspec = kwargs_gridspec or {}
        # update the kwargs to allow overwriting
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
        # using logger to print warnings
        axes: dict[str, plt.Axes] = {}
        for lead, (row, col) in mapper.items():
            if lead not in signals:
                _log.warning(
                    "Lead %r not found in signal data — axes left blank.", lead
                )
            ax = fig.add_subplot(gs[row, col])
            axes[lead] = ax
        # #### warn about signal data keys the mapper did not request
        for lead in signals:
            if lead not in mapper:
                _log.warning(
                    "Lead %r is in signal data but not requested in "
                    "mapper.", lead,
                )
        # return
        return fig, axes
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _render_leads(
        self,
        axes: dict[str, plt.Axes],
        signals: dict[str, np.ndarray],
        style: ECGStyle,
        sampling_rate: float,
        show_axes: dict[str, str | None] | str | None,
        show_lead_labels: bool,
        cal_pulse: str | None,
        cal_leads: list[str] | None,
        kwargs_plot: dict | dict[str, dict] | None,
        kwargs_grid: dict | dict[str, dict] | None,
        kwargs_ticks: dict | dict[str, dict] | None,
        kwargs_background: dict | dict[str, dict] | None,
        kwargs_label: dict | dict[str, dict] | None,
    ) -> None:
        """
        Render each lead: trace, limits, background, grid, and tick visibility.
        
        Parameters
        ----------
        axes : `dict` [`str`, `plt.Axes`]
            Per-lead axes created by ``_build_figure``.
        signals : `dict[str, np.ndarray]`
            Signal data extracted from the reader.
        style : `ECGStyle`
            Style configuration.
        sampling_rate : `float`
            Sampling frequency in Hz used to build the time axis.
        show_axes : `dict` [`str`, `str` | `None`] | `str` | `None`
            Which axis ticks and labels to show per lead. A string value
            applies uniformly: ``'x'`` x-axis only, ``'y'`` y-axis only,
            ``'b'`` both, ``None`` hides all. A dict maps individual lead
            names to these same string values, leaving unlisted leads hidden.
        show_lead_labels : `bool`
            When True, annotate each panel with its lead name.
        cal_pulse : {'square', 'line'} | `None`
            Calibration pulse style to prepend to each lead, or ``None`` to
            disable. The pulse height follows the clinical 10 mm paper
            convention and is computed as ``10.0 / style.mm_per_mv`` in
            the signal's own units. With the default ``mm_per_mv=10`` this
            is the standard 1 mV pulse for mV signals; for μV signals
            using e.g. ``mm_per_mv=10/1000`` it is 1000 (signal units),
            i.e. a 1 mV-equivalent 10 mm pulse. ``'square'`` draws the
            full rectangular pulse. ``'line'`` draws only a single
            vertical spike, matching the convention used by some
            thermal-paper ECG machines.
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
        """
        minor_x = getattr(self, PDNames.MINOR_STEP_X)
        major_x = getattr(self, PDNames.MAJOR_STEP_X)
        minor_y = getattr(self, PDNames.MINOR_STEP_Y)
        major_y = getattr(self, PDNames.MAJOR_STEP_Y)
        # #### get cal_leads
        if cal_leads is None:
            # simply print cal for each lead
            cal_leads = list(signals.keys())
        for lead, ax in axes.items():
            if lead not in signals:
                # blank axes already created and warned in _build_figure
                continue
            signal = signals[lead]
            # #### prepend calibration pulse
            if (cal_pulse is not None) and (lead in cal_leads):
                n_pre  = round(0.1 * sampling_rate)
                n_post = round(0.1 * sampling_rate)
                # amplitude follows the clinical 10 mm paper convention:
                # mm_per_mv is used as "mm per signal unit" (the y-axis
                # gain), so 10 / mm_per_mv is the pulse height in signal
                # units. With the default mm_per_mv=10 this is 1.0 (the
                # standard 1 mV pulse for mV signals); for μV signals
                # using mm_per_mv=10/1000 it is 1000 (a 1 mV-equivalent
                # 10 mm pulse).
                amp = 10.0 / style.mm_per_mv
                if cal_pulse == 'square':
                    body = np.full(round(0.2 * sampling_rate), amp)
                else:
                    body = np.array([0.0, amp, 0.0])
                # 0.1s zero baseline, 0.2s square body (or 3-sample line), 0.1s zero baseline
                pulse = np.concatenate(
                    [np.zeros(n_pre), body, np.zeros(n_post)])
                # replace the first len(pulse) samples so all leads stay the
                # same length and tile_x_axis windows remain aligned
                signal = signal.copy()
                signal[:len(pulse)] = pulse
            t = np.arange(len(signal)) / sampling_rate
            # #### resolve per-lead kwargs
            p_kw   = _resolve_lead_kwargs(kwargs_plot,       lead)
            g_kw   = _resolve_lead_kwargs(kwargs_grid,       lead)
            t_kw   = _resolve_lead_kwargs(kwargs_ticks,      lead)
            bg_kw  = _resolve_lead_kwargs(kwargs_background, lead)
            # #### trace
            plot_kw = _update_kwargs(
                p_kw,
                color=style.trace_colour,
                lw=style.trace_linewidth,
                clip_on=style.clip_on_trace,
                zorder=3,
            )
            ax.plot(
                t, signal,
                **plot_kw,
            )
            # #### axis limits
            if style.x_lim:
                ax.set_xlim(style.x_lim)
            else:
                ax.set_xlim(0.0, len(signal) / sampling_rate)
            ax.set_ylim(style.y_lim)
            # #### background
            ax.patch.set_facecolor(style.background_colour)
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
                color=style.minor_grid_colour,
                linewidth=style.minor_grid_linewidth,
                zorder=1,
            )
            major_kw = _update_kwargs(
                g_kw,
                color=style.major_grid_colour,
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
            t_params_kwarg = _update_kwargs(
                t_kw,
                axis='both', which='both',
                bottom=False, left=False,
                labelbottom=False, labelleft=False,
            )
            ax.tick_params(
                **t_params_kwarg,
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
                    color=style.trace_colour,
                    clip_on=False,
                )
                ax.text(
                    *style.label_coordinates,
                    lead,
                    transform=ax.transAxes,
                    **lbl_kw,
                )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __call__(
        self,
        reader: Any,
        mapper: dict,
        source: str = "waveforms",
        style: ECGStyle | None = None,
        show_axes: dict[str, str | None] | str | None = None,
        sampling_rate: float | None = None,
        show_lead_labels: bool = False,
        cal_pulse: Literal["square", "line"] | None = None,
        cal_leads: list[str] | None = None,
        kwargs_fig: dict | None = None,
        kwargs_gridspec: dict | None = None,
        kwargs_plot: dict | dict[str, dict] | None = None,
        kwargs_grid: dict | dict[str, dict] | None = None,
        kwargs_ticks: dict | dict[str, dict] | None = None,
        kwargs_background: dict | dict[str, dict] | None = None,
        kwargs_label: dict | dict[str, dict] | None = None,
    ) -> Self:
        """
        Creates an ECG figure from a called reader instance.
        
        Parameters
        ----------
        reader : Any
            A called ECGXMLReader or ECGDICOMReader instance.
        mapper : `dict` [`str`, `tuple` [`int`, `slice`]]
            Layout dict mapping lead names to ``(row_index, col_slice)``.
            Dict insertion order determines plotting order; grid dimensions are
            derived from the mapper values. Mismatch warnings (missing or
            unrequested leads) are emitted at WARNING level via the
            ``ecgprocess.plot_ecgs`` logger.
        source : {'waveforms', 'median'}, default 'waveforms'
            Whether to plot WaveForms or MedianBeats signals. Can be modified
            to use a non-standard source name by updating self.SOURCE_MAP.
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
        cal_pulse : {'square', 'line'} | `None`, default `None`
            Calibration pulse style to prepend to each lead signal before
            rendering. ``None`` disables the pulse. The pulse height
            follows the clinical 10 mm paper convention and is computed
            as ``10.0 / style.mm_per_mv`` in the signal's own units, so
            it always spans 10 mm of plotted paper regardless of unit
            choice (mV, μV, …). With the default ``mm_per_mv=10`` this
            gives the standard 1 mV pulse for mV signals; for μV signals
            using e.g. ``mm_per_mv=10/1000`` it gives 1000 signal units
            (a 1 mV-equivalent 10 mm pulse). ``'square'`` draws the full
            rectangular pulse: 0.1 s baseline, then 0.2 s at the computed
            amplitude, then 0.1 s baseline. ``'line'`` draws only a
            single vertical spike: 0.1 s baseline, then a 3-sample
            rise/peak/fall, then 0.1 s baseline, matching the convention
            used by some thermal-paper ECG machines. The caller's data is
            not mutated.
        cal_leads : `list` [`str`] | `None`, default `None`
            Restricts which leads receive the calibration pulse. When
            `None`, every lead in the signal data receives the pulse
            (provided ``cal_pulse`` is not `None`). Lead names not
            present in the signal data are ignored. Has no effect when
            ``cal_pulse`` is `None`.
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
        
        Returns
        -------
        self : ECGDrawing
            Returns the instance with populated figure, axes, and
            calibration attributes.
        """
        # #### type-check every parameter at the public boundary
        is_type(mapper, dict)
        is_type(source, str)
        is_type(style, (ECGStyle, type(None)))
        is_type(show_axes, (str, dict, type(None)))
        is_type(sampling_rate, (float, int, type(None)))
        is_type(show_lead_labels, bool)
        is_type(cal_pulse, (str, type(None)))
        is_type(cal_leads, (list, type(None)))
        is_type(kwargs_fig, (dict, type(None)))
        is_type(kwargs_gridspec, (dict, type(None)))
        is_type(kwargs_plot, (dict, type(None)))
        is_type(kwargs_grid, (dict, type(None)))
        is_type(kwargs_ticks, (dict, type(None)))
        is_type(kwargs_background, (dict, type(None)))
        is_type(kwargs_label, (dict, type(None)))
        # #### resolve style
        style = style or ECGStyle()
        # #### validate source and extract signals
        if source not in self.SOURCE_MAP:
            raise InputValidationError(
                f"source must be 'waveforms' or 'median', got {source!r}."
            )
        signals = getattr(reader, self.SOURCE_MAP[source], None)
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
        # #### validate show_axes content (type already checked above)
        if isinstance(show_axes, str):
            if show_axes not in self._VALID_SHOW_AXES:
                raise InputValidationError(
                    f"show_axes must be 'x', 'y', 'b', or None, "
                    f"got {show_axes!r}."
                )
        elif isinstance(show_axes, dict):
            invalid = {
                v for v in show_axes.values()
                if v not in self._VALID_SHOW_AXES
            }
            if invalid:
                raise InputValidationError(
                    f"show_axes dict contains invalid values: {invalid!r}."
                )
        # #### validate cal_pulse
        if cal_pulse is not None \
                and cal_pulse not in self._VALID_CAL_PULSE_STYLES:
            raise InputValidationError(
                f"cal_pulse must be 'square', 'line', or None, "
                f"got {cal_pulse!r}."
            )
        # #### build figure
        fig, axes = self._build_figure(
            signals, mapper, style,
            kwargs_fig=kwargs_fig,
            kwargs_gridspec=kwargs_gridspec,
        )
        setattr(self, PDNames.FIGURE,        fig)
        setattr(self, PDNames.AXES,          axes)
        setattr(self, PDNames.LAYOUT_MAPPER, mapper)
        # #### capture metadata for annotation templates and sampling rate
        meta = getattr(reader, CoreData.DataTypes.MetaData, None) or {}
        setattr(self, PDNames.META_DATA, meta)
        # #### resolve sampling rate
        # trying to pull this from the metadata
        if sampling_rate is None:
            sampling_rate = meta.get(CoreData.MetaData.SF)
        # if still None raise an error
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
            cal_pulse=cal_pulse,
            cal_leads=cal_leads,
            kwargs_plot=kwargs_plot,
            kwargs_grid=kwargs_grid,
            kwargs_ticks=kwargs_ticks,
            kwargs_background=kwargs_background,
            kwargs_label=kwargs_label,
        )
        # return
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def tile_x_axis(
        self,
        xlims: dict[str, tuple[float, float]] | None = None,
    ) -> Self:
        """
        Tile the x-axis so each column shows an equal slice of the total
        signal duration, mimicking continuous ECG paper.

        The column count is derived from the mapper used at render time.
        Each column's x window runs from
        ``x_min + col * segment`` to ``x_min + (col + 1) * segment``,
        where ``segment = (x_max - x_min) / n_cols``. Multi-column spans
        (e.g. a full-width rhythm strip) receive the proportionally wider
        window. Each row resets to zero independently.

        Signal data outside a column's x window is removed from the line
        artists rather than clipped. This prevents traces from bleeding
        horizontally into adjacent panels while leaving
        ``clip_on_trace=False`` intact so tall deflections can still cross
        row boundaries.

        Parameters
        ----------
        xlims : `dict` [`str`, `tuple` [`float`, `float`]] | `None`, \
optional
            Per-lead x-axis overrides. Keys are lead names; values are
            ``(x_min, x_max)`` in seconds. Leads not listed fall back to
            the auto-tiled column window.

        Returns
        -------
        self : ECGDrawing
            Returns the instance for method chaining.

        Raises
        ------
        NotCalledError
            If ``__call__`` has not been invoked yet.
        InputValidationError
            If ``xlims`` is not a dict or contains non-tuple values.
        """
        axes = getattr(self, PDNames.AXES)
        mapper = getattr(self, PDNames.LAYOUT_MAPPER)
        if axes is None or mapper is None:
            raise NotCalledError(
                "ECGDrawing must be called before tile_x_axis()."
            )
        is_type(xlims, (dict, type(None)))
        xlims = xlims or {}
        # #### derive total x range and column count from rendered state
        # Use min xlim across all axes so that every tile window has complete
        # signal coverage — leads with cal pulses have a longer xlim than
        # leads without, and using min prevents an empty trailing gap.
        x_min = min(ax.get_xlim()[0] for ax in axes.values())
        x_max = min(ax.get_xlim()[1] for ax in axes.values())
        n_cols = max(col.stop for _, col in mapper.values())
        segment = (x_max - x_min) / n_cols
        for lead, (_, col_slice) in mapper.items():
            if lead in xlims:
                col_x_min, col_x_max = xlims[lead]
            else:
                col_x_min = x_min + col_slice.start * segment
                col_x_max = x_min + col_slice.stop * segment
            ax = axes[lead]
            for line in ax.lines:
                xd = np.asarray(line.get_xdata())
                yd = np.asarray(line.get_ydata())
                mask = (xd >= col_x_min) & (xd <= col_x_max)
                line.set_xdata(xd[mask])
                line.set_ydata(yd[mask])
            ax.set_xlim(col_x_min, col_x_max)
        return self
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def annotate(
        self,
        annotations: list[dict[str, Any]],
    ) -> Self:
        """
        Add free-form templated text annotations to the rendered figure.

        Each annotation is a spec dict pairing a template string with a
        figure-fraction position; any layout (line breaks, spacing, unit
        text) lives in the string itself. ``'{key}'`` placeholders are
        resolved against the MetaData captured from the reader during
        the `__call__` render; plain strings without placeholders are
        drawn literally and need no metadata.

        Parameters
        ----------
        annotations : `list` [`dict` [`str`, `any`]]
            One spec dict per annotation. Required keys: ``'text'``
            (`str`, the template) and ``'xy'`` (a 2-item tuple of
            `float`, the position in 0-1 figure-fraction coordinates).
            All remaining keys are forwarded to
            `matplotlib.figure.Figure.text`, merged with the defaults
            ``fontsize=7``, ``ha='left'``, ``va='bottom'``
            (caller-supplied values win).

        Returns
        -------
        self : ECGDrawing
            The instance, allowing chaining after `__call__` and
            `tile_x_axis`.

        Raises
        ------
        NotCalledError
            If __call__ has not been invoked yet.
        InputValidationError
            If a spec dict is malformed, or a referenced metadata key
            is missing or None.

        Notes
        -----
        Templates support ``\\n`` line breaks, format specs such as
        ``'{key:.1f}'``, and literal braces via ``'{{'``/``'}}'``.
        Metadata keys containing ``'.'`` or ``'['`` are interpreted by
        the `str.format` field grammar and cannot be referenced.
        """
        # #### the figure must exist before it can be annotated
        fig = getattr(self, PDNames.FIGURE)
        if fig is None:
            raise NotCalledError(
                "ECGDrawing must be called before annotate()."
            )
        # #### check input
        is_type(annotations, list)
        meta = getattr(self, PDNames.META_DATA)
        # #### resolve and draw each annotation
        for spec in annotations:
            text, xy, extras = _split_annotation_spec(spec)
            resolved = _resolve_annotation(text, meta)
            # caller-supplied keys override the defaults
            txt_kw = _update_kwargs(
                extras,
                fontsize=7, ha='left', va='bottom',
            )
            fig.text(xy[0], xy[1], resolved, **txt_kw)
        # return
        return self
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
        # input
        is_type(crop, bool)
        is_type(close, bool)
        # get figure
        fig = getattr(self, PDNames.FIGURE)
        if fig is None:
            raise NotCalledError(
                "ECGDrawing must be called before to_numpy()."
            )
        # cropping
        if crop:
            fig.tight_layout(pad=0)
        fig.canvas.draw()
        # get array from fig
        arr = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).copy()
        h, w = fig.canvas.get_width_height()[::-1]
        arr = arr.reshape(h, w, 4)
        # close if needed and results attributes
        if close:
            plt.close(fig)
            setattr(self, PDNames.FIGURE, None)
            setattr(self, PDNames.AXES,   None)
        # return
        return arr

