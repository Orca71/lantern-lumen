-- =============================================
-- Matrix Query #06: Expense Breakdown
-- Measures: Cost structure and whether
-- any category is disproportionately high
-- =============================================

WITH total_cost AS (
    SELECT SUM(amount) AS total_expenses
    FROM expenses
),
by_category AS (
    SELECT
        category,
        COUNT(*)            AS entries,
        SUM(amount)         AS category_total
    FROM expenses
    GROUP BY category
)

SELECT
    bc.category,
    bc.entries,
    ROUND(bc.category_total, 2)                 AS category_total,
    ROUND(
        bc.category_total / NULLIF(tc.total_expenses, 0) * 100
    , 2)                                        AS pct_of_expenses,
    CASE
        WHEN bc.category = 'Payroll'
            AND bc.category_total / NULLIF(tc.total_expenses, 0) * 100 > 70
            THEN 'High — review headcount'
        WHEN bc.category = 'Rent'
            AND bc.category_total / NULLIF(tc.total_expenses, 0) * 100 > 15
            THEN 'High — consider renegotiating'
        WHEN bc.category = 'Marketing'
            AND bc.category_total / NULLIF(tc.total_expenses, 0) * 100 < 5
            THEN 'Low — may limit growth'
        ELSE 'Normal'
    END                                         AS flag
FROM by_category bc, total_cost tc
ORDER BY bc.category_total DESC;