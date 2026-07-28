# Key numbers — IBM HR attrition

Every figure here came from an actual run on 2026-07-28. Cite these, not estimates.

Sources: `02_prediction_model.py` (stdout) and `attrition_analysis.sql`
(12 queries → `notes/query-results.txt`, zero MySQL errors).

## Dataset

| Metric | Value |
|---|---|
| Employee records | **1,470** |
| Attributes in the raw CSV | **35** |
| Dropped as constant | 3 — `EmployeeCount`, `StandardHours`, `Over18` |
| Loaded into `hr_analytics.employees` | 1,470 rows, snake_case columns |
| Leavers | 237 |
| **Overall attrition rate** | **16.12%** |

Python and SQL agree on the attrition rate — 16.1224% from
`value_counts(normalize=True)`, 16.12% from Q1. The double-quoted-identifier
trap did not occur; `attrition_analysis.sql` uses bare snake_case throughout.

## Model

| Metric | Value |
|---|---|
| Algorithm | Random Forest — 300 trees, `max_depth=10`, `class_weight='balanced'` |
| Split | 80/20 stratified, `random_state=42` (1,176 train / 294 test) |
| **ROC-AUC** | **0.774** |
| Accuracy | 0.82 — **do not quote this** |
| Precision / recall / F1 on leavers | 0.43 / 0.34 / 0.38 (47 in the test set) |
| Confusion matrix | `[[226, 21], [31, 16]]` |

⚠️ **Quote ROC-AUC, never accuracy.** With 16% attrition, "predict nobody
leaves" scores 84% accuracy — higher than this model's 82% — and is useless.
That gap is the reason the resume says ROC-AUC.

⚠️ **Recall on leavers is 0.34** — the model catches 16 of 47 actual leavers at
the default 0.5 threshold. Be ready for this: it is a screening aid that ranks
who to talk to, not a decision system. Lowering the threshold trades precision
for recall, and for a retention conversation that is usually the right trade.

### Top 10 attrition drivers (Gini importance)

| # | Feature | Importance |
|---|---|---|
| 1 | MonthlyIncome | 0.0744 |
| 2 | Age | 0.0621 |
| 3 | TotalWorkingYears | 0.0546 |
| 4 | **OverTime_Yes** | 0.0512 |
| 5 | YearsAtCompany | 0.0511 |
| 6 | DailyRate | 0.0493 |
| 7 | HourlyRate | 0.0438 |
| 8 | MonthlyRate | 0.0431 |
| 9 | YearsWithCurrManager | 0.0431 |
| 10 | DistanceFromHome | 0.0406 |

⚠️ **`DailyRate`, `HourlyRate` and `MonthlyRate` are noise — measured, not
assumed.** They are randomly generated filler in the IBM dataset. Correlation
with attrition:

| Feature | Corr | Leavers vs stayers |
|---|---|---|
| HourlyRate | −0.007 | 66 vs 66 — identical |
| MonthlyRate | +0.015 | 14,559 vs 14,266 |
| DailyRate | −0.057 | 750 vs 813 |
| *MonthlyIncome (real)* | *−0.160* | *4,787 vs 6,833* |
| *TotalWorkingYears (real)* | *−0.171* | — |

The three rate columns sit near zero while the genuine drivers are 3–10× stronger.
They rank high because Gini importance is biased toward high-cardinality
continuous features — a property of the metric, not a finding. Do not present
them as drivers. If asked, that bias is the answer and permutation importance is
the fix.

## Risk scores — scored out-of-fold

| Metric | Value |
|---|---|
| Current employees scored (`Attrition = No`) | **1,233** |
| High risk (p > 0.6) | **22** |
| Medium risk (0.3 < p ≤ 0.6) | **330** |
| Low risk (p ≤ 0.3) | 881 |
| Score range | 0.047 – 0.794 |
| Output | `outputs/employee_risk_scores.csv` |

**Why out-of-fold, and why this matters.** The script originally scored everyone
with `model.predict_proba(X)` — the same model fitted on 80% of them. Measured:

| | Employees | Mean score | Max | High risk |
|---|---|---|---|---|
| Seen in training | 986 | 0.172 | 0.566 | **0 (0.0%)** |
| Held out | 247 | 0.265 | 0.855 | **10 (4.0%)** |

