import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database.db")
SQL_PATH = os.path.join(BASE_DIR, "database", "database.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    with open(SQL_PATH, "r") as file:
        conn.executescript(file.read())

    # Add auth_token to existing databases if it doesn't exist
    columns = conn.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "auth_token" not in column_names:
        conn.execute(
            "ALTER TABLE users ADD COLUMN auth_token TEXT"
        )

    conn.commit()
    conn.close()