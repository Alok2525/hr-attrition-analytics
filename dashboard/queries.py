"""
HR Attrition Analytics — dashboard queries
Author : Alok Kumar Ojha
Purpose: Every figure the dashboard renders, aggregated in MySQL rather than in
         pandas.

Each query mirrors one in attrition_analysis.sql, so a dashboard number that
disagrees with notes/key-numbers.md is a bug in one of the two — not a
rounding difference. The query constants below are named for the question they
answer and tagged with the SQL file's Q-number.

Two sources, and the split is deliberate:

    MySQL  hr_analytics.employees        all 1,470 employees, snake_case
    CSV    outputs/employee_risk_scores  1,233 current employees, snake_case
    CSV    outputs/hike_simulation       the same 1,233 at 7 hike levels

The model outputs stay in CSV because they are model artifacts, not source
data — they are reproduced by re-running 02_prediction_model.py, and writing
them back into the database would make the database a mix of observed facts
and one particular run's predictions.

⚠️ The casing differs between the two: the script snake-cases columns on the
way into MySQL but exports the CSVs from the original DataFrame. The CSV
loaders below normalise to snake_case so the two can be joined on
employee_number without a silent empty result.
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = REPO_ROOT / "outputs"


def get_engine():
    """Build the MySQL engine from the same env vars the rest of the repo uses."""
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD")
    if not password:
        raise SystemExit(
            "Set MYSQL_PASSWORD first:  export MYSQL_PASSWORD='...'"
        )
    host = os.environ.get("MYSQL_HOST", "localhost")
    db = os.environ.get("MYSQL_DB", "hr_analytics")
    return create_engine(
        f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:3306/{db}"
    )


def run(engine, sql, **params):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or None)


def _snake(df):
    """MonthlyIncome -> monthly_income, matching the MySQL table's casing."""
    df.columns = (df.columns
                  .str.replace(r"(?<!^)(?=[A-Z])", "_", regex=True)
                  .str.lower())
    return df


def _model_output(filename):
    """Read a model artifact, or say plainly how to produce it.

    These two files are gitignored — they are one training run's output, not
    source data — so a clean clone has neither until the model script has been
    run. Without this, page 3 fails on a bare FileNotFoundError that reads like
    a bug in the dashboard rather than a step not yet taken.
    """
    path = OUTPUTS / filename
    if not path.exists():
        raise SystemExit(
            f"{path} is missing.\n"
            "It is generated, not committed. Run the model first:\n\n"
            "    python 02_prediction_model.py\n"
        )
    return pd.read_csv(path)


def load_risk_scores():
    """The actionable list: current employees, scored out-of-fold."""
    return _snake(_model_output("employee_risk_scores.csv"))


def load_hike_simulation():
    """Long format — one row per (employee, hike level)."""
    return _model_output("hike_simulation.csv")


# ----------------------------------------------------------------------
# Headline KPIs — Q1 plus the supporting averages
# ----------------------------------------------------------------------

KPIS = """
SELECT
    COUNT(*)                                                     AS headcount,
    SUM(attrition = 'Yes')                                       AS leavers,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2)          AS attrition_pct,
    ROUND(AVG(years_at_company), 1)                              AS avg_tenure,
    ROUND(AVG(age), 1)                                           AS avg_age,
    ROUND(AVG(monthly_income), 0)                                AS avg_income
FROM employees
"""

# ----------------------------------------------------------------------
# Page 1 — Attrition Overview
# ----------------------------------------------------------------------

# Q2, rolled up to department.
ATTRITION_BY_DEPARTMENT = """
SELECT
    department,
    COUNT(*)                                            AS headcount,
    SUM(attrition = 'Yes')                              AS leavers,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY department
ORDER BY attrition_pct DESC
"""

# Q2 at job-role grain — this is where Sales Representative at 39.76% shows up.
ATTRITION_BY_ROLE = """
SELECT
    job_role,
    department,
    COUNT(*)                                            AS headcount,
    SUM(attrition = 'Yes')                              AS leavers,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY job_role, department
ORDER BY attrition_pct DESC
"""

# Q9. Ordered category, so the chart uses the ordinal ramp.
ATTRITION_BY_AGE = """
SELECT
    CASE
        WHEN age < 30 THEN 'Under 30'
        WHEN age < 40 THEN '30-39'
        WHEN age < 50 THEN '40-49'
        ELSE '50+'
    END                                                 AS age_group,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(age)
"""

