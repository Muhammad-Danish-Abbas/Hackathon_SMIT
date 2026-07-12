"""
Snowflake Connection Diagnostic Script
----------------------------------------
Ye script sirf ye check karta hai ke .env se Snowflake connection ban raha hai ya nahi.
Koi sensitive data print nahi karta (password kabhi print nahi hota).

Run (project folder ke andar, jahan .env hai):
    python test_connection.py
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] .env file load ho gayi (agar exist karti hai)")
except ImportError:
    print("[WARN] python-dotenv installed nahi hai -> pip install python-dotenv")

# ---- Step 1: Check karo ke sab env vars mil rahe hain ----
required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
missing = [v for v in required if not os.getenv(v)]

if missing:
    print(f"[FAIL] Ye environment variables missing hain: {missing}")
    print("       -> .env file check karo, ye script us folder se chalao jahan .env hai")
    raise SystemExit(1)

account = os.environ["SNOWFLAKE_ACCOUNT"]
user = os.environ["SNOWFLAKE_USER"]
password = os.environ["SNOWFLAKE_PASSWORD"]

print(f"[OK] SNOWFLAKE_ACCOUNT  = {account}")
print(f"[OK] SNOWFLAKE_USER     = {user}")
print(f"[OK] SNOWFLAKE_PASSWORD = {'*' * len(password)} ({len(password)} characters)")
print(f"[OK] SNOWFLAKE_WAREHOUSE = {os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')}")
print(f"[OK] SNOWFLAKE_DATABASE  = {os.getenv('SNOWFLAKE_DATABASE', 'AQI_HACKATHON')}")
print(f"[OK] SNOWFLAKE_SCHEMA    = {os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')}")

# ---- Step 2: Actual connection try karo ----
print("\nConnecting to Snowflake...")

try:
    import snowflake.connector
except ImportError:
    print("[FAIL] snowflake-connector-python installed nahi hai")
    print("       -> pip install snowflake-connector-python")
    raise SystemExit(1)

try:
    conn = snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "AQI_HACKATHON"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    )
    print("[SUCCESS] Snowflake se connection ban gaya!")

    cur = conn.cursor()
    cur.execute("SELECT CURRENT_VERSION(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
    version, db, schema, wh = cur.fetchone()
    print(f"  Snowflake version : {version}")
    print(f"  Current database  : {db}")
    print(f"  Current schema    : {schema}")
    print(f"  Current warehouse : {wh}")

    # Tables check karo
    cur.execute("SHOW TABLES IN SCHEMA PUBLIC")
    tables = cur.fetchall()
    print(f"\n  PUBLIC schema mein {len(tables)} tables mile:")
    for t in tables:
        print(f"    - {t[1]}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"[FAIL] Connection nahi bana. Error:\n{e}")
    print("\nCommon fixes:")
    print("  1. Account identifier format check karo (e.g. tm62640.ap-south-1 - no https://, no .snowflakecomputing.com)")
    print("  2. Password mein special characters (# @ etc.) hain to .env mein quotes lagao: SNOWFLAKE_PASSWORD=\"your#pass\"")
    print("  3. Username sahi hai ya nahi confirm karo (Session details se mila wala)")
    print("  4. Warehouse 'COMPUTE_WH' start/resumed hai ya nahi Snowflake console mein check karo")
