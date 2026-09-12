import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "hexapulse.db"

# Conservation des événements passés
PAST_EVENT_RETENTION_HOURS = 24


# ============================================================
# CONNEXION SQLITE
# ============================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALISATION DE LA BASE
# ============================================================

def init_database():

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # TABLE DES ÉVÉNEMENTS
    # --------------------------------------------------------

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

            created_at TEXT
        )
    """)

    # --------------------------------------------------------
    # TABLE DES ALERTES DÉJÀ TRAITÉES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_external_id TEXT UNIQUE,

            alert_level TEXT,

            alert_message TEXT,

            created_at TEXT
        )
    """)

    connection.commit()

    connection.close()


# ============================================================
# SAUVEGARDE DES ÉVÉNEMENTS
# ============================================================

def save_events(events):

    if not events:
        return 0

    connection = get_connection()

    cursor = connection.cursor()

    saved = 0

    for event in events:

        try:

            cursor.execute("""
                INSERT OR REPLACE INTO events (
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
                    created_at
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (

                event.get("external_id"),

                event.get("title"),

                event.get("country"),

                event.get("currency"),

                event.get("impact"),

                event.get("event_date"),

                event.get("actual"),

                event.get("forecast"),

                event.get("previous"),

                event.get("description"),

                event.get("source"),

                event.get("created_at")

            ))

            saved += 1

        except Exception as error:

            print(
                "[DATABASE] Erreur sauvegarde :",
                error
            )

    connection.commit()

    connection.close()

    return saved


# ============================================================
# NETTOYAGE DES ANCIENS ÉVÉNEMENTS
# ============================================================

def cleanup_old_events():

    connection = get_connection()

    cursor = connection.cursor()

    limit_date = (
        datetime.now(timezone.utc)
        - timedelta(
            hours=PAST_EVENT_RETENTION_HOURS
        )
    ).isoformat()

    cursor.execute("""
        DELETE FROM events
        WHERE event_date IS NOT NULL
        AND event_date < ?
    """, (
        limit_date,
    ))

    deleted = cursor.rowcount

    connection.commit()

    connection.close()

    print(
        f"[DATABASE] "
        f"Événements supprimés : "
        f"{deleted}"
    )

    return deleted


# ============================================================
# RÉCUPÉRATION DES ÉVÉNEMENTS
# ============================================================

def get_events(limit=200):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
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
            created_at

        FROM events

        ORDER BY event_date ASC

        LIMIT ?
    """, (
        limit,
    ))

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# NOMBRE TOTAL D'ÉVÉNEMENTS
# ============================================================

def get_event_count():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM events
    """)

    count = cursor.fetchone()[0]

    connection.close()

    return count


# ============================================================
# VÉRIFIER SI UNE ALERTE A DÉJÀ ÉTÉ TRAITÉE
# ============================================================

def alert_already_processed(
    event_external_id
):

    if not event_external_id:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id

        FROM alerts_history

        WHERE event_external_id = ?

        LIMIT 1
    """, (
        event_external_id,
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# ENREGISTRER UNE ALERTE
# ============================================================

def save_alert(
    event_external_id,
    alert_level,
    alert_message
):

    if not event_external_id:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

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

            datetime.now(
                timezone.utc
            ).isoformat()

        ))

        connection.commit()

        saved = cursor.rowcount > 0

        connection.close()

        return saved

    except Exception as error:

        print(
            "[DATABASE] "
            "Erreur sauvegarde alerte :",
            error
        )

        connection.close()

        return False


# ============================================================
# RÉCUPÉRER L'HISTORIQUE DES ALERTES
# ============================================================

def get_alert_history(limit=100):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            event_external_id,
            alert_level,
            alert_message,
            created_at

        FROM alerts_history

        ORDER BY created_at DESC

        LIMIT ?
    """, (
        limit,
    ))

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# NETTOYAGE DE L'HISTORIQUE DES ALERTES
# ============================================================

def cleanup_alert_history():

    connection = get_connection()

    cursor = connection.cursor()

    # On conserve l'historique pendant 30 jours
    limit_date = (
        datetime.now(timezone.utc)
        - timedelta(days=30)
    ).isoformat()

    cursor.execute("""
        DELETE FROM alerts_history

        WHERE created_at < ?
    """, (
        limit_date,
    ))

    deleted = cursor.rowcount

    connection.commit()

    connection.close()

    print(
        f"[DATABASE] "
        f"Alertes historiques supprimées : "
        f"{deleted}"
    )

    return deleted


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HEXAPULSE DATABASE")
    print("=" * 60)
    print()

    init_database()

    print(
        "[DATABASE] Base initialisée."
    )

    print(
        f"[DATABASE] "
        f"Événements : "
        f"{get_event_count()}"
    )

    print(
        f"[DATABASE] "
        f"Alertes historiques : "
        f"{len(get_alert_history())}"
    )

    print()