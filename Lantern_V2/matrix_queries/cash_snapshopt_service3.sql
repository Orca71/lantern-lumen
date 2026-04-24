INSERT INTO cash_snapshot (snapshot_date, cash_balance, accounts_receivable, accounts_payable)
VALUES
('2025-01-31', 120000, 22000, 8000),
('2025-02-28', 112000, 24000, 8500),
('2025-03-31', 104000, 26000, 9000),
('2025-04-30', 95000,  28000, 9500),
('2025-05-31', 87000,  30000, 10000),
('2025-06-30', 79000,  32000, 10500),
('2025-07-31', 71000,  34000, 11000),
('2025-08-31', 63000,  36000, 11500),
('2025-09-30', 52000,  40000, 12000),
('2025-10-31', 43000,  44000, 12500),
('2025-11-30', 35000,  48000, 13000),
('2025-12-31', 28000,  52000, 13500);


SELECT category, COUNT(*) as entries, SUM(amount) as total
FROM expenses
GROUP BY category
ORDER BY total DESC;


SELECT 
    snapshot_date,
    cash_balance,
    ROUND(cash_balance * 1.0 / (SELECT SUM(amount)/12 FROM expenses), 1) as runway_months
FROM cash_snapshot
ORDER BY snapshot_date;