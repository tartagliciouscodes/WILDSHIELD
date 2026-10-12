import sqlite3
from datetime import datetime

DB_NAME = "wildlife_events.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal TEXT,
        time TEXT,
        risk TEXT,
        confidence REAL
    )
    """)

    conn.commit()
    conn.close()


def save_event(animal, risk, confidence):
    init_db()

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    event_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    cursor.execute(
        """
        INSERT INTO events (animal, time, risk, confidence)
        VALUES (?, ?, ?, ?)
        """,
        (animal, event_time, risk, confidence)
    )

    conn.commit()
    conn.close()


def get_events():
    init_db()

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    SELECT animal, time, risk, confidence
    FROM events
    ORDER BY id DESC
    """)

    events = cursor.fetchall()

    conn.close()

    return events


init_db()
