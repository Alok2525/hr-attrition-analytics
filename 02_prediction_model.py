"""
HR Attrition — EDA + Prediction Model
Author : Alok Kumar Ojha
Purpose: Explore attrition drivers, train a Random Forest classifier, and
         export per-employee risk scores plus a salary-hike simulation for the
         dashboard.
Run    : python 02_prediction_model.py
"""

import os
from urllib.parse import quote_plus

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from sklearn.model_selection import (
    train_test_split, cross_val_predict, StratifiedKFold)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

# ----------------------------------------------------------------------
# 1. LOAD DATA
# ----------------------------------------------------------------------
df = pd.read_csv("data/WA_Fn-UseC_-HR-Employee-Attrition.csv")
print(df.shape)          # (1470, 35)
print(df["Attrition"].value_counts(normalize=True))   # ~16% Yes → imbalanced!

# Drop constant / ID columns that add no signal
df = df.drop(columns=["EmployeeCount", "StandardHours", "Over18"])

# ----------------------------------------------------------------------
# 2. EDA — key plots (save each as PNG for the repo)
# ----------------------------------------------------------------------
plt.figure(figsize=(8, 4))
sns.countplot(data=df, x="Department", hue="Attrition")
plt.title("Attrition by Department")
plt.tight_layout(); plt.savefig("outputs/attrition_by_department.png"); plt.close()

plt.figure(figsize=(6, 4))
sns.countplot(data=df, x="OverTime", hue="Attrition")
plt.title("Overtime vs Attrition")
plt.tight_layout(); plt.savefig("outputs/overtime_vs_attrition.png"); plt.close()

plt.figure(figsize=(8, 4))
sns.boxplot(data=df, x="Attrition", y="MonthlyIncome")
plt.title("Monthly Income: Leavers vs Stayers")
plt.tight_layout(); plt.savefig("outputs/income_vs_attrition.png"); plt.close()

# Attrition rate cross-tab (print for README insights)
print("\nAttrition rate by OverTime:")
print(df.groupby("OverTime")["Attrition"].apply(lambda s: (s == "Yes").mean().round(3)))

# ----------------------------------------------------------------------
# 3. LOAD INTO MYSQL (for SQL analysis file)
#    Credentials come from the environment — never hardcode them here.
#    export MYSQL_PASSWORD='...'   before running.
# ----------------------------------------------------------------------
DB_USER = os.environ.get("MYSQL_USER", "root")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD")
if not DB_PASSWORD:
    raise SystemExit("Set MYSQL_PASSWORD first:  export MYSQL_PASSWORD='...'")
DB_HOST = os.environ.get("MYSQL_HOST", "localhost")

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:3306/hr_analytics")
sql_df = df.copy()
sql_df.columns = (sql_df.columns
                  .str.replace(r"(?<!^)(?=[A-Z])", "_", regex=True)
                  .str.lower())              # MonthlyIncome -> monthly_income
sql_df.to_sql("employees", engine, if_exists="replace", index=False)
print(f"\nLoaded employees table: {len(sql_df):,} rows")

# ----------------------------------------------------------------------
# 4. FEATURE ENGINEERING FOR MODEL
# ----------------------------------------------------------------------
y = df["Attrition"].map({"Yes": 1, "No": 0})
X = pd.get_dummies(df.drop(columns=["Attrition", "EmployeeNumber"]), drop_first=True)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y   # stratify: keep 16% ratio
)

# ----------------------------------------------------------------------
# 5. TRAIN RANDOM FOREST
#    class_weight='balanced' handles the 84/16 class imbalance.
# ----------------------------------------------------------------------
model = RandomForestClassifier(
    n_estimators=300, max_depth=10,
    class_weight="balanced", random_state=42
)
model.fit(X_train, y_train)

y_pred  = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n", classification_report(y_test, y_pred))
print("ROC-AUC:", round(roc_auc_score(y_test, y_proba), 3))
print("Confusion matrix:\n", confusion_matrix(y_test, y_pred))

# ----------------------------------------------------------------------
# 6. FEATURE IMPORTANCE — what actually drives attrition
# ----------------------------------------------------------------------
imp = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop 10 attrition drivers:\n", imp.head(10))

plt.figure(figsize=(8, 5))
imp.head(10).sort_values().plot(kind="barh", color="#c0392b")
plt.title("Top 10 Attrition Drivers (Feature Importance)")
plt.tight_layout(); plt.savefig("outputs/feature_importance.png"); plt.close()

# ----------------------------------------------------------------------
# 7. EXPORT RISK SCORES
#    Score ALL current employees (Attrition = No) — the actionable list.
#
#    Scored out-of-fold, not with the model above. Reusing `model` here would
#    score the 80% it was trained on in-sample: it has memorised their
#    Attrition = No label and pushes their probability down, so they never
#    cross a risk threshold. Measured on this dataset, that put all 10
#    "high-risk" employees inside the 247-row test slice and none in the 986
#    trained-on rows — a ranking of who landed in which split, not of who is
#    at risk. cross_val_predict gives every employee a prediction from a fold
#    that never saw them, so the scores are comparable across the population.
# ----------------------------------------------------------------------
oof_proba = cross_val_predict(
    RandomForestClassifier(n_estimators=300, max_depth=10,
                           class_weight="balanced", random_state=42),
    X, y,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    method="predict_proba",
)[:, 1]
df["attrition_probability"] = oof_proba.round(3)

