"""
ETL Pipeline: Extract -> Transform -> Load
--------------------------------------------
1. Extract : iot_data.csv (simulator) + openaq_data.json (real API) read karta hai.
2. Transform: dropna, duplicates remove, AQI category + health risk add karta hai.
3. Load    : clean data ko Snowflake ke SILVER layer mein (ya CSV fallback mein) load karta hai.

Run:
    python etl.py
"""

import os
import json
import pandas as pd
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IOT_CSV = os.path.join(DATA_DIR, "iot_data.csv")
OPENAQ_JSON = os.path.join(DATA_DIR, "openaq_data.json")
SILVER_CSV = os.path.join(DATA_DIR, "silver_clean.csv")
GOLD_CSV = os.path.join(DATA_DIR, "gold_analytics.csv")


# ---------------------------------------------------------------------
# EXTRACT
# ---------------------------------------------------------------------
def extract_iot():
    if not os.path.isfile(IOT_CSV):
        print("iot_data.csv nahi mili. Pehle iot_simulator.py chalao.")
        return pd.DataFrame()
    df = pd.read_csv(IOT_CSV)
    df["source"] = "IOT_SIMULATOR"
    return df


def extract_openaq():
    if not os.path.isfile(OPENAQ_JSON):
        print("openaq_data.json nahi mili. Pehle openaq_fetcher.py chalao.")
        return pd.DataFrame()
    with open(OPENAQ_JSON) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    if df.empty:
        return df
    # sirf pm25 readings rakho aur IoT jaisa shape do
    df = df[df["parameter"].str.lower() == "pm25"] if "parameter" in df.columns else df
    df = df.rename(columns={"value": "pm25", "datetime": "timestamp"})
    df["sensor_id"] = df.get("location_id")
    df["location_type"] = "OpenAQ_Station"
    df["co2"] = None
    df["temp"] = None
    df["source"] = "OPENAQ_API"
    keep_cols = ["timestamp", "sensor_id", "city", "location_type", "pm25", "co2", "temp", "source"]
    for c in keep_cols:
        if c not in df.columns:
            df[c] = None
    return df[keep_cols]


# ---------------------------------------------------------------------
# TRANSFORM
# ---------------------------------------------------------------------
def aqi_category(pm25):
    """US EPA jaisa simplified PM2.5 -> AQI category mapping."""
    if pd.isna(pm25):
        return "Unknown"
    if pm25 <= 12:
        return "Good"
    elif pm25 <= 35.4:
        return "Moderate"
    elif pm25 <= 55.4:
        return "Unhealthy for Sensitive Groups"
    elif pm25 <= 150.4:
        return "Unhealthy"
    elif pm25 <= 250.4:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def health_risk(category):
    mapping = {
        "Good": "Low",
        "Moderate": "Low-Medium",
        "Unhealthy for Sensitive Groups": "Medium",
        "Unhealthy": "High",
        "Very Unhealthy": "Very High",
        "Hazardous": "Severe",
        "Unknown": "Unknown",
    }
    return mapping.get(category, "Unknown")


def transform(df):
    if df.empty:
        return df

    df = df.dropna(subset=["pm25"]).copy()
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    df = df.dropna(subset=["pm25"])

    df = df.drop_duplicates(subset=["sensor_id", "timestamp", "pm25"])

    df["aqi_category"] = df["pm25"].apply(aqi_category)
    df["health_risk"] = df["aqi_category"].apply(health_risk)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    df["loaded_at"] = datetime.now(timezone.utc).isoformat()

    return df.sort_values("timestamp").reset_index(drop=True)


def build_gold_summary(silver_df):
    """GOLD layer: city-wise analytics summary (dashboard ke liye ready)."""
    if silver_df.empty:
        return pd.DataFrame()

    gold = silver_df.groupby("city").agg(
        avg_pm25=("pm25", "mean"),
        max_pm25=("pm25", "max"),
        min_pm25=("pm25", "min"),
        total_readings=("pm25", "count"),
    ).reset_index()

    gold["avg_pm25"] = gold["avg_pm25"].round(1)
    gold["aqi_category"] = gold["avg_pm25"].apply(aqi_category)
    gold["health_risk"] = gold["aqi_category"].apply(health_risk)
    gold["generated_at"] = datetime.now(timezone.utc).isoformat()

    return gold.sort_values("avg_pm25", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------
def load_to_snowflake(silver_df, gold_df):
    try:
        from snowflake_conn import get_connection
    except ImportError:
        print("snowflake_conn.py nahi mila -> Snowflake load skip, sirf CSV mein save hoga.")
        return

    try:
        conn = get_connection()
        cur = conn.cursor()

        for _, row in silver_df.iterrows():
            cur.execute(
                """
                INSERT INTO SILVER_AIR_QUALITY
                (READING_TS, SENSOR_ID, CITY, LOCATION_TYPE, PM25, CO2, TEMP,
                 AQI_CATEGORY, HEALTH_RISK, SOURCE, LOADED_AT)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(row["timestamp"]), row["sensor_id"], row["city"], row["location_type"],
                    float(row["pm25"]) if pd.notna(row["pm25"]) else None,
                    float(row["co2"]) if pd.notna(row["co2"]) else None,
                    float(row["temp"]) if pd.notna(row["temp"]) else None,
                    row["aqi_category"], row["health_risk"], row["source"], row["loaded_at"],
                ),
            )

        for _, row in gold_df.iterrows():
            cur.execute(
                """
                INSERT INTO GOLD_CITY_ANALYTICS
                (CITY, AVG_PM25, MAX_PM25, MIN_PM25, TOTAL_READINGS,
                 AQI_CATEGORY, HEALTH_RISK, GENERATED_AT)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    row["city"], row["avg_pm25"], row["max_pm25"], row["min_pm25"],
                    int(row["total_readings"]), row["aqi_category"], row["health_risk"],
                    row["generated_at"],
                ),
            )

        conn.commit()
        cur.close()
        conn.close()
        print("Snowflake SILVER + GOLD layers mein data load ho gaya.")
    except Exception as e:
        print(f"Snowflake load mein error (CSV fallback use ho raha hai): {e}")


def main():
    print("Extract shuru...")
    iot_df = extract_iot()
    openaq_df = extract_openaq()
    combined = pd.concat([iot_df, openaq_df], ignore_index=True, sort=False)
    print(f"  Total raw rows: {len(combined)}")

    print("Transform shuru...")
    silver_df = transform(combined)
    print(f"  Clean rows (Silver): {len(silver_df)}")

    gold_df = build_gold_summary(silver_df)
    print(f"  City summaries (Gold): {len(gold_df)}")

    silver_df.to_csv(SILVER_CSV, index=False)
    gold_df.to_csv(GOLD_CSV, index=False)
    print(f"Saved: {SILVER_CSV}")
    print(f"Saved: {GOLD_CSV}")

    print("Load shuru (Snowflake, agar configured hai)...")
    load_to_snowflake(silver_df, gold_df)

    print("ETL complete!")


if __name__ == "__main__":
    main()
