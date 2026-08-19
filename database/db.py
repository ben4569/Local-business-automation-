import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()


class DatabaseError(RuntimeError):
    pass


def get_config():
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", ""),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "shopsight"),
    }


@contextmanager
def get_connection():
    connection = None

    try:
        connection = mysql.connector.connect(
            **get_config()
        )

        yield connection

    except Error as exc:
        raise DatabaseError(
            "Unable to connect to the database."
        ) from exc

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def init_db():
    with get_connection() as connection:
        cursor = connection.cursor(
            buffered=True
        )

        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()


def test_connection():
    with get_connection() as connection:
        cursor = connection.cursor(
            buffered=True
        )

        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            return result is not None and result[0] == 1

        finally:
            cursor.close()
