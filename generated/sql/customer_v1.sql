CREATE CATALOG IF NOT EXISTS ${CATALOG};
CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA};
USE ${CATALOG}.${SCHEMA};

-- Data Product: customer entity customer_profile
CREATE TABLE IF NOT EXISTS customer_profile_v1 (
  customer_id STRING NOT NULL,
  full_name STRING,
  primary_email STRING,
  phone STRING,
  country STRING,
  segment STRING,
  status STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) USING DELTA;

-- Data Product: customer entity customer_accounts
CREATE TABLE IF NOT EXISTS customer_accounts_v1 (
  account_id STRING NOT NULL,
  customer_id STRING,
  plan_code STRING,
  billing_cycle_day INT,
  status STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) USING DELTA;

-- Data Product: customer entity customer_subscriptions
CREATE TABLE IF NOT EXISTS customer_subscriptions_v1 (
  subscription_id STRING NOT NULL,
  account_id STRING,
  product_id STRING,
  status STRING,
  start_date DATE,
  end_date DATE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) USING DELTA;
