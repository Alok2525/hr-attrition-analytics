# Dataset

This project uses the **IBM HR Analytics Employee Attrition & Performance** dataset.

Download from Kaggle: https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset

Place this file in this `data/` folder:

- WA_Fn-UseC_-HR-Employee-Attrition.csv

`02_prediction_model.py` writes its model output to `../outputs/` — the per-employee
risk scores the dashboard's third page reads, and the salary-hike simulation behind
its what-if. Raw and generated CSVs are kept out of version control by `.gitignore`.
