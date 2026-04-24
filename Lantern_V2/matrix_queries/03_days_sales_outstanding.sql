-- =============================================
-- Matrix Query #03: Days Sales Outstanding
-- Measures: How long on average it takes
-- clients to pay invoices
-- =============================================

WITH paid_invoices AS (
	SELECT 
		invoice_id,
		client_id,
		issue_date,
		paid_date,
		JULIANDAY(paid_date) - JULIANDAY(issue_date) AS days_to_collect
	FROM invoices
	WHERE paid_date IS NOT NULL
),
dso_by_client AS (
	SELECT 
		c.client_name,
		COUNT(p.invoice_id) AS invoices_paid,
		ROUND(AVG(p.days_to_collect), 1) AS avg_days_to_pay
	FROM paid_invoices p
	JOIN clients c ON p.client_id = c.client_id 
	GROUP BY c.client_name 
)

SELECT 
	client_name,
	invoices_paid,
	avg_days_to_pay,
	CASE
		WHEN avg_days_to_pay < 30 THEN 'Excellent'
		WHEN avg_days_to_pay < 45 THEN 'Healthy'
		WHEN avg_days_to_pay < 60 THEN 'Concerning'
		ELSE 'Dangerous'
	END AS dso_status,
	ROUND(AVG(avg_days_to_pay) OVER (), 1) AS company_avg_dso
FROM dso_by_client 
ORDER BY avg_days_to_pay DESC; 
	
	
	