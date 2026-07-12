import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import snowflake.connector

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SILVER_CSV = os.path.join(DATA_DIR, "silver_clean.csv")
GOLD_CSV = os.path.join(DATA_DIR, "gold_analytics.csv")

st.set_page_config(page_title="Pakistan Air Quality Dashboard", layout="wide", page_icon="🌫️")


@st.cache_data(ttl=30)
def load_data():
    try:
        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "AQI_HACKATHON"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )
        silver = pd.read_sql("SELECT * FROM SILVER_AIR_QUALITY", conn)
        gold = pd.read_sql("SELECT * FROM GOLD_CITY_ANALYTICS", conn)
        conn.close()
        silver.columns = [c.lower() for c in silver.columns]
        gold.columns = [c.lower() for c in gold.columns]
        return silver, gold, "Snowflake (Live)", None
    except Exception as e:
        silver = pd.read_csv(SILVER_CSV) if os.path.isfile(SILVER_CSV) else pd.DataFrame()
        gold = pd.read_csv(GOLD_CSV) if os.path.isfile(GOLD_CSV) else pd.DataFrame()
        return silver, gold, "Local CSV (ETL Output)", str(e)


def main():
    st.title("Pakistan Air Quality Monitoring Dashboard")
    st.caption("IoT Sensors + OpenAQ Real Data | Bronze -> Silver -> Gold Pipeline")

    silver, gold, source, snowflake_error = load_data()

    st.sidebar.header("Data Source")
    st.sidebar.info(f"Currently showing: **{source}**")
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    if snowflake_error:
        st.error(f"Snowflake connection failed: {snowflake_error}")

    if silver.empty:
        st.warning("Abhi data available nahi.")
        return

    col1, col2, col3, col4 = st.columns(4)
    avg_aqi = round(silver["pm25"].mean(), 1)
    total_readings = len(silver)
    if not gold.empty:
        highest_row = gold.loc[gold["avg_pm25"].idxmax()]
        highest_city = highest_row["city"]
        highest_val = highest_row["avg_pm25"]
    else:
        highest_city, highest_val = "N/A", 0

    col1.metric("Average AQI (PM2.5)", f"{avg_aqi}")
    col2.metric("Highest AQI City", f"{highest_city}", f"{highest_val}")
    col3.metric("Total Readings", f"{total_readings}")
    col4.metric("Active Cities", f"{silver['city'].nunique()}")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("City-wise Average PM2.5")
        if not gold.empty:
            fig = px.bar(gold.sort_values("avg_pm25", ascending=False),
                         x="city", y="avg_pm25", color="avg_pm25",
                         color_continuous_scale="OrRd",
                         labels={"avg_pm25": "Avg PM2.5", "city": "City"})
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("AQI Category Distribution")
        cat_counts = silver["aqi_category"].value_counts().reset_index()
        cat_counts.columns = ["aqi_category", "count"]
        fig2 = px.pie(cat_counts, names="aqi_category", values="count", hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("AQI Trend Over Time")
    if "timestamp" in silver.columns:
        silver["timestamp"] = pd.to_datetime(silver["timestamp"], errors="coerce")
        trend_df = silver.dropna(subset=["timestamp"]).sort_values("timestamp")
        fig3 = px.line(trend_df, x="timestamp", y="pm25", color="city", markers=True)
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Raw Clean Data (Silver Layer)"):
        st.dataframe(silver, use_container_width=True)

    with st.expander("City Analytics (Gold Layer)"):
        st.dataframe(gold, use_container_width=True)


if __name__ == "__main__":
    main()