risk_out = df.loc[df["Attrition"] == "No",
                  ["EmployeeNumber", "Department", "JobRole", "OverTime",
                   "MonthlyIncome", "YearsAtCompany", "attrition_probability"]]
risk_out["risk_band"] = pd.cut(risk_out["attrition_probability"],
                               bins=[0, 0.3, 0.6, 1.0],
                               labels=["Low", "Medium", "High"])
risk_out = risk_out.sort_values("attrition_probability", ascending=False)

# Export snake_case, matching the MySQL employees table and hike_simulation.csv.
# The six selected columns come straight from the source DataFrame and were
# CamelCase; a consumer joining on EmployeeNumber vs employee_number matches
# nothing and fails silently — Power BI renders an empty table, no error.
risk_out.columns = (risk_out.columns
                    .str.replace(r"(?<!^)(?=[A-Z])", "_", regex=True)
                    .str.lower())
risk_out.to_csv("outputs/employee_risk_scores.csv", index=False)

print(f"\n✅ Exported {len(risk_out)} employee risk scores, scored out-of-fold "
      f"({(risk_out['risk_band'] == 'High').sum()} high-risk, "
      f"{(risk_out['risk_band'] == 'Medium').sum()} medium) "
      "→ outputs/employee_risk_scores.csv")

# ----------------------------------------------------------------------
# 8. WHAT-IF: SALARY-HIKE SIMULATION
#    The question the dashboard asks: if we raised everyone's pay by H%,
#    what would the model predict then?
#
#    This is a real re-prediction, not a linear approximation. The intervention
#    is a change to the *input* (MonthlyIncome), so the models are fitted once
#    on the observed data and then asked about the counterfactual. Refitting on
#    hiked salaries would answer a different question — what a world where
#    everyone already earned more looks like — and would let the target leak
#    back into the model through the very feature being changed.
#
#    Each employee is still scored by a fold that never saw them, so the H=0
#    column must reproduce section 7's out-of-fold scores exactly. That
#    equality is asserted below rather than assumed.
#
#    Only MonthlyIncome moves. PercentSalaryHike is last year's raise, a
#    different quantity; DailyRate/HourlyRate/MonthlyRate are random filler in
#    this dataset (see notes/key-numbers.md) and carry no salary signal.
# ----------------------------------------------------------------------
HIKE_LEVELS = [0, 5, 10, 15, 20, 25, 30]

folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
sim = pd.DataFrame(index=X.index, columns=HIKE_LEVELS, dtype=float)

for train_idx, test_idx in folds.split(X, y):
    fold_model = RandomForestClassifier(
        n_estimators=300, max_depth=10,
        class_weight="balanced", random_state=42
    ).fit(X.iloc[train_idx], y.iloc[train_idx])

    held_out = X.iloc[test_idx]
    for hike in HIKE_LEVELS:
        counterfactual = held_out.copy()
        counterfactual["MonthlyIncome"] = counterfactual["MonthlyIncome"] * (1 + hike / 100)
        sim.loc[held_out.index, hike] = fold_model.predict_proba(counterfactual)[:, 1]

# The H=0 column and section 7's scores come from the same folds and the same
# seed, so they must agree. If they ever stop agreeing, the two are no longer
# describing the same model and the simulation is meaningless.
assert np.allclose(sim[0], oof_proba), "H=0 does not reproduce the out-of-fold scores"

sim_current = sim.loc[df["Attrition"] == "No"].round(3)
sim_current.insert(0, "employee_number",
                   df.loc[sim_current.index, "EmployeeNumber"].values)
sim_out = (sim_current
           .melt(id_vars="employee_number",
                 var_name="hike_pct", value_name="attrition_probability")
           .sort_values(["employee_number", "hike_pct"]))
sim_out.to_csv("outputs/hike_simulation.csv", index=False)

baseline = sim.loc[df["Attrition"] == "No", 0]
topmost = sim.loc[df["Attrition"] == "No", HIKE_LEVELS[-1]]
print(f"\n✅ Simulated {len(HIKE_LEVELS)} salary-hike levels for {len(baseline):,} "
      f"current employees → outputs/hike_simulation.csv")
print(f"   Mean predicted risk: {baseline.mean():.3f} at +0%  →  "
      f"{topmost.mean():.3f} at +{HIKE_LEVELS[-1]}%")
print(f"   High risk (p > 0.6): {(baseline > 0.6).sum()} at +0%  →  "
      f"{(topmost > 0.6).sum()} at +{HIKE_LEVELS[-1]}%")
