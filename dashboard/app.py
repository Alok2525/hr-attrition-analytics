"""
HR Attrition Analytics — dashboard
Author : Alok Kumar Ojha
Purpose: A 3-page dashboard over 1,470 IBM HR employee records — the attrition
         picture, the drivers behind it, and the per-employee risk list the
         model produces.
Run    : streamlit run dashboard/app.py     (from the repo root)

Every figure traces back to a query in attrition_analysis.sql and to a number
recorded in notes/key-numbers.md. The sanity check on page 1 asserts that
relationship out loud rather than leaving it to be trusted.

Two population sizes appear in this app and both are correct:

    1,470   every employee — pages 1 and 2, read from MySQL
    1,233   current employees only — page 3, read from the model's CSV output

Page 3 excludes the 237 who already left, because scoring them would be
scoring a known outcome. The page says so on screen.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import queries as q
import theme as t

st.set_page_config(
    page_title="HR Attrition Analytics",
    page_icon="👥",
    layout="wide",
)

# ----------------------------------------------------------------------
# Chrome
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <style>
      .stApp {{ background: {t.PLANE}; }}
      .block-container {{ padding-top: 2.5rem; max-width: 1280px; }}
      .tile {{
        background: {t.SURFACE};
        border: 1px solid rgba(11,11,11,0.10);
        border-radius: 10px;
        padding: 16px 18px;
        height: 100%;
      }}
      .tile-label {{
        font-size: 12px; letter-spacing: .04em; text-transform: uppercase;
        color: {t.INK_MUTED}; margin-bottom: 6px;
      }}
      .tile-value {{
        font-size: 30px; line-height: 1.15; font-weight: 600;
        color: {t.INK_PRIMARY};
      }}
      .tile-note {{ font-size: 12px; color: {t.INK_SECONDARY}; margin-top: 6px; }}
      .section {{
        font-size: 13px; letter-spacing: .04em; text-transform: uppercase;
        color: {t.INK_MUTED}; margin: 26px 0 10px;
      }}
      .finding {{
        background: {t.SURFACE};
        border-left: 3px solid {t.ACCENT};
        border-radius: 4px;
        padding: 14px 16px;
        color: {t.INK_PRIMARY};
        font-size: 15px;
      }}
      .headline {{
        background: {t.SURFACE};
        border: 1px solid rgba(11,11,11,0.10);
        border-left: 3px solid {t.NEG};
        border-radius: 10px;
        padding: 22px 26px;
      }}
      .headline-value {{
        font-size: 56px; line-height: 1; font-weight: 600; color: {t.NEG};
      }}
      .headline-label {{
        font-size: 16px; color: {t.INK_PRIMARY}; margin-top: 10px;
      }}
      .headline-note {{ font-size: 13px; color: {t.INK_SECONDARY}; margin-top: 8px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def tile(col, label, value, note=None):
    col.markdown(
        f'<div class="tile"><div class="tile-label">{label}</div>'
        f'<div class="tile-value">{value}</div>'
        + (f'<div class="tile-note">{note}</div>' if note else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def section(label):
    st.markdown(f'<div class="section">{label}</div>', unsafe_allow_html=True)


def finding(text):
    st.markdown(f'<div class="finding">{text}</div>', unsafe_allow_html=True)


def table_view(df, label="Table view"):
    """Every chart gets a WCAG-clean twin — colour is never the only channel."""
    with st.expander(label):
        st.dataframe(df, width="stretch", hide_index=True)


def rate_bar(df, label_col, value_col, height=300, highlight=None,
             ordinal=False, horizontal=False, xtitle=None, ytitle=None,
             hover_extra=None):
    """A single-measure attrition-rate bar chart, coloured by its job.

    Ordered categories get the single-hue ramp; nominal ones get one colour
    with the accent spent on the category that carries the story.
    """
    labels = df[label_col].astype(str)
    if ordinal:
        ramp = t.ORDINAL_5 if len(df) > 4 else t.ORDINAL_4
        colors = ramp[:len(df)]
    elif highlight is not None:
        colors = t.emphasis_colors(labels, highlight)
    else:
        colors = t.SERIES_1

    customdata = df[hover_extra] if hover_extra else None
    suffix = (f"<br>%{{customdata[0]:,}} employees" if hover_extra else "")

    if horizontal:
        fig = go.Figure(go.Bar(
            x=df[value_col], y=labels, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            customdata=customdata,
            hovertemplate="%{y}<br>%{x:.2f}%" + suffix + "<extra></extra>",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=labels, y=df[value_col],
            marker=dict(color=colors, line=dict(width=0)),
            customdata=customdata,
            hovertemplate="%{x}<br>%{y:.2f}%" + suffix + "<extra></extra>",
        ))
    return t.style(fig, height=height, xtitle=xtitle, ytitle=ytitle)


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
@st.cache_resource
def engine():
    return q.get_engine()


@st.cache_data(ttl=3600)
def load(sql):
    return q.run(engine(), sql)


@st.cache_data(ttl=3600)
def risk_scores():
    return q.load_risk_scores()


@st.cache_data(ttl=3600)
def hike_simulation():
    """Wide format: one row per employee, one column per hike level."""
    long = q.load_hike_simulation()
    return long.pivot(index="employee_number", columns="hike_pct",
                      values="attrition_probability")


# ----------------------------------------------------------------------
# Page 1 — Attrition Overview
# ----------------------------------------------------------------------
def page_overview():
    k = load(q.KPIS).iloc[0]
    by_dept = load(q.ATTRITION_BY_DEPARTMENT)
    by_role = load(q.ATTRITION_BY_ROLE)
    by_age = load(q.ATTRITION_BY_AGE)
    worst_role = load(q.WORST_ROLE_PER_DEPARTMENT)

    st.title("Attrition Overview")
    st.caption(
        "1,470 employee records from the IBM HR Analytics dataset. "
        "Attrition is recorded as a completed fact, not a forecast."
    )

    # .iloc[0] on a mixed-dtype row yields floats for every column, so the
    # counts are cast back before they are formatted.
    c = st.columns(4)
    tile(c[0], "Headcount", f"{int(k.headcount):,}", "all employee records")
    tile(c[1], "Leavers", f"{int(k.leavers):,}", "attrition = Yes")
    tile(c[2], "Attrition rate", t.pct(k.attrition_pct),
         "the 84/16 class imbalance")
    tile(c[3], "Average tenure", f"{k.avg_tenure:.1f} yrs",
         f"average age {k.avg_age:.0f}")

    worst = by_role.iloc[0]
    finding(
        f"Attrition runs at <b>{t.pct(k.attrition_pct)}</b> overall, but it is not "
        f"spread evenly. <b>{worst.job_role}</b> loses "
        f"<b>{t.pct(worst.attrition_pct)}</b> of its {int(worst.headcount)} people — "
        f"{worst.attrition_pct / k.attrition_pct:.1f}× the company rate — and the "
        f"under-30 cohort loses "
        f"<b>{t.pct(by_age.iloc[0].attrition_pct)}</b>. The company average is the "
        "one number that describes nobody."
    )

    left, right = st.columns(2)

    with left:
        section("Attrition by department")
        st.plotly_chart(
            rate_bar(by_dept, "department", "attrition_pct", height=300,
                     highlight=by_dept.iloc[0]["department"],
                     hover_extra=["headcount"], ytitle="Attrition rate (%)"),
            width="stretch",
        )
        st.caption(
            "Nominal categories, so one colour with the accent on the worst — "
            "shading them by value would repeat what the bar height already says."
        )
        table_view(by_dept, "Table view — departments")

    with right:
        section("Attrition by age group")
        st.plotly_chart(
            rate_bar(by_age, "age_group", "attrition_pct", height=300,
                     ordinal=True, hover_extra=["employees"],
                     ytitle="Attrition rate (%)"),
            width="stretch",
        )
        st.caption(
            "Ordered buckets, so these use a single-hue ordinal ramp. The "
            "gradient is real: under-30s leave at "
            f"{t.pct(by_age.iloc[0].attrition_pct)} against "
            f"{t.pct(by_age['attrition_pct'].min())} at the safest age."
        )
        table_view(by_age, "Table view — age groups")

    section("Attrition by job role")
    r = by_role.sort_values("attrition_pct")
    st.plotly_chart(
        rate_bar(r, "job_role", "attrition_pct", height=400, horizontal=True,
                 highlight=by_role.iloc[0]["job_role"],
                 hover_extra=["headcount"], xtitle="Attrition rate (%)"),
        width="stretch",
    )
    st.caption(
        f"{worst.job_role} is the worst at {t.pct(worst.attrition_pct)}, but it is "
        f"only {int(worst.headcount)} people. Laboratory Technician sits lower at "
        f"{t.pct(by_role.iloc[1].attrition_pct)} and covers "
        f"{int(by_role.iloc[1].headcount)} — the larger absolute loss. Rate and "
        "headcount answer different questions."
    )
    table_view(by_role, "Table view — all 9 roles")

    section("Worst role inside each department")
    top_per_dept = worst_role[worst_role["risk_rank"] == 1]
    st.dataframe(top_per_dept, width="stretch", hide_index=True)
    st.caption(
        "A department head does not manage the company average. This is the "
        "`RANK() OVER (PARTITION BY department)` result from Q12."
    )

    # The check that keeps this dashboard honest.
    section("Sanity check against the SQL layer")
    checks = pd.DataFrame(
        [
            ("Headcount", float(k.headcount), 1470.0),
            ("Leavers", float(k.leavers), 237.0),
            ("Overall attrition %", float(k.attrition_pct), 16.12),
            ("Worst role — Sales Representative %",
             float(by_role.iloc[0].attrition_pct), 39.76),
            ("Under 30 %", float(by_age.iloc[0].attrition_pct), 27.91),
        ],
        columns=["Measure", "Dashboard", "notes/key-numbers.md"],
    )
    checks["Match"] = [
        "✅" if abs(a - b) < 0.01 else "❌"
        for a, b in zip(checks["Dashboard"], checks["notes/key-numbers.md"])
    ]
    st.dataframe(checks, width="stretch", hide_index=True)
    st.caption(
        "Recomputed live from MySQL on every load and compared to the figures "
        "recorded when the SQL layer was run. A ❌ here means the dashboard and "
        "the notes have diverged, and one of them is wrong."
    )


# ----------------------------------------------------------------------
# Page 2 — Risk Factors
# ----------------------------------------------------------------------
def page_risk_factors():
    overtime = load(q.ATTRITION_BY_OVERTIME)
    income_q = load(q.ATTRITION_BY_INCOME_QUARTILE)
    tenure = load(q.ATTRITION_BY_TENURE)
    wlb = load(q.WORK_LIFE_BALANCE_GRID)
    commute = load(q.ATTRITION_BY_COMMUTE)
    cohort = load(q.COMPOUND_RISK_COHORT)
    income = load(q.INCOME_LEAVERS_VS_STAYERS)

    st.title("Risk Factors")
    st.caption("What separates the people who leave from the people who stay.")

    ot = overtime.set_index("over_time")["attrition_pct"]
    multiple = ot["Yes"] / ot["No"]

    st.markdown(
        f'<div class="headline">'
        f'<div class="headline-value">{multiple:.2f}×</div>'
        f'<div class="headline-label">Employees working overtime leave '
        f'{multiple:.1f} times more often</div>'
        f'<div class="headline-note">{t.pct(ot["Yes"])} of the '
        f'{int(overtime.set_index("over_time").loc["Yes", "employees"]):,} on '
        f'overtime, against {t.pct(ot["No"])} of the '
        f'{int(overtime.set_index("over_time").loc["No", "employees"]):,} who are '
        f'not. Overtime is the only top-five model driver HR can change directly '
        f'— income, age and tenure are slower levers.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    section("Overtime")
    fig = go.Figure(go.Bar(
        x=overtime["over_time"].map({"No": "No overtime", "Yes": "Overtime"}),
        y=overtime["attrition_pct"],
        marker=dict(color=[t.POS, t.NEG], line=dict(width=0)),
        customdata=overtime[["employees"]],
        hovertemplate="%{x}<br>%{y:.2f}%<br>%{customdata[0]:,} employees<extra></extra>",
    ))
    st.plotly_chart(t.style(fig, height=280, ytitle="Attrition rate (%)"),
                    width="stretch")
    st.caption(
        "The one chart on this page using the polarity pair — the two bars are "
        "opposite outcomes of the same choice, not two members of a category."
    )
    table_view(overtime, "Table view — overtime")

    left, right = st.columns(2)

    with left:
        section("Attrition by income quartile")
        iq = income_q.copy()
        iq["band"] = [f"Q{int(r.income_quartile)}  {int(r.band_min):,}–{int(r.band_max):,}"
                      for r in iq.itertuples()]
        st.plotly_chart(
            rate_bar(iq, "band", "attrition_pct", height=310, ordinal=True,
                     hover_extra=["employees"], ytitle="Attrition rate (%)"),
            width="stretch",
        )
        st.caption(
            f"Monotonic from {t.pct(iq.iloc[0].attrition_pct)} in the bottom "
            f"quartile to {t.pct(iq.iloc[-1].attrition_pct)} in the top. "
            "Quartile edges come from `NTILE(4)` over the data, not from "
            "round-number salary bands chosen by hand."
        )
        table_view(income_q, "Table view — income quartiles")

    with right:
        section("Attrition by tenure")
        st.plotly_chart(
            rate_bar(tenure, "tenure_bucket", "attrition_pct", height=310,
                     ordinal=True, hover_extra=["employees"],
                     ytitle="Attrition rate (%)"),
            width="stretch",
        )
        st.caption(
            f"Also monotonic — {t.pct(tenure.iloc[0].attrition_pct)} in the first "
            f"two years down to {t.pct(tenure.iloc[-1].attrition_pct)} after ten. "
            "Attrition here is a front-loaded problem, which makes onboarding and "
            "the first-year experience the place to spend."
        )
        table_view(tenure, "Table view — tenure buckets")

    section("The compound risk cohort")
    ch = cohort.set_index("profile")
    hi = ch.loc["Compound risk cohort"]
    lo = ch.loc["Everyone else"]
    finding(
        f"Overtime <b>and</b> income under 3,000 <b>and</b> three years or less: "
        f"<b>{t.pct(hi.attrition_pct)}</b> attrition against "
        f"<b>{t.pct(lo.attrition_pct)}</b> for everyone else — a "
        f"<b>{hi.attrition_pct / lo.attrition_pct:.2f}×</b> multiple. It is only "
        f"<b>{int(hi.employees)} people</b>, and that is what makes it usable: a "
        f"retention budget aimed at {int(hi.employees)} named employees is an "
        "intervention, not a policy paper."
    )
    fig = go.Figure(go.Bar(
        x=cohort["profile"], y=cohort["attrition_pct"],
        marker=dict(color=[t.NEG, t.RECESSIVE], line=dict(width=0)),
        customdata=cohort[["employees"]],
        hovertemplate="%{x}<br>%{y:.2f}%<br>%{customdata[0]:,} employees<extra></extra>",
    ))
    st.plotly_chart(t.style(fig, height=260, ytitle="Attrition rate (%)"),
                    width="stretch")
    table_view(cohort, "Table view — compound cohort")

    section("Work-life balance × job satisfaction")
    grid = wlb.pivot(index="work_life_balance", columns="job_satisfaction",
                     values="attrition_pct")
    counts = wlb.pivot(index="work_life_balance", columns="job_satisfaction",
                       values="employees")
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=[f"Job satisfaction {c}" for c in grid.columns],
        y=[f"Work-life balance {i}" for i in grid.index],
        colorscale=[[0, "#eef4fc"], [1, t.NEG]],
        customdata=counts.values,
        hovertemplate=("%{y} · %{x}<br>%{z:.2f}% attrition"
                       "<br>%{customdata:,} employees<extra></extra>"),
        colorbar=dict(title="Attrition %", outlinewidth=0,
                      tickfont=dict(color=t.INK_MUTED, size=11)),
    ))
    fig.update_traces(
        text=[[f"{z:.0f}%<br><span style='font-size:10px'>n={n}</span>"
               for z, n in zip(zrow, nrow)]
              for zrow, nrow in zip(grid.values, counts.values)],
        texttemplate="%{text}",
        textfont=dict(size=12, family=t.FONT),
    )
    st.plotly_chart(t.style(fig, height=330), width="stretch")
    st.caption(
        "The cell counts are printed because some of them are thin — the worst "
        f"cell holds {int(counts.values.min())} employees at the smallest. A rate "
        "computed over a handful of people is a rate you should not act on alone."
    )
    table_view(wlb, "Table view — the full 4×4 grid")

    left, right = st.columns(2)

    with left:
        section("Commute distance")
        st.plotly_chart(
            rate_bar(commute, "commute_band", "attrition_pct", height=280,
                     ordinal=True, hover_extra=["employees"],
                     ytitle="Attrition rate (%)"),
            width="stretch",
        )
        table_view(commute, "Table view — commute")

    with right:
        section("Income — leavers against stayers")
        inc = income.copy()
        inc["label"] = inc["attrition"].map({"Yes": "Left", "No": "Stayed"})
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=inc["label"], y=inc["avg_monthly_income"], name="Mean",
            marker=dict(color=t.SERIES_1, line=dict(width=0)),
            hovertemplate="%{x}<br>mean %{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=inc["label"], y=inc["median_monthly_income"], name="Median",
            marker=dict(color=t.SERIES_2, line=dict(width=0)),
            hovertemplate="%{x}<br>median %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(barmode="group")
        st.plotly_chart(
            t.style(fig, height=280, showlegend=True, ytitle="Monthly income"),
            width="stretch",
        )
        st.caption(
            "Mean and median disagree by about 1,600 because the income "
            "distribution is right-skewed. Both are shown rather than picking "
            "the flattering one."
        )
        table_view(income, "Table view — income")

    section("A caveat about the model's own driver ranking")
    st.warning(
        "`DailyRate`, `HourlyRate` and `MonthlyRate` all rank inside the model's "
        "top ten by Gini importance — and all three are random filler in this "
        "dataset. Measured correlation with attrition runs −0.007 to −0.057, "
        "against −0.160 for MonthlyIncome. They rank high because Gini "
        "importance is biased toward high-cardinality continuous features. That "
        "is a property of the metric, not a finding, and permutation importance "
        "is the fix. None of the charts on this page use them."
    )


# ----------------------------------------------------------------------
# Page 3 — At-Risk Employees
# ----------------------------------------------------------------------
def page_at_risk():
    scores = risk_scores()
    sim = hike_simulation()

    st.title("At-Risk Employees")
    st.caption(
        "The actionable list — 1,233 current employees ranked by the model's "
        "predicted probability of leaving. The 237 who already left are "
        "excluded: scoring them would be scoring a known outcome."
    )

    bands = (scores["risk_band"].value_counts()
             .reindex(t.RISK_ORDER).fillna(0).astype(int))
    high = int(bands["High"])

    c = st.columns(4)
    tile(c[0], "Employees scored", f"{len(scores):,}", "current employees only")
    tile(c[1], "High risk", f"{high}", "p > 0.6")
    tile(c[2], "Medium risk", f"{int(bands['Medium'])}", "0.3 < p ≤ 0.6")
    tile(c[3], "Model ROC-AUC", "0.774", "recall on leavers 0.34")

    finding(
        "Every employee here is scored <b>out of fold</b> — by a model that never "
        "saw their record during training. Scoring them with a model fitted on "
        "their own rows collapsed the probabilities: all ten of the original "
        "high-risk employees came from the held-out fifth and none from the 986 "
        "trained-on rows, because the model had already memorised their "
        f"<code>Attrition = No</code> label. Correcting it moved high risk from "
        f"10 to {high} and medium from 131 to {int(bands['Medium'])}."
    )

    section("Risk band distribution")
    b = bands.reset_index()
    b.columns = ["risk_band", "employees"]
    b["pct"] = (100 * b["employees"] / len(scores)).round(2)
    fig = go.Figure(go.Bar(
        x=b["employees"], y=b["risk_band"], orientation="h",
        marker=dict(color=[t.RISK_BANDS[x] for x in b["risk_band"]],
                    line=dict(width=0)),
        customdata=b[["pct"]],
        hovertemplate="%{y} risk<br>%{x:,} employees (%{customdata[0]:.1f}%)<extra></extra>",
    ))
    st.plotly_chart(t.style(fig, height=220, xtitle="Employees"),
                    width="stretch")

    st.warning(
        f"**Read this list as a screening aid, not a verdict.** Recall on actual "
        f"leavers is 0.34 — the model catches 16 of 47 in the test set at the "
        f"default threshold. It is good at ranking who to talk to first and bad "
        f"at guaranteeing it has found everyone. The {high} names below are where "
        f"a retention conversation is most likely to be worth having, not a list "
        f"of people who will leave."
    )

    section("The ranked list")
    f1, f2 = st.columns([1, 2])
    with f1:
        band_filter = st.multiselect(
            "Risk band", t.RISK_ORDER, default=["High", "Medium"])
    with f2:
        dept_filter = st.multiselect(
            "Department", sorted(scores["department"].unique()),
            default=list(sorted(scores["department"].unique())))

    view = scores[scores["risk_band"].isin(band_filter)
                  & scores["department"].isin(dept_filter)]
    view = view.sort_values("attrition_probability", ascending=False)

    st.dataframe(
        view.style.map(
            lambda v: f"background-color: {t.RISK_BANDS.get(v, '')}22;"
                      f"color: {t.RISK_BANDS.get(v, t.INK_PRIMARY)};",
            subset=["risk_band"],
        ),
        width="stretch", hide_index=True, height=420,
        column_config={
            "employee_number": st.column_config.NumberColumn("Employee", format="%d"),
            "department": "Department",
            "job_role": "Job role",
            "over_time": "Overtime",
            "monthly_income": st.column_config.NumberColumn(
                "Monthly income", format="%,d"),
            "years_at_company": st.column_config.NumberColumn("Tenure (yrs)"),
            "attrition_probability": st.column_config.ProgressColumn(
                "Risk", min_value=0.0, max_value=1.0, format="%.3f"),
            "risk_band": "Band",
        },
    )
    st.caption(
        f"Showing {len(view):,} of {len(scores):,} scored employees. Sortable by "
        "any column — the default order is the model's ranking."
    )

    # ------------------------------------------------------------------
    # The what-if
    # ------------------------------------------------------------------
    section("What-if — a salary hike")

    st.markdown(
        "This re-runs the model. Every employee's `MonthlyIncome` is raised by "
        "the chosen percentage and scored again by the same fold model that "
        "never saw them, so the 0% column reproduces the ranked list above "
        "exactly. It is **not** a linear approximation of the risk score."
    )

    s1, s2 = st.columns([1, 2])
    with s1:
        hike = st.select_slider("Salary hike", options=list(sim.columns),
                                value=15, format_func=lambda v: f"+{v}%")
    with s2:
        scope = st.radio(
            "Apply the hike to",
            ["Everyone (1,233)", "Bottom income quartile", "Already high risk"],
            horizontal=True,
        )

    idx = scores.set_index("employee_number")
    if scope == "Bottom income quartile":
        keep = idx[idx["monthly_income"] <= idx["monthly_income"].quantile(0.25)].index
    elif scope == "Already high risk":
        keep = idx[idx["risk_band"] == "High"].index
    else:
        keep = idx.index

    subset = sim.loc[sim.index.intersection(keep)]
    base_mean, new_mean = subset[0].mean(), subset[hike].mean()
    base_high, new_high = int((subset[0] > 0.6).sum()), int((subset[hike] > 0.6).sum())

    c = st.columns(4)
    tile(c[0], "Employees in scope", f"{len(subset):,}",
         f"median income {idx.loc[subset.index, 'monthly_income'].median():,.0f}")
    tile(c[1], "Mean predicted risk", f"{new_mean:.1%}",
         f"was {base_mean:.1%} at +0%")
    tile(c[2], "High risk (p > 0.6)", f"{new_high}", f"was {base_high} at +0%")
    tile(c[3], "Change", f"{100 * (new_mean - base_mean):+.2f} pt",
         "in mean predicted risk")

    fig = go.Figure()
    for label, sel in [
        ("Everyone", idx.index),
        ("Bottom income quartile",
         idx[idx["monthly_income"] <= idx["monthly_income"].quantile(0.25)].index),
        ("Already high risk", idx[idx["risk_band"] == "High"].index),
    ]:
        rows = sim.loc[sim.index.intersection(sel)]
        fig.add_trace(go.Scatter(
            x=list(sim.columns), y=[100 * rows[h].mean() for h in sim.columns],
            mode="lines+markers", name=label,
            line=dict(width=2),
            hovertemplate=f"{label}<br>+%{{x}}%<br>%{{y:.2f}}% mean risk<extra></extra>",
        ))
    fig.update_traces(marker=dict(size=6))
    fig.data[0].line.color = t.RECESSIVE
    fig.data[1].line.color = t.SERIES_1
    fig.data[2].line.color = t.NEG
    st.plotly_chart(
        t.style(fig, height=320, showlegend=True,
                xtitle="Salary hike (%)", ytitle="Mean predicted risk (%)"),
        width="stretch",
    )

    everyone = sim
    bottom = sim.loc[sim.index.intersection(
        idx[idx["monthly_income"] <= idx["monthly_income"].quantile(0.25)].index)]
    top_hike = sim.columns[-1]
    delta = sim[top_hike] - sim[0]

    finding(
        f"A blanket <b>+{top_hike}%</b> raise moves mean predicted risk from "
        f"<b>{everyone[0].mean():.1%}</b> to <b>{everyone[top_hike].mean():.1%}</b> "
        f"— {100 * (everyone[top_hike].mean() - everyone[0].mean()):.1f} points, "
        f"across the entire payroll. Aimed only at the bottom income quartile it "
        f"moves <b>{bottom[0].mean():.1%} → {bottom[top_hike].mean():.1%}</b>, "
        f"roughly <b>{(bottom[0].mean() - bottom[top_hike].mean()) / (everyone[0].mean() - everyone[top_hike].mean()):.0f}×</b> "
        f"the effect for a quarter of the cost. Pay is a driver, but it is not a "
        f"lever you pull uniformly."
    )

    st.warning(
        f"**{int((delta > 0.001).sum()):,} of {len(sim):,} employees score "
        f"*higher* after a +{top_hike}% raise**, against "
        f"{int((delta < -0.001).sum()):,} who score lower. Income is not "
        "monotonic in isolation: the model has learned that well-paid leavers "
        "are a different population — senior, more marketable, and leaving for "
        "reasons a raise does not address.\n\n"
        "The honest limit of this simulation is that raising `MonthlyIncome` "
        "alone moves an employee into a region of feature space the model never "
        "observed — income is correlated with `JobLevel`, `TotalWorkingYears` "
        "and `JobRole`, and a Sales Representative on a director's salary is not "
        "a person in the training data. Treat it as a directional sensitivity "
        "analysis against a real model, not a causal estimate of what a raise "
        "would do."
    )


# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------
PAGES = {
    "Attrition Overview": page_overview,
    "Risk Factors": page_risk_factors,
    "At-Risk Employees": page_at_risk,
}

# ?page=Risk+Factors opens straight to a page, so individual views can be
# linked and captured without clicking through the sidebar.
requested = st.query_params.get("page", "")
start = list(PAGES).index(requested) if requested in PAGES else 0

with st.sidebar:
    st.markdown("### HR Attrition Analytics")
    st.caption("IBM HR dataset · 1,470 employees")
    choice = st.radio("Page", list(PAGES), index=start, label_visibility="collapsed")
    st.divider()
    st.caption(
        "Pages 1–2 read aggregates from MySQL, cached for an hour. Page 3 reads "
        "the model's out-of-fold scores from `outputs/`. Every figure traces to "
        "a query in `attrition_analysis.sql` and a number in "
        "`notes/key-numbers.md`."
    )

PAGES[choice]()
