-- 本例表名：master、diseases、measurements；Notebook09使用SQLite。
-- 先聚合，再按患者连接，不直接将两张一对多原表互相展开。
WITH disease_counts AS (
    SELECT Patient_ID, COUNT(*) AS n_disease_records
    FROM diseases GROUP BY Patient_ID
), measurement_counts AS (
    SELECT Patient_ID, COUNT(*) AS n_measurement_records
    FROM measurements GROUP BY Patient_ID
)
SELECT p.Patient_ID, p.Age_At_2024,
       COALESCE(d.n_disease_records, 0) AS n_disease_records,
       COALESCE(m.n_measurement_records, 0) AS n_measurement_records
FROM master AS p
LEFT JOIN disease_counts AS d ON p.Patient_ID = d.Patient_ID
LEFT JOIN measurement_counts AS m ON p.Patient_ID = m.Patient_ID
ORDER BY p.Patient_ID;
