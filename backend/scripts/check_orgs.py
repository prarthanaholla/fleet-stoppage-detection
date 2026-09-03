import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor = conn.cursor()

cursor.execute("SELECT id, name, org_id FROM vehicles;")
print("Vehicles:", cursor.fetchall())

# add to check_orgs.py
cursor.execute("SELECT started_at FROM stoppages WHERE status='CONFIRMED' LIMIT 3")
print("Stoppages:", cursor.fetchall())

cursor.close()
conn.close()