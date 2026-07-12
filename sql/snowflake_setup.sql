-- ============================================================
-- AQI Hackathon: Snowflake Medallion Architecture Setup
-- Bronze (raw) -> Silver (clean) -> Gold (analytics)
-- ============================================================

CREATE DATABASE IF NOT EXISTS AQI_HACKATHON;
USE DATABASE AQI_HACKATHON;

CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- ------------------------------------------------------------
-- BRONZE LAYER: Raw IoT sensor data (as-is, no cleaning)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS BRONZE_IOT_READINGS (
    READING_ID      NUMBER AUTOINCREMENT PRIMARY KEY,
    READING_TS      TIMESTAMP_NTZ,
    SENSOR_ID       VARCHAR(50),
    CITY            VARCHAR(50),
    LOCATION_TYPE   VARCHAR(50),
    PM25            FLOAT,
    CO2             FLOAT,
    TEMP            FLOAT,
    INGESTED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Raw OpenAQ API pull (optional, kept separate from IoT bronze)
CREATE TABLE IF NOT EXISTS BRONZE_OPENAQ_RAW (
    RECORD_ID       NUMBER AUTOINCREMENT PRIMARY KEY,
    LOCATION_ID     VARCHAR(50),
    LOCATION_NAME   VARCHAR(200),
    CITY            VARCHAR(100),
    LATITUDE        FLOAT,
    LONGITUDE       FLOAT,
    PARAMETER       VARCHAR(50),
    VALUE           FLOAT,
    UNIT            VARCHAR(20),
    READING_DATETIME TIMESTAMP_NTZ,
    FETCHED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ------------------------------------------------------------
-- SILVER LAYER: Cleaned + enriched (IoT + OpenAQ combined)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SILVER_AIR_QUALITY (
    ID              NUMBER AUTOINCREMENT PRIMARY KEY,
    READING_TS      TIMESTAMP_NTZ,
    SENSOR_ID       VARCHAR(50),
    CITY            VARCHAR(50),
    LOCATION_TYPE   VARCHAR(50),
    PM25            FLOAT,
    CO2             FLOAT,
    TEMP            FLOAT,
    AQI_CATEGORY    VARCHAR(50),
    HEALTH_RISK     VARCHAR(50),
    SOURCE          VARCHAR(30),          -- IOT_SIMULATOR / OPENAQ_API
    LOADED_AT       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ------------------------------------------------------------
-- GOLD LAYER: City-wise analytics summary (dashboard-ready)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS GOLD_CITY_ANALYTICS (
    ID              NUMBER AUTOINCREMENT PRIMARY KEY,
    CITY            VARCHAR(50),
    AVG_PM25        FLOAT,
    MAX_PM25        FLOAT,
    MIN_PM25        FLOAT,
    TOTAL_READINGS  NUMBER,
    AQI_CATEGORY    VARCHAR(50),
    HEALTH_RISK     VARCHAR(50),
    GENERATED_AT    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ------------------------------------------------------------
-- Useful GOLD-layer views for the dashboard
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW VW_OVERALL_STATS AS
SELECT
    ROUND(AVG(PM25), 1) AS AVG_AQI,
    COUNT(*)            AS TOTAL_READINGS,
    MAX(PM25)            AS HIGHEST_PM25
FROM SILVER_AIR_QUALITY;

CREATE OR REPLACE VIEW VW_HIGHEST_AQI_CITY AS
SELECT CITY, ROUND(AVG(PM25),1) AS AVG_PM25
FROM SILVER_AIR_QUALITY
GROUP BY CITY
ORDER BY AVG_PM25 DESC
LIMIT 1;

CREATE OR REPLACE VIEW VW_AQI_TREND AS
SELECT
    DATE_TRUNC('HOUR', READING_TS) AS HOUR_BUCKET,
    CITY,
    ROUND(AVG(PM25), 1) AS AVG_PM25
FROM SILVER_AIR_QUALITY
GROUP BY HOUR_BUCKET, CITY
ORDER BY HOUR_BUCKET;
