"""
HR Attrition Analytics — chart theme
Author : Alok Kumar Ojha
Purpose: One place for the palette and the chart chrome, so every figure in the
         dashboard reads as part of the same system.

Colour is assigned by the job it does, not by taste:

    identity    categorical slots, in fixed order, never cycled
    magnitude   one hue, light -> dark
    polarity    two hues that read as opposite + a neutral midpoint
    emphasis    one accent against recessive grey

Most charts here carry a single measure — attrition rate — so they use one
colour for every mark, and the accent is spent on the one category that
carries the story. Colouring nominal bars darker-where-bigger would
double-encode the bar length and burn the only free channel on information
the chart already shows.

RISK_BANDS is the one place a fixed colour meaning is imposed: Low/Medium/High
is an ordered domain scale where green-amber-red is the convention every HR
reader already knows, so inventing a different mapping would only cost the
reader a legend lookup. It is checked for contrast against the surface rather
than assumed, and the bands are also distinguishable by position and label, so
the colour is reinforcing rather than load-bearing.
"""

# --- surfaces and ink ---------------------------------------------------
SURFACE = "#fcfcfb"        # chart surface
PLANE = "#f9f9f7"          # page plane
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"      # axis and tick labels
GRIDLINE = "#e1e0d9"       # hairline, solid — never dashed
BASELINE = "#c3c2b7"

# --- categorical slots (fixed order) ------------------------------------
SERIES_1 = "#2a78d6"       # blue
SERIES_2 = "#eb6834"       # orange
SERIES_3 = "#1baf7a"       # aqua

# --- polarity (diverging pair: warm/cool, neutral midpoint) -------------
POS = "#2a78d6"            # blue  — the better outcome
NEG = "#e34948"            # red   — the worse outcome

# --- emphasis -----------------------------------------------------------
ACCENT = SERIES_1
RECESSIVE = "#c3c2b7"      # the "grey the rest" fill

# --- ordinal ramp (ordered categories only) -----------------------------
# Validated: single hue, monotone light->dark, all adjacent dL >= 0.06.
ORDINAL_5 = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
ORDINAL_4 = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"]

# --- risk bands (ordered domain scale, conventional meaning) ------------
RISK_BANDS = {
    "Low": "#1baf7a",
    "Medium": "#d99514",
    "High": "#e34948",
}
RISK_ORDER = ["High", "Medium", "Low"]

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def style(fig, height=340, showlegend=False, xtitle=None, ytitle=None):
    """Apply the shared chart chrome: recessive grid, hairline axes, no clutter."""
    fig.update_layout(
        height=height,
        showlegend=showlegend,
        # Thin marks with room to breathe. Saturated fills belong on small
        # marks and accents, not on large blocks.
        bargap=0.45,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_SECONDARY),
        margin=dict(l=8, r=16, t=8, b=8),
        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=BASELINE,
            font=dict(family=FONT, size=13, color=INK_PRIMARY),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            title_text="",
        ),
    )
    axis = dict(
        showgrid=True,
        gridcolor=GRIDLINE,
        gridwidth=1,
        griddash="solid",
        zeroline=False,
        linecolor=BASELINE,
        tickfont=dict(color=INK_MUTED, size=12),
        title_font=dict(color=INK_MUTED, size=12),
    )
    fig.update_xaxes(**axis, title_text=xtitle)
    fig.update_yaxes(**axis, title_text=ytitle)
    return fig


def pct(v, decimals=2):
    """Format a percentage for display."""
    return f"{v:.{decimals}f}%"


def money(v, decimals=0):
    """Format a salary figure. The IBM dataset carries no currency unit."""
    return f"{v:,.{decimals}f}"


def emphasis_colors(labels, highlight):
    """Accent the one category that carries the story; grey the rest."""
    return [ACCENT if lab == highlight else RECESSIVE for lab in labels]
