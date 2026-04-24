-- =============================================
-- Matrix Query #04: Client Concentration Risk
-- Measures: How dependent the business is
-- on any single client for revenue
-- =============================================

WITH total_rev AS (
	SELECT SUM(amount) AS total_revenue
	FROM invoices
),
client_rev AS (
	SELECT
		c.client_name,
		c.status,
		SUM(i.amount) AS client_revenue,
		COUNT(i.invoice_id) AS invoice_count
	FROM invoices i
	JOIN clients c ON i.client_id = c.client_id 
	GROUP BY c.client_name , c.status
)

SELECT 
	cr.client_name, 
	cr.status,
	cr.invoice_count,
	cr.client_revenue,
	ROUND(
		cr.client_revenue / NULLIF(tr.total_revenue, 0) * 100, 2) AS revenue_pct,
	CASE 
		WHEN cr.client_revenue / NULLIF(tr.total_revenue, 0) * 100 < 25
			THEN 'Safe'
		WHEN cr.client_revenue / NULLIF(tr.total_revenue, 0) * 100 < 50
			THEN 'Concerning'
		ELSE 
			'Dangerous'
	END AS concentration_risk, tr.total_revenue
FROM client_rev cr , total_rev tr
ORDER BY cr.client_revenue 	desc; 
	