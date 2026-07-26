"""
HR Attrition — EDA + Prediction Model
Author : Alok Kumar Ojha
Purpose: Explore attrition drivers, train a Random Forest classifier,
         and export per-employee risk scores for the Power BI dashboard.
Run    : python 02_prediction_model.py
Note   : Convert to a Jupyter Notebook with markdown commentary for GitHub.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
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
# ----------------------------------------------------------------------
engine = create_engine("mysql+pymysql://root:yourpassword@localhost:3306/hr_analytics")
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
# 7. EXPORT RISK SCORES FOR POWER BI
#    Score ALL current employees (Attrition = No) — the actionable list.
# ----------------------------------------------------------------------
df["attrition_probability"] = model.predict_proba(X)[:, 1].round(3)

risk_out = df.loc[df["Attrition"] == "No",
                  ["EmployeeNumber", "Department", "JobRole", "OverTime",
                   "MonthlyIncome", "YearsAtCompany", "attrition_probability"]]
risk_out["risk_band"] = pd.cut(risk_out["attrition_probability"],
                               bins=[0, 0.3, 0.6, 1.0],
                               labels=["Low", "Medium", "High"])
risk_out = risk_out.sort_values("attrition_probability", ascending=False)
risk_out.to_csv("outputs/employee_risk_scores.csv", index=False)

print(f"\n✅ Exported {len(risk_out)} employee risk scores "
      f"({(risk_out['risk_band'] == 'High').sum()} high-risk) "
      "→ outputs/employee_risk_scores.csv (use in Power BI page 3)")
