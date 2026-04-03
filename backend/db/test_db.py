# test_db.py — run this to confirm connection
from psycopg2 import connect

try:
    conn = connect(
        host='localhost',
        port=5432,
        database='wildfire_db',
        user='postgres',
        password='root'
    )
    print("✅ Connected successfully!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)