Every "high-risk" employee came from the 247-row test slice and none from the
986 trained-on rows — not because those 986 were safe, but because the model had
memorised their `Attrition = No` label and never scored them above 0.566. The
list ranked who landed in which split. Scoring is now `cross_val_predict` with
5-fold stratified CV, so every employee is scored by a fold that never saw them
and the numbers are comparable across the whole population. High risk went
10 → 22, medium 131 → 330, drawn from all 1,233.

**Interview answer:** *"Scoring the training rows in-sample hides exactly the
people you want to find — the model has already seen their label, so their
probability collapses. I checked, and all ten of my high-risk employees were
coming from the held-out fifth. Out-of-fold prediction gives every employee an
honest score and the high-risk list more than doubled."*

## SQL findings

| Query | Finding | Value |
|---|---|---|
| Q1 | Overall attrition | **16.12%** — 237 of 1,470 |
| Q2 | Worst role | **Sales Representative — 39.76%** (33 of 83) |
| Q2 | Runners-up | Laboratory Technician 23.94% (259), HR 23.08% (52) |
| Q3 | **Overtime split** | **30.53% with overtime vs 10.44% without — 2.92×** (416 vs 1,054 employees) |
| Q4 | Income, leavers vs stayers | avg 4,787 vs 6,833; median 3,202 vs 5,204 |
| Q5 | Income quartile | **Q1 29.35% → Q4 10.35%**, monotonic (bands 1,009–2,911 / 2,911–4,930 / 4,936–8,380 / 8,381–19,999) |
| Q6 | **Tenure** | **0–2 yrs 29.82% → 10+ yrs 8.13%**, monotonic across all four buckets |
| Q7 | Worst work-life × satisfaction cell | WLB 1 × JobSat 1 — 47.06% (17 employees); best is WLB 3 × JobSat 4 — 7.22% (263) |
| Q8 | Commute | 0–5 km 13.77% → 15+ km 20.67% |
| Q9 | Age | **Under 30 — 27.91%** (326 employees) vs 40–49 at 9.74% |
| Q10 | Years since promotion | No clean gradient — 0 yrs 18.93%, 5 yrs 4.44%, 7 yrs 21.05% (groups under 20 excluded) |
| Q11 | **Compound risk cohort** | **65.63% vs 13.87% — 4.73×.** 64 employees who work overtime **and** earn under 3,000 **and** have ≤3 years tenure |
| Q12 | Worst role per department | Sales → Sales Rep 39.76%; R&D → Lab Technician 23.94%; HR → HR 23.08% |

### The three findings worth leading with

1. **The compound cohort is the headline.** Overtime + under-3,000 income + ≤3
   years tenure = 65.63% attrition against 13.87% for everyone else. It is only
   64 people, which is what makes it actionable — a retention budget aimed at 64
   named employees is a real intervention, not a policy paper.
2. **Overtime alone nearly triples attrition** — 30.53% vs 10.44%. It is the
   only top-5 model driver that HR can directly change; income, age and tenure
   are slower levers.
3. **Attrition is front-loaded and bottom-loaded.** Under-30s leave at 27.91%,
   0–2 year employees at 29.82%, bottom-quartile earners at 29.35% — and both
   the tenure and income gradients are monotonic, so this is a trend rather than
   a single bad bucket.

### Reconciliation

| Check | Result |
|---|---|
| Python attrition rate vs Q1 | 16.1224% vs 16.12% ✅ |
| CSV rows vs `employees` table | 1,470 loaded; 1,233 scored = 1,470 − 237 leavers ✅ |
| Risk bands sum | 22 + 330 + 881 = 1,233 ✅ |
| Q2 role headcounts sum | 83+259+52+326+292+145+131+54+37+80+11 = 1,470 ✅ |
| Q3 overtime split sum | 416 + 1,054 = 1,470 ✅ |
| Q6 tenure buckets sum | 342+434+448+246 = 1,470 ✅ |
| Q9 age groups sum | 326+622+349+173 = 1,470 ✅ |

### Notes on reading these

- Q10 excludes promotion-gap groups with fewer than 20 employees (`HAVING
  COUNT(*) >= 20`), so 8, 9 and 10 years are absent. Not missing data.
- `EmployeeNumber` is dropped before training — it is an ID, and leaving it in
  invites the model to memorise individuals.
- The risk CSV covers current employees only. Scoring the 237 who already left
  would be scoring a known outcome.
