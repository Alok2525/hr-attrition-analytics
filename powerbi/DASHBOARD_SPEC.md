# Power BI Dashboard — Build Spec

Everything needed to build `dashboard.pbix` in Power BI Desktop.

---

## 1. Connect — two sources

| Source | What | Column casing |
|---|---|---|
| **MySQL** `hr_analytics` → table `employees` | All 1,470 employees, 32 columns | `snake_case` (`monthly_income`) |
| **CSV** `outputs/employee_risk_scores.csv` | Model risk scores, current employees only | `CamelCase` (`MonthlyIncome`) |

⚠️ The casing differs because `02_prediction_model.py` snake-cases columns for MySQL but
exports the CSV from the original DataFrame. Rename the CSV columns to snake_case in
Power Query (**Transform data → right-click column → Rename**) so both tables match.

Run the script first — it creates both the MySQL table and the CSV:

```bash
python 02_prediction_model.py
```

---

## 2. Relationship

| From (1) | To (many) | Key |
|---|---|---|
| `employees` | `risk_scores` | `employee_number` |

Single direction, `employees` → `risk_scores`.

> `risk_scores` only holds employees where `attrition = 'No'` (the actionable list), so
> this is intentionally a subset. Page 3 visuals should sit on `risk_scores`, not
> `employees`.

---

## 3. DAX measures

Create a blank `_Measures` table and add:

### Attrition core

```dax
Headcount = COUNTROWS ( employees )

Leavers =
CALCULATE ( COUNTROWS ( employees ), employees[attrition] = "Yes" )

Attrition % = DIVIDE ( [Leavers], [Headcount] )

Retained = [Headcount] - [Leavers]
```

### Segment comparisons

```dax
Avg Monthly Income = AVERAGE ( employees[monthly_income] )

Avg Tenure = AVERAGE ( employees[years_at_company] )

Avg Age = AVERAGE ( employees[age] )

Attrition % — Overtime =
CALCULATE ( [Attrition %], employees[over_time] = "Yes" )

Attrition % — No Overtime =
CALCULATE ( [Attrition %], employees[over_time] = "No" )

Overtime Risk Multiple =
DIVIDE ( [Attrition % — Overtime], [Attrition % — No Overtime] )
```

`Overtime Risk Multiple` is the headline number for Page 2 — it quantifies how many times
more likely overtime employees are to leave.

### Income band (calculated column on `employees`)

```dax
income_band =
SWITCH (
    TRUE (),
    employees[monthly_income] < 3000,  "1. < 3k",
    employees[monthly_income] < 6000,  "2. 3k-6k",
    employees[monthly_income] < 10000, "3. 6k-10k",
    "4. 10k+"
)
```

### Tenure bucket (calculated column on `employees`)

```dax
tenure_bucket =
SWITCH (
    TRUE (),
    employees[years_at_company] <= 2,  "0-2 yrs",
    employees[years_at_company] <= 5,  "3-5 yrs",
    employees[years_at_company] <= 10, "6-10 yrs",
    "10+ yrs"
)
```

### Model risk

```dax
Employees Scored = COUNTROWS ( risk_scores )

High Risk Count =
CALCULATE ( COUNTROWS ( risk_scores ), risk_scores[risk_band] = "High" )

High Risk % = DIVIDE ( [High Risk Count], [Employees Scored] )

Avg Risk Score = AVERAGE ( risk_scores[attrition_probability] )
```

---

## 4. What-if: salary-hike simulation (Page 3)

**Modeling → New parameter → Numeric range**

- Name: `Salary Hike %`
- Min 0, Max 30, Increment 5, Default 0

This creates a `Salary Hike %` table with a `Salary Hike % Value` measure. Then add:

```dax
Simulated Income =
AVERAGE ( risk_scores[monthly_income] ) * ( 1 + 'Salary Hike %'[Salary Hike % Value] / 100 )

Est. Risk After Hike =
-- Income sits in the top handful of feature importances, so a hike lowers predicted
-- risk. This is a directional what-if for the dashboard, NOT a model re-prediction.
VAR HikePct   = 'Salary Hike %'[Salary Hike % Value] / 100
VAR Sensitivity = 0.4   -- tune from your feature-importance output
RETURN
MAX ( 0, [Avg Risk Score] * ( 1 - HikePct * Sensitivity ) )
```

> Be honest about this in the interview: it's a **linear sensitivity approximation**, not
> the Random Forest re-scoring itself. If asked how to do it properly — re-run
> `predict_proba` with `MonthlyIncome` scaled up and export a second CSV per hike level.
> Knowing that distinction is what separates you from someone who just copied a tutorial.

---

## 5. Pages

### Page 1 — Attrition Overview
| Visual | Fields |
|---|---|
| Cards | `Headcount`, `Leavers`, `Attrition %`, `Avg Tenure` |
| Bar chart | Axis `employees[department]`, Values `Attrition %` |
| Bar chart (sorted desc) | Axis `employees[job_role]`, Values `Attrition %` |
| Donut | Legend `employees[attrition]`, Values `Headcount` |
| Slicers | `employees[department]`, `employees[gender]` |

### Page 2 — Risk Factors
| Visual | Fields |
|---|---|
| Card (large) | `Overtime Risk Multiple` — title it "Overtime employees leave Nx more often" |
| Clustered column | Axis `employees[over_time]`, Values `Attrition %` |
| Column chart | Axis `employees[income_band]`, Values `Attrition %` |
| Column chart | Axis `employees[tenure_bucket]`, Values `Attrition %` |
| Line chart | Axis `employees[work_life_balance]`, Values `Attrition %` |
| Column chart | Axis `employees[distance_from_home]` (binned), Values `Attrition %` |

### Page 3 — At-Risk Employees
| Visual | Fields |
|---|---|
| Cards | `Employees Scored`, `High Risk Count`, `High Risk %` |
| **Table** (sort by risk desc) | `employee_number`, `department`, `job_role`, `over_time`, `monthly_income`, `years_at_company`, `attrition_probability`, `risk_band` |
| Conditional formatting | Data bars on `attrition_probability`; colour `risk_band` red/amber/green |
| Slicer | `risk_scores[risk_band]` |
| What-if slicer | `Salary Hike %` |
| Cards | `Simulated Income`, `Est. Risk After Hike` |

---

## 6. Before you commit

1. Export all 3 pages → `powerbi/screenshots/page1_overview.png`, `page2_risk_factors.png`, `page3_at_risk.png`
2. Embed the PNGs in the main `README.md`
3. Fill the **Key Insights** section with the real numbers from your own run —
   `02_prediction_model.py` prints the attrition rate, ROC-AUC and top-10 drivers
4. Save `dashboard.pbix` into `powerbi/`

### Numbers your script prints that belong in the README

| From the script output | Goes in README as |
|---|---|
| `df["Attrition"].value_counts(normalize=True)` | Overall attrition rate |
| `Attrition rate by OverTime` | The overtime multiple |
| `ROC-AUC:` | Model performance — **use this, not accuracy** (the classes are 84/16 imbalanced) |
| `Top 10 attrition drivers` | Which features actually matter |
| `Exported N employee risk scores (M high-risk)` | Size of the actionable list |
