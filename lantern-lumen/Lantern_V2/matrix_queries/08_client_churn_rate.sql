-- =============================================
-- Matrix Query #08: Client Churn Rate
-- Measures: Client and revenue loss during
-- the period and net revenue impact
-- =============================================

WITH client_counts AS (
    SELECT
        COUNT(*)                                AS total_clients,
        SUM(CASE WHEN status = 'churned'
            THEN 1 ELSE 0 END)                  AS churned_clients,
        SUM(CASE WHEN status = 'active'
            THEN 1 ELSE 0 END)                  AS active_clients
    FROM clients
),
total_rev AS (
    SELECT SUM(amount) AS total_revenue
    FROM invoices
),
churned_revenue AS (
    SELECT
        COALESCE(SUM(i.amount), 0)              AS lost_revenue
    FROM clients c
    LEFT JOIN invoices i ON c.client_id = i.client_id
    WHERE c.status = 'churned'
),
new_client_revenue AS (
    SELECT
        COALESCE(SUM(i.amount), 0)              AS new_revenue
    FROM clients c
    LEFT JOIN invoices i ON c.client_id = i.client_id
    WHERE STRFTIME('%Y', c.acquired_date) = '2023'
       OR STRFTIME('%Y', c.acquired_date) = '2024'
       OR STRFTIME('%Y', c.acquired_date) = '2025'
),
churned_detail AS (
    SELECT
        c.client_name,
        c.industry,
        COALESCE(SUM(i.amount), 0)              AS client_revenue
    FROM clients c
    LEFT JOIN invoices i ON c.client_id = i.client_id
    WHERE c.status = 'churned'
    GROUP BY c.client_name, c.industry
)

SELECT
    -- Client churn metrics
    cc.total_clients,
    cc.active_clients,
    cc.churned_clients,
    ROUND(
        cc.churned_clients * 100.0 
        / NULLIF(cc.total_clients, 0)
    , 2)                                        AS client_churn_pct,
    CASE
        WHEN cc.churned_clients * 100.0 
            / NULLIF(cc.total_clients, 0) < 10
            THEN 'Healthy'
        WHEN cc.churned_clients * 100.0 
            / NULLIF(cc.total_clients, 0) < 25
            THEN 'Concerning'
        ELSE 'Dangerous'
    END                                         AS client_churn_status,

    -- Revenue churn metrics
    ROUND(cr.lost_revenue, 2)                   AS lost_revenue,
    ROUND(
        cr.lost_revenue * 100.0 
        / NULLIF(tr.total_revenue, 0)
    , 2)                                        AS revenue_churn_pct,
    CASE
        WHEN cr.lost_revenue * 100.0 
            / NULLIF(tr.total_revenue, 0) < 10
            THEN 'Healthy'
        WHEN cr.lost_revenue * 100.0 
            / NULLIF(tr.total_revenue, 0) < 25
            THEN 'Concerning'
        ELSE 'Dangerous'
    END                                         AS revenue_churn_status,

    -- Replacement rate
    ROUND(ncr.new_revenue, 2)                   AS new_client_revenue,
    ROUND(
        ncr.new_revenue * 100.0 
        / NULLIF(tr.total_revenue, 0)
    , 2)                                        AS replacement_rate_pct,

    -- Net revenue impact
    ROUND(
        (cr.lost_revenue - ncr.new_revenue) * 100.0 
        / NULLIF(tr.total_revenue, 0)
    , 2)                                        AS net_revenue_impact_pct,
    CASE
        WHEN cr.lost_revenue <= ncr.new_revenue
            THEN 'Recovered — new clients offset losses'
        ELSE 'Not Recovered — net revenue loss'
    END                                         AS recovery_status,

    -- Churned client detail
    cd.client_name                              AS churned_client,
    cd.industry                                 AS churned_industry,
    ROUND(cd.client_revenue, 2)                 AS churned_client_revenue

FROM client_counts cc, total_rev tr, 
     churned_revenue cr, new_client_revenue ncr
LEFT JOIN churned_detail cd ON 1=1
ORDER BY cd.client_revenue DESC;