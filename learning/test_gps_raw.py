import psycopg2
import datetime

gps_time = datetime.datetime.now()
conn=psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor=conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS gps_raw (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    gps_time TIMESTAMP NOT NULL,
    speed DOUBLE PRECISION
);
""")
cursor.execute("""
INSERT INTO gps_raw (
    vehicle_id,
    lat,
    lon,
    gps_time,
    speed
)
VALUES (%s, %s, %s, %s, %s);
""",
(
    1,
    12.9716,
    77.5946,
    gps_time,
    None
))
conn.commit()

cursor.execute("""
SELECT *
FROM gps_raw;
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()
conn.close()