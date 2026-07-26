# 👥 HR Analytics — Employee Attrition Analysis & Prediction

**Tools:** Python (pandas, scikit-learn) · SQL · Power BI (DAX)

An end-to-end HR analytics project on the **IBM HR Analytics Employee Attrition** dataset (1,470 employees, 35 attributes). It combines descriptive analysis (SQL + pandas), a predictive model (Random Forest) that flags at-risk employees, and a Power BI dashboard that turns the findings into an HR action plan.

---

## 📌 Business Problem

Employee turnover is expensive. HR wants to know **which factors drive attrition** and **which current employees are most at risk of leaving**, so retention efforts can be targeted where they matter most.

---

## 🧰 Tools & Skills Demonstrated

| Layer | Tools / Skills |
|---|---|
| EDA & feature engineering | Python — pandas, seaborn, matplotlib |
| Predictive modeling | scikit-learn — Random Forest, train/test split, feature importance |
| Analysis | SQL — attrition rates by segment, salary & overtime analysis |
| Visualization | Power BI — DAX measures, risk table, what-if parameter |
| Version control | Git & GitHub |

---

## 🗂️ Project Structure

```
hr-attrition-analytics/
├── README.md
├── requirements.txt
├── data/
│   └── README.md                    # Dataset source & download steps
├── 02_prediction_model.py           # EDA + Random Forest + at-risk export
├── attrition_analysis.sql           # 12 attrition questions answered in SQL
└── powerbi/
    ├── dashboard.pbix               # (add your Power BI file here)
    └── screenshots/                 # Dashboard page previews (PNG)
```

---

## 🔄 Workflow

1. **Extract** — Download the IBM HR CSV from Kaggle (see `data/README.md`).
2. **EDA (Python)** — Explore attrition by department, overtime, income, tenure, and satisfaction; save charts as PNGs.
3. **Model (Python)** — One-hot encode categoricals, train a Random Forest classifier, evaluate (accuracy, precision/recall), and export each employee's predicted attrition probability to `at_risk_employees.csv`.
4. **Analyze (SQL)** — Load the data into a database and compute attrition rates across departments, roles, salary bands, and overtime status.
5. **Visualize (Power BI)** — Build a 3-page dashboard including a sortable at-risk employee table driven by the model's scores.

---

## 📊 Dashboard Pages

| Page | Contents |
|---|---|
| 1. Attrition Overview | Overall attrition %, headcount, department & role breakdown |
| 2. Risk Factors | Impact of overtime, monthly income, work-life balance, distance from home |
| 3. At-Risk Employees | Model probability scores as a sortable table + what-if salary-hike simulation |

> 📷 Add exported PNGs to `powerbi/screenshots/` and embed them here.

---

## 💡 Key Insights

<!-- TODO: replace with the real numbers from your own run BEFORE pushing -->
- _Pending — fill in after running the pipeline end-to-end._

---

## ▶️ How to Run

```bash
git clone https://github.com/Alok2525/hr-attrition-analytics.git
cd hr-attrition-analytics
pip install -r requirements.txt

# Download the dataset into data/ (see data/README.md), then:
python 02_prediction_model.py                   # EDA + model + risk scores
mysql -u root -p hr_analytics < attrition_analysis.sql   # run the analysis queries

# Open powerbi/dashboard.pbix and point it at the CSV / database
```

---

## 👤 Author

**Alok Kumar Ojha** — Data Analyst | Python · SQL · Power BI
Connect on [LinkedIn](https://linkedin.com/in/alok-kumar-ojha-450247176)
