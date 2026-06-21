import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)

cursor = conn.cursor()

# Create organisations table
cursor.execute("""
CREATE TABLE IF NOT EXISTS organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);
""")

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);
""")

# Create org_users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS org_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    role VARCHAR(20) NOT NULL DEFAULT 'member'
    CHECK (role IN ('admin', 'manager', 'member')),
    UNIQUE(user_id, org_id)
);
""")

conn.commit()

# Insert organisation
cursor.execute("""
INSERT INTO organisations(name)
VALUES (%s)
ON CONFLICT(name) DO NOTHING;
""", ("OpenAI",))

# Insert user
cursor.execute("""
INSERT INTO users(name, email, password_hash)
VALUES (%s, %s, %s)
ON CONFLICT(email) DO NOTHING;
""",
(
    "Prarthana",
    "prarthana@example.com",
    "hashed_password_123"
))

conn.commit()

# Get ids
cursor.execute("""
SELECT id FROM users
WHERE email = %s;
""", ("prarthana@example.com",))

user_id = cursor.fetchone()[0]

cursor.execute("""
SELECT id FROM organisations
WHERE name = %s;
""", ("OpenAI",))

org_id = cursor.fetchone()[0]

# Link user to organisation
cursor.execute("""
INSERT INTO org_users(
    user_id,
    org_id,
    role
)
VALUES (%s, %s, %s)
ON CONFLICT(user_id, org_id)
DO NOTHING;
""",
(
    user_id,
    org_id,
    "admin"
))

conn.commit()

# Fetch joined data
cursor.execute("""
SELECT
    u.name,
    u.email,
    o.name,
    ou.role
FROM org_users ou
JOIN users u
    ON ou.user_id = u.id
JOIN organisations o
    ON ou.org_id = o.id;
""")

rows = cursor.fetchall()

print("\nOrganisation Members:\n")

for row in rows:
    print(row)

cursor.close()
conn.close()