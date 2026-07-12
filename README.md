# 🌫️ Pakistan Air Quality Monitoring System

Ek end-to-end data engineering project jo **fake IoT sensor data** aur **real OpenAQ API data**
ko combine karke Snowflake ke **Medallion Architecture (Bronze → Silver → Gold)** mein store karta hai,
aur ek **Streamlit dashboard** par live insights dikhata hai.

---

## 📐 Architecture

```
Python IoT Simulator ──┐
                        ├──► Pandas ETL ──► Snowflake (Bronze → Silver → Gold) ──► Streamlit Dashboard
OpenAQ API Fetcher ─────┘
```

- **Bronze Layer** — Raw, uncleaned data (IoT readings + OpenAQ raw pulls)
- **Silver Layer** — Cleaned, deduplicated, enriched with AQI Category + Health Risk
- **Gold Layer** — City-wise analytics summary, dashboard-ready

---

## 📁 Project Structure

```
aqi_hackathon/
├── iot_simulator.py       # Step 1: 10 fake IoT sensors, generates readings every 10s
├── openaq_fetcher.py      # Step 2: Real Pakistan AQI data from OpenAQ API
├── etl.py                 # Step 3: Extract → Transform → Load pipeline (Pandas)
├── snowflake_conn.py      # Snowflake connection helper
├── sql/
│   └── snowflake_setup.sql # Step 4: Bronze/Silver/Gold table DDL + views
├── dashboard.py            # Step 5: Streamlit dashboard
├── data/                   # Generated CSV/JSON files (gitignored recommended)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Setup & Run (Step by Step)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment variables
`.env.example` ko `.env` mein copy karo aur apni OpenAQ API key + Snowflake credentials daalo:
```bash
cp .env.example .env
```

> **Note:** Agar Snowflake credentials set nahi karoge, tab bhi poora system chalega —
> ETL automatically local CSV files mein data save karega aur dashboard unhi se data dikhayega.

### 3. Snowflake setup (agar use kar rahe ho)
Snowflake worksheet mein `sql/snowflake_setup.sql` run karo — ye database, schema, aur
Bronze/Silver/Gold tables + dashboard views bana dega.

### 4. IoT Simulator chalao
```bash
python iot_simulator.py --rounds 5      # demo ke liye 5 rounds (~50 sec)
# ya continuous mode:
python iot_simulator.py
```

### 5. OpenAQ real data fetch karo
```bash
python openaq_fetcher.py
```

### 6. ETL chalao (clean + Snowflake load)
```bash
python etl.py
```

### 7. Dashboard chalao
```bash
streamlit run dashboard.py
```

---

## 📊 Dashboard Features
- ✅ Average AQI (PM2.5)
- ✅ Highest AQI City
- ✅ Total Readings count
- ✅ City-wise PM2.5 bar chart
- ✅ AQI category distribution (pie chart)
- ✅ AQI trend over time (line chart)
- ✅ Raw Silver/Gold data tables

---

## 🧪 Tech Stack
- **Python** — IoT simulation, ETL logic
- **OpenAQ API v3** — real-world air quality data source
- **Pandas** — data cleaning & transformation
- **Snowflake** — Medallion architecture data warehouse
- **Streamlit + Plotly** — interactive dashboard

---

## 👤 Author
Muhammad Danish — SMIT 

---