# Q12. Worst role inside each department — the ranking a department head cares
# about, since 39.76% company-wide is not their number.
WORST_ROLE_PER_DEPARTMENT = """
WITH role_stats AS (
    SELECT
        department,
        job_role,
        COUNT(*)                                            AS headcount,
        ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
    FROM employees
    GROUP BY department, job_role
)
SELECT department, job_role, headcount, attrition_pct,
       RANK() OVER (PARTITION BY department ORDER BY attrition_pct DESC) AS risk_rank
FROM role_stats
ORDER BY department, risk_rank
"""

# ----------------------------------------------------------------------
# Page 2 — Risk Factors
# ----------------------------------------------------------------------

# Q3. The headline: the overtime multiple is computed from these two rows.
ATTRITION_BY_OVERTIME = """
SELECT
    over_time,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY over_time
ORDER BY over_time
"""

# Q5. NTILE(4) over income, not fixed salary bands — the quartile boundaries
# come from the data, and the recorded band edges (1,009-2,911 / 2,911-4,930 /
# 4,936-8,380 / 8,381-19,999) are what this returns.
ATTRITION_BY_INCOME_QUARTILE = """
WITH banded AS (
    SELECT *, NTILE(4) OVER (ORDER BY monthly_income) AS income_quartile
    FROM employees
)
SELECT
    income_quartile,
    MIN(monthly_income)                                 AS band_min,
    MAX(monthly_income)                                 AS band_max,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM banded
GROUP BY income_quartile
ORDER BY income_quartile
"""

# Q6. ORDER BY MIN(years_at_company) keeps the buckets in tenure order rather
# than alphabetical — '10+ yrs' would otherwise sort first and reverse the
# gradient the chart exists to show.
ATTRITION_BY_TENURE = """
SELECT
    CASE
        WHEN years_at_company <= 2  THEN '0-2 yrs'
        WHEN years_at_company <= 5  THEN '3-5 yrs'
        WHEN years_at_company <= 10 THEN '6-10 yrs'
        ELSE '10+ yrs'
    END                                                 AS tenure_bucket,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(years_at_company)
"""

# Q7. The full 4x4 grid, rendered as a heatmap. Cells are thin — the worst
# holds 17 employees — so the app prints the count alongside the rate.
WORK_LIFE_BALANCE_GRID = """
SELECT
    work_life_balance,
    job_satisfaction,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY work_life_balance, job_satisfaction
ORDER BY work_life_balance, job_satisfaction
"""

# Q8. Commute distance.
ATTRITION_BY_COMMUTE = """
SELECT
    CASE
        WHEN distance_from_home <= 5  THEN '0-5 km'
        WHEN distance_from_home <= 15 THEN '6-15 km'
        ELSE '15+ km'
    END                                                 AS commute_band,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(distance_from_home)
"""

# Q11. The compound cohort — overtime AND under 3,000 AND 3 years or less.
# The strongest finding in the dataset, and the smallest: 64 people.
COMPOUND_RISK_COHORT = """
WITH risk_cohort AS (
    SELECT *,
        CASE WHEN over_time = 'Yes'
              AND monthly_income < 3000
              AND years_at_company <= 3
             THEN 'Compound risk cohort' ELSE 'Everyone else' END AS profile
    FROM employees
)
SELECT
    profile,
    COUNT(*)                                            AS employees,
    ROUND(100.0 * SUM(attrition = 'Yes') / COUNT(*), 2) AS attrition_pct
FROM risk_cohort
GROUP BY profile
ORDER BY attrition_pct DESC
"""

# Q4. Income of leavers against stayers. Median as well as mean, because the
# income distribution is right-skewed and the two disagree by ~1,600.
INCOME_LEAVERS_VS_STAYERS = """
WITH ranked AS (
    SELECT attrition,
           monthly_income,
           ROW_NUMBER() OVER (PARTITION BY attrition ORDER BY monthly_income) AS rn,
           COUNT(*)     OVER (PARTITION BY attrition)                         AS cnt
    FROM employees
),
medians AS (
    SELECT attrition, ROUND(AVG(monthly_income), 0) AS median_monthly_income
    FROM ranked
    WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
    GROUP BY attrition
)
SELECT
    e.attrition,
    ROUND(AVG(e.monthly_income), 0) AS avg_monthly_income,
    m.median_monthly_income,
    COUNT(*)                        AS employees
FROM employees e
JOIN medians m ON m.attrition = e.attrition
GROUP BY e.attrition, m.median_monthly_income
ORDER BY e.attrition
"""

# ----------------------------------------------------------------------
# Page 3 — At-Risk Employees
# ----------------------------------------------------------------------
#
# This page sits on the risk CSV, not on `employees`. The CSV holds only the
# 1,233 employees whose attrition is 'No' — scoring the 237 who already left
# would be scoring a known outcome. A card reading 1,233 here and 1,470 on
# page 1 is correct, not a filter left on by accident, and the page says so.
