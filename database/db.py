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

    conn.commit()
    conn.close()
