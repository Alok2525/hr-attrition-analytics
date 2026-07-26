-- ============================================================
-- HR ANALYTICS — EMPLOYEE ATTRITION ANALYSIS
-- 12 Business Questions — MySQL 8.0
-- Table: employees (IBM HR dataset, 1,470 rows)
-- ============================================================


-- ------------------------------------------------------------
-- Q1. Overall Attrition Rate
-- ------------------------------------------------------------
SELECT
    COUNT(*)                                                          AS total_employees,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)                AS leavers,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees;


-- ------------------------------------------------------------
-- Q2. Attrition by Department & Job Role
-- Business use: locate the bleeding — which teams lose people
-- ------------------------------------------------------------
SELECT
    department,
    job_role,
    COUNT(*)                                                          AS headcount,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)                AS leavers,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY department, job_role
ORDER BY attrition_pct DESC;


-- ------------------------------------------------------------
-- Q3. Overtime Impact on Attrition (KEY INSIGHT)
-- ------------------------------------------------------------
SELECT
    over_time,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY over_time;


-- ------------------------------------------------------------
-- Q4. Salary Comparison — Leavers vs Stayers
-- ------------------------------------------------------------
-- MySQL has no PERCENTILE_CONT, so the median comes from the middle row(s)
-- of each group using ROW_NUMBER() + COUNT() window functions.
WITH ranked AS (
    SELECT attrition,
           monthly_income,
           ROW_NUMBER() OVER (PARTITION BY attrition ORDER BY monthly_income) AS rn,
           COUNT(*)     OVER (PARTITION BY attrition)                        AS cnt
    FROM employees
),
medians AS (
    SELECT attrition,
           ROUND(AVG(monthly_income), 0) AS median_monthly_income
    FROM ranked
    WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
    GROUP BY attrition
)
SELECT
    e.attrition,
    ROUND(AVG(e.monthly_income), 0)    AS avg_monthly_income,
    m.median_monthly_income,
    MIN(e.monthly_income)              AS min_income,
    MAX(e.monthly_income)              AS max_income
FROM employees e
JOIN medians m ON m.attrition = e.attrition
GROUP BY e.attrition, m.median_monthly_income;


-- ------------------------------------------------------------
-- Q5. Attrition by Income Quartile (window function)
-- ------------------------------------------------------------
WITH banded AS (
    SELECT *,
           NTILE(4) OVER (ORDER BY monthly_income) AS income_quartile
    FROM employees
)
SELECT
    income_quartile,
    MIN(monthly_income) AS band_min,
    MAX(monthly_income) AS band_max,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2) AS attrition_pct
FROM banded
GROUP BY income_quartile
ORDER BY income_quartile;


-- ------------------------------------------------------------
-- Q6. Tenure Buckets — when do people leave?
-- ------------------------------------------------------------
SELECT
    CASE
        WHEN years_at_company <= 2  THEN '0–2 yrs'
        WHEN years_at_company <= 5  THEN '3–5 yrs'
        WHEN years_at_company <= 10 THEN '6–10 yrs'
        ELSE '10+ yrs'
    END                                                               AS tenure_bucket,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(years_at_company);


-- ------------------------------------------------------------
-- Q7. Work-Life Balance & Job Satisfaction Impact
-- (1 = Low, 4 = Very High)
-- ------------------------------------------------------------
SELECT
    work_life_balance,
    job_satisfaction,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY work_life_balance, job_satisfaction
ORDER BY attrition_pct DESC;


-- ------------------------------------------------------------
-- Q8. Distance from Home Effect
-- ------------------------------------------------------------
SELECT
    CASE
        WHEN distance_from_home <= 5  THEN '0–5 km'
        WHEN distance_from_home <= 15 THEN '6–15 km'
        ELSE '15+ km'
    END                                                               AS commute_band,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(distance_from_home);


-- ------------------------------------------------------------
-- Q9. Age Group Analysis
-- ------------------------------------------------------------
SELECT
    CASE
        WHEN age < 30 THEN 'Under 30'
        WHEN age < 40 THEN '30–39'
        WHEN age < 50 THEN '40–49'
        ELSE '50+'
    END                                                               AS age_group,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY 1
ORDER BY MIN(age);


-- ------------------------------------------------------------
-- Q10. Years Since Last Promotion vs Attrition
-- Business use: is stagnation pushing people out?
-- ------------------------------------------------------------
SELECT
    years_since_last_promotion,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM employees
GROUP BY years_since_last_promotion
HAVING COUNT(*) >= 20            -- ignore tiny groups
ORDER BY years_since_last_promotion;


-- ------------------------------------------------------------
-- Q11. Compound Risk Profile: Overtime + Low Income + Short Tenure
-- Business use: define the highest-risk cohort for HR action
-- ------------------------------------------------------------
WITH risk_cohort AS (
    SELECT *,
        CASE WHEN over_time = 'Yes'
              AND monthly_income < 3000
              AND years_at_company <= 3
             THEN 'High Risk Profile' ELSE 'Others' END AS profile
    FROM employees
)
SELECT
    profile,
    COUNT(*)                                                          AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                              AS attrition_pct
FROM risk_cohort
GROUP BY profile;


-- ------------------------------------------------------------
-- Q12. Attrition Ranking of Job Roles Within Each Department
-- (window function: RANK)
-- ------------------------------------------------------------
WITH role_stats AS (
    SELECT
        department,
        job_role,
        ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)
              / COUNT(*), 2) AS attrition_pct
    FROM employees
    GROUP BY department, job_role
)
SELECT
    department,
    job_role,
    attrition_pct,
    RANK() OVER (PARTITION BY department ORDER BY attrition_pct DESC) AS risk_rank
FROM role_stats
ORDER BY department, risk_rank;
