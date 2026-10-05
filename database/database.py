import psycopg
from psycopg.types.json import Json
from config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)

def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def save_measurement(device_id, data):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO measurements (device_id, data)
            VALUES (%s, %s)
            """,
            (
                device_id,
                Json(data)
            )
        )

        connection.commit()

    finally:
        connection.close()