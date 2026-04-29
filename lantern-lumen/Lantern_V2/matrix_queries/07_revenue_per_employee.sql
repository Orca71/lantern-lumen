-- =============================================
-- Matrix Query #07: Revenue per Employee
-- Measures: How efficiently the team
-- generates revenue relative to headcount
-- Benchmarks (consulting):
-- Above $150k = Excellent
-- $100k-150k  = Healthy
-- Below $100k = Concerning
-- =============================================

WITH total_rev AS (
    SELECT SUM(amount) AS total_revenue
    FROM invoices
),
headcount AS (
    SELECT COUNT(*) AS active_employees
    FROM employees
    WHERE end_date IS NULL
)

SELECT
    tr.total_revenue,
    hc.active_employees,
    ROUND(
        tr.total_revenue / NULLIF(hc.active_employees, 0)
    , 2)                                        AS revenue_per_employee,
    CASE
        WHEN tr.total_revenue / NULLIF(hc.active_employees, 0) > 150000
            THEN 'Excellent'
        WHEN tr.total_revenue / NULLIF(hc.active_employees, 0) > 100000
            THEN 'Healthy'
        ELSE
            'Concerning — revenue may not justify headcount'
    END                                         AS efficiency_status
FROM total_rev tr, headcount hc;