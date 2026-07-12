"""
IoT Air Quality Sensor Simulator
---------------------------------
Ye script 10 fake IoT sensors ka data generate karti hai (PM2.5, CO2, Temperature)
Har SENSOR_INTERVAL seconds baad naya reading generate hoti hai.
Data CSV file mein save hota hai (data/iot_data.csv) aur agar Snowflake
credentials .env mein set hain to Snowflake ke BRONZE layer mein bhi insert hota hai.

Run:
    python iot_simulator.py                # continuous mode (Ctrl+C to stop)
    python iot_simulator.py --once         # sirf ek batch generate karke exit
    python iot_simulator.py --rounds 5     # 5 rounds generate karke exit
"""

import csv
import os
import random
import time
import argparse
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "iot_data.csv")

SENSOR_INTERVAL = 10  # seconds

# 10 fake sensors -> (sensor_id, city, location_type, base_pm25, base_co2, base_temp)
SENSORS = [
    ("PKS_KHI_IND_01", "Karachi",    "Industrial",  85, 700, 34),
    ("PKS_KHI_TRF_02", "Karachi",    "Traffic",     70, 650, 33),
    ("PKS_KHI_RES_03", "Karachi",    "Residential", 45, 500, 32),
    ("PKS_LHR_RES_04", "Lahore",     "Residential", 95, 720, 35),
    ("PKS_LHR_TRF_05", "Lahore",     "Traffic",     110, 780, 36),
    ("PKS_LHR_IND_06", "Lahore",     "Industrial",  120, 800, 36),
    ("PKS_ISB_PRK_07", "Islamabad",  "Park",        25, 420, 28),
    ("PKS_ISB_RES_08", "Islamabad",  "Residential", 35, 460, 29),
    ("PKS_MUL_TRF_09", "Multan",     "Traffic",     100, 700, 38),
    ("PKS_QTA_RES_10", "Quetta",     "Residential", 40, 480, 25),
]

CSV_HEADERS = ["timestamp", "sensor_id", "city", "location_type", "pm25", "co2", "temp"]


def generate_reading(sensor):
    """Ek sensor ke liye realistic random reading generate karta hai."""
    sensor_id, city, loc_type, base_pm25, base_co2, base_temp = sensor

    pm25 = max(0, round(base_pm25 + random.uniform(-15, 15), 1))
    co2 = max(350, round(base_co2 + random.uniform(-50, 50), 1))
    temp = round(base_temp + random.uniform(-3, 3), 1)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_id": sensor_id,
        "city": city,
        "location_type": loc_type,
        "pm25": pm25,
        "co2": co2,
        "temp": temp,
    }


def append_to_csv(rows):
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def insert_to_snowflake(rows):
    """Optional: agar Snowflake .env configured hai to Bronze layer mein insert karo."""
    try:
        from snowflake_conn import get_connection
    except ImportError:
        return  # snowflake_conn.py nahi mila, skip karo

    try:
        conn = get_connection()
        cur = conn.cursor()
        for r in rows:
            cur.execute(
                """
                INSERT INTO BRONZE_IOT_READINGS
                (READING_TS, SENSOR_ID, CITY, LOCATION_TYPE, PM25, CO2, TEMP)
                VALUES (%(timestamp)s, %(sensor_id)s, %(city)s, %(location_type)s,
                        %(pm25)s, %(co2)s, %(temp)s)
                """,
                r,
            )
        conn.commit()
        cur.close()
        conn.close()
        print(f"  -> Snowflake BRONZE mein {len(rows)} rows insert huey.")
    except Exception as e:
        print(f"  -> Snowflake insert skip (error: {e})")


def run_batch():
    rows = [generate_reading(s) for s in SENSORS]
    append_to_csv(rows)
    insert_to_snowflake(rows)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(rows)} sensor readings generate + CSV mein save.")
    return rows


def main():
    parser = argparse.ArgumentParser(description="IoT Air Quality Sensor Simulator")
    parser.add_argument("--once", action="store_true", help="Sirf ek batch generate karo")
    parser.add_argument("--rounds", type=int, default=0, help="N rounds generate karke exit")
    args = parser.parse_args()

    if args.once:
        run_batch()
        return

    if args.rounds > 0:
        for i in range(args.rounds):
            run_batch()
            if i < args.rounds - 1:
                time.sleep(SENSOR_INTERVAL)
        return

    print("IoT Simulator start ho gaya. Ctrl+C se rokein.")
    try:
        while True:
            run_batch()
            time.sleep(SENSOR_INTERVAL)
    except KeyboardInterrupt:
        print("\nSimulator band kar diya gaya.")


if __name__ == "__main__":
    main()
