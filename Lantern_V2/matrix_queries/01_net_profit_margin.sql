WITH revenue AS (
	SELECT SUM(amount) AS total_revenue
	FROM invoices),
cost AS (
	SELECT SUM(amount) AS total_expenses 
	FROM expenses)
	
SELECT 
	total_revenue,
	ROUND(total_expenses, 2) AS total_expenses, 
	ROUND(total_revenue - total_expenses, 2) AS net_profit,
	ROUND((total_revenue - total_expenses) / NULLIF(total_revenue, 0) * 100, 2) AS net_profit_margin_pct
FROM revenue , cost; 
	

