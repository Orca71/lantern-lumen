-- =============================================
-- Matrix Query #05: Burn Rate & Runway
-- Measures: How fast the company is spending
-- cash and how many months until it runs out
-- =============================================

WITH monthly_revenue AS (
	SELECT
		STRFTIME('%Y-%m', issue_date) AS month,
		SUM(amount) AS revenue
	FROM invoices
	GROUP BY STRFTIME('%Y-%m', issue_date)
),
monthly_expenses AS (
	SELECT
		STRFTIME('%Y-%m', expense_date) AS month,
		SUM(amount) AS expenses
	FROM expenses
	GROUP BY STRFTIME('%Y-%m', expense_date)
),
monthly_burn AS (
	SELECT 
		r.month,
		r.revenue,
		e.expenses,
		ROUND(e.expenses - r.revenue, 2) AS burn_rate
	FROM monthly_revenue r
	JOIN monthly_expenses e ON r.month = e.month
),
latest_cash AS (
	SELECT cash_balance
	FROM cash_snapshot
	ORDER BY snapshot_date DESC
	LIMIT 1
)

SELECT
    mb.month,
    mb.revenue,
    mb.expenses,
    mb.burn_rate,
    CASE
        WHEN mb.burn_rate > 0 THEN 'Burning Cash'
        ELSE                       'Profitable'
    END                                         AS burn_status,
    lc.cash_balance                             AS current_cash,
    ROUND(
        lc.cash_balance / NULLIF(
            AVG(CASE WHEN mb.burn_rate > 0 
                THEN mb.burn_rate END) OVER ()
        , 0)
    , 1)                                        AS runway_months
FROM monthly_burn mb, latest_cash lc
ORDER BY mb.month;
	