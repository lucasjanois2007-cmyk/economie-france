from pathlib import Path
from datetime import datetime, timezone
import sqlite3


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "hexapulse.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            title TEXT,
            country TEXT,
            currency TEXT,
            impact TEXT,
            event_date TEXT,
            actual TEXT,
            forecast TEXT,
            previous TEXT,
            description TEXT,
            source TEXT,
            created_at TEXT,

            category TEXT,
            score INTEGER,
            direction TEXT,
            monetary_bias TEXT,
            surprise REAL,
            alert_level TEXT,
            assets TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_external_id TEXT UNIQUE,
            alert_level TEXT,
            alert_message TEXT,
            created_at TEXT
        )
    """)

    # Migration pour une ancienne base HexaPulse
    existing_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(events)").fetchall()
    }

    columns_to_add = {
        "category": "TEXT",
        "score": "INTEGER",
        "direction": "TEXT",
        "monetary_bias": "TEXT",
        "surprise": "REAL",
        "alert_level": "TEXT",
        "assets": "TEXT",
    }

    for column, column_type in columns_to_add.items():
        if column not in existing_columns:
            cursor.execute(
                f"ALTER TABLE events ADD COLUMN {column} {column_type}"
            )

    connection.commit()
    connection.close()

    print("[DATABASE] Base initialisée.")


def save_events(events):
    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        external_id = event.get("external_id")

        if not external_id:
            external_id = (
                f"{event.get('title', '')}|"
                f"{event.get('event_date', '')}|"
                f"{event.get('country', '')}"
            )

        cursor.execute("""
            INSERT INTO events (
                external_id,
                title,
                country,
                currency,
                impact,
                event_date,
                actual,
                forecast,
                previous,
                description,
                source,
                created_at,
                category,
                score,
                direction,
                monetary_bias,
                surprise,
                alert_level,
                assets
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(external_id) DO UPDATE SET
                title = excluded.title,
                country = excluded.country,
                currency = excluded.currency,
                impact = excluded.impact,
                event_date = excluded.event_date,
                actual = excluded.actual,
                forecast = excluded.forecast,
                previous = excluded.previous,
                description = excluded.description,
                source = excluded.source,
                category = excluded.category,
                score = excluded.score,
                direction = excluded.direction,
                monetary_bias = excluded.monetary_bias,
                surprise = excluded.surprise,
                alert_level = excluded.alert_level,
                assets = excluded.assets
        """, (
            external_id,
            event.get("title", ""),
            event.get("country", ""),
            event.get("currency", ""),
            event.get("impact", ""),
            event.get("event_date", ""),
            event.get("actual", ""),
            event.get("forecast", ""),
            event.get("previous", ""),
            event.get("description", ""),
            event.get("source", ""),
            event.get("created_at", now),

            event.get("category"),
            event.get("score"),
            event.get("direction"),
            event.get("monetary_bias"),
            event.get("surprise"),
            event.get("alert_level"),
            event.get("assets"),
        ))

    connection.commit()
    connection.close()

    return len(events)


def cleanup_old_events():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM events
        WHERE event_date < datetime('now', '-30 days')
    """)

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    print(f"[DATABASE] Événements supprimés : {deleted}")
    return deleted


def get_events(limit=500):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM events
        ORDER BY event_date ASC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return [dict(row) for row in rows]


def get_event_count():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM events")
    count = cursor.fetchone()[0]

    connection.close()

    return count


def alert_already_processed(event_external_id):
    if not event_external_id:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT 1
        FROM alerts_history
        WHERE event_external_id = ?
        LIMIT 1
    """, (event_external_id,))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def save_alert(event_external_id, alert_level, alert_message):
    if not event_external_id:
        return

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO alerts_history (
            event_external_id,
            alert_level,
            alert_message,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        event_external_id,
        alert_level,
        alert_message,
        datetime.now(timezone.utc).isoformat()
    ))

    connection.commit()
    connection.close()


def get_alert_history(limit=100):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM alerts_history
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    return [dict(row) for row in rows]


def cleanup_alert_history():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM alerts_history
        WHERE created_at < datetime('now', '-90 days')
    """)

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    print(f"[DATABASE] Alertes historiques supprimées : {deleted}")
    return deleted


if __name__ == "__main__":
    print()
    print("HEXAPULSE DATABASE")
    print("==================")
    print()

    init_database()

    print(f"[DATABASE] Événements : {get_event_count()}")
    print(
        f"[DATABASE] Alertes historiques : "
        f"{len(get_alert_history())}"
    )