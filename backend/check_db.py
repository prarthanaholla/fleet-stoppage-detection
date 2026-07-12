import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor = conn.cursor()

cursor.execute("SELECT * FROM vehicles;")
rows = cursor.fetchall()
print("Vehicles:")
for row in rows:
    print(row)

cursor.execute("SELECT * FROM gps_raw;")
rows = cursor.fetchall()
print("\nGPS Raw:")
for row in rows:
    print(row)

cursor.close()
conn.close()