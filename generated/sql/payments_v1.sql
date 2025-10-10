CREATE CATALOG IF NOT EXISTS ${CATALOG};
CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA};
USE ${CATALOG}.${SCHEMA};

-- Data Product: payments entity payments
CREATE TABLE IF NOT EXISTS payments_v1 (
  payment_id STRING NOT NULL,
  account_id STRING,
  bill_id STRING,
  amount STRING,
  currency STRING,
  method STRING,
  status STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) USING DELTA;

-- Data Product: payments entity bills
CREATE TABLE IF NOT EXISTS bills_v1 (
  bill_id STRING NOT NULL,
  account_id STRING,
  amount_due STRING,
  status STRING,
  bill_date DATE
) USING DELTA;
