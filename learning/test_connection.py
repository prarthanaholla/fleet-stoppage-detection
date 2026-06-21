import datetime

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)

cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    last_lat DOUBLE PRECISION,
    last_lng DOUBLE PRECISION,
    last_seen TIMESTAMP,
    org_id INTEGER NOT NULL REFERENCES organisations(id)
);
""")

# Insert or update vehicle
cursor.execute("""
INSERT INTO vehicles (
    name,
    last_lat,
    last_lng,
    last_seen,
    org_id
)
VALUES (%s, %s, %s, %s, %s)

ON CONFLICT (name)
DO UPDATE SET
    last_lat = EXCLUDED.last_lat,
    last_lng = EXCLUDED.last_lng,
    last_seen = EXCLUDED.last_seen,
    org_id = EXCLUDED.org_id;
""",
(
    "Truck A",
    12.9716,
    77.5946,
    datetime.datetime.now(),
    1
))

conn.commit()

# Fetch data
cursor.execute("""
SELECT *
FROM vehicles;
""")

rows = cursor.fetchall()

print("\nVehicles Table:")
for row in rows:
    print(row)

cursor.close()
conn.close()
"""
Why UNIQUE on name: Postgres has no built-in concept of "this row represents the same real-world vehicle as that row" unless you tell it which column to check. By adding UNIQUE to name, you're telling Postgres: "no two rows in this table are allowed to have the same name value, ever." This is what gives the word "conflict" any meaning at all — without that rule, inserting "Truck A" twice is just two unrelated rows to Postgres, nothing conflicting about it.
What ON CONFLICT (name) DO UPDATE actually does: when you try to INSERT a new row, Postgres first checks: does any existing row already have this same name? If no — proceed with a normal insert, brand new row, new id. If yes — that's the "conflict" — and instead of inserting, Postgres throws away the insert attempt and instead runs the UPDATE clause on the existing row that has that matching name, setting last_lat, last_lng, last_seen to the new incoming values.
Why this guarantees one row per vehicle: since name is unique and every insert attempt checks against that uniqueness rule first, it's structurally impossible for two rows with the same name to ever coexist. The first ping for a new vehicle creates its one row. Every ping after that, forever, updates that same row instead of creating a new one.
"""