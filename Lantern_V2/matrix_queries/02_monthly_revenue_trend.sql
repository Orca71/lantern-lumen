-- =============================================
-- Matrix Query #02: Monthly Revenue Trend
-- Measures: Month over month revenue growth
-- and whether the business is growing or declining
-- =============================================


WITH monthly_revenue AS (
	SELECT
		STRFTIME('%Y-%m', issue_date) AS month,
		SUM(amount) AS monthly_revenue
	FROM invoices 
	GROUP BY STRFTIME('%Y-%m', issue_date)
),

with_growth AS (
		SELECT 
			month,
			monthly_revenue,
			LAG(monthly_revenue) OVER (ORDER BY MONTH) AS prev_month_revenue
		FROM monthly_revenue
)
SELECT
    month,
    monthly_revenue,
    prev_month_revenue,
    ROUND(monthly_revenue - prev_month_revenue, 2) AS revenue_change,
    ROUND(
        (monthly_revenue - prev_month_revenue)
        / NULLIF(prev_month_revenue, 0) * 100
    , 2)                                           AS mom_growth_pct
FROM with_growth
ORDER BY month;