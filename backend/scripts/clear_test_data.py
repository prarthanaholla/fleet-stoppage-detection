import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor = conn.cursor()

cursor.execute("DELETE FROM gps_raw WHERE id > 8;")
cursor.execute("DELETE FROM stoppages;")
cursor.execute("DELETE FROM gps_matched;")
# clear_test_data.py
cursor.execute("DELETE FROM gps_raw WHERE vehicle_id = 1;")
cursor.execute("DELETE FROM stoppages;")
cursor.execute("DELETE FROM gps_matched;")
cursor.execute("DELETE FROM trips WHERE vehicle_id = 1;")
cursor.execute("""
    ALTER TABLE stoppages 
    DROP CONSTRAINT IF EXISTS valid_status;
""")
cursor.execute("""
    ALTER TABLE stoppages
    DROP CONSTRAINT IF EXISTS stoppages_status_check;
""")
cursor.execute("""
    ALTER TABLE stoppages
    ADD CONSTRAINT valid_status 
    CHECK (status IN ('ACTIVE', 'ENDED', 'SUSPECTED', 'CONFIRMED', 'FALSE_ALARM'));
""")

conn.commit()

cursor.execute("SELECT COUNT(*) FROM gps_raw;")
print(f"gps_raw rows remaining: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
print("Done")