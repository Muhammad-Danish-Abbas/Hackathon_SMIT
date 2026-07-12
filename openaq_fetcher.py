"""
OpenAQ API Fetcher
-------------------
Pakistan ke real air quality data OpenAQ API (v3) se fetch karta hai.

Setup:
1. https://explore.openaq.org/register par account banao aur API key lo.
2. .env file mein OPENAQ_API_KEY=xxxx set karo (ya environment variable set karo).

Run:
    python openaq_fetcher.py
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
JSON_PATH = os.path.join(DATA_DIR, "openaq_data.json")

API_KEY = os.getenv("OPENAQ_API_KEY", "")
BASE_URL = "https://api.openaq.org/v3"

# Pakistan ka ISO 3166-1 alpha-2 country code -> ye bbox se zyada accurate hai
# (bbox India ke border wale areas bhi utha leta tha)
PAKISTAN_ISO = "PK"


def get_headers():
    if not API_KEY:
        print("WARNING: OPENAQ_API_KEY set nahi hai. .env file mein daalo.")
    return {"X-API-Key": API_KEY}


def fetch_pakistan_locations(limit=50):
    """Pakistan ke andar available monitoring locations fetch karta hai (country ISO code se filter)."""
    url = f"{BASE_URL}/locations"
    params = {"iso": PAKISTAN_ISO, "limit": limit}
    resp = requests.get(url, headers=get_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def fetch_latest_measurements(location_id):
    """Ek location ki latest readings (parameters: pm25, pm10, co2 etc.) fetch karta hai."""
    url = f"{BASE_URL}/locations/{location_id}/latest"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if resp.status_code != 200:
        return []
    return resp.json().get("results", [])


def build_dataset():
    """Pakistan locations + unki latest measurements combine karke ek clean list banata hai.

    Note: OpenAQ v3 ka /latest endpoint sirf `sensorsId` deta hai, parameter
    ka naam (pm25/co2 etc.) nahi deta. Wo naam location object ke andar
    `sensors` list mein hota hai, isliye pehle sensorId -> parameter mapping
    banate hain, phir latest values ko us mapping se match karte hain.
    """
    records = []
    try:
        locations = fetch_pakistan_locations()
    except Exception as e:
        print(f"Locations fetch mein error: {e}")
        return records

    print(f"{len(locations)} Pakistan locations mile.")

    for loc in locations:
        # Extra safety: iso=PK filter ke bawajood agar koi non-Pakistan
        # location aa jaye to usko skip karo (double-check).
        country = loc.get("country", {}) or {}
        if country.get("code") and country.get("code") != PAKISTAN_ISO:
            continue

        loc_id = loc.get("id")
        name = loc.get("name")
        city = (loc.get("locality") or name or "Unknown")
        coords = loc.get("coordinates", {})

        # sensorId -> (parameter_name, unit) mapping location ke sensors list se
        sensor_map = {}
        for s in loc.get("sensors", []):
            param = s.get("parameter", {}) or {}
            sensor_map[s.get("id")] = (param.get("name"), param.get("units"))

        try:
            measurements = fetch_latest_measurements(loc_id)
        except Exception:
            measurements = []

        for m in measurements:
            sensor_id = m.get("sensorsId")
            param_name, unit = sensor_map.get(sensor_id, (None, None))
            dt = m.get("datetime")
            dt_utc = dt.get("utc") if isinstance(dt, dict) else dt
            m_coords = m.get("coordinates", coords) or coords

            records.append({
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "location_id": loc_id,
                "location_name": name,
                "city": city,
                "latitude": m_coords.get("latitude"),
                "longitude": m_coords.get("longitude"),
                "parameter": param_name,
                "value": m.get("value"),
                "unit": unit,
                "datetime": dt_utc,
            })
        time.sleep(0.3)  # rate limit ka khayal rakhne ke liye

    return records


def save_json(records):
    with open(JSON_PATH, "w") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records save hue: {JSON_PATH}")


def main():
    records = build_dataset()
    if not records:
        print("Koi data nahi mila. API key ya network check karo. Fallback sample data use hoga.")
        records = generate_fallback_sample()
    save_json(records)


def generate_fallback_sample():
    """Agar API fail ho jaye (no key / no internet) to demo ke liye sample data."""
    import random
    cities = ["Karachi", "Lahore", "Islamabad", "Multan", "Peshawar"]
    sample = []
    for city in cities:
        sample.append({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "location_id": f"SAMPLE_{city.upper()}",
            "location_name": f"{city} Monitoring Station",
            "city": city,
            "latitude": None,
            "longitude": None,
            "parameter": "pm25",
            "value": round(random.uniform(30, 150), 1),
            "unit": "µg/m³",
            "datetime": datetime.now(timezone.utc).isoformat(),
        })
    return sample


if __name__ == "__main__":
    main()
