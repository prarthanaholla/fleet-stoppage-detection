import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor = conn.cursor()

# Update vehicle to belong to org_id=5 (Porter)
cursor.execute("UPDATE vehicles SET org_id = 5 WHERE id = 1;")
conn.commit()

cursor.execute("SELECT id, name, org_id FROM vehicles;")
print("Vehicles after fix:", cursor.fetchall())

cursor.close()
conn.close()
print("Done")