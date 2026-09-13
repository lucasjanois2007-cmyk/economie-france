"""
HEXAPULSE BOT
Synchronisation automatique du calendrier économique.

Fonctions :
- récupération BiQuote
- sauvegarde SQLite
- nettoyage des anciennes données
- analyse économique
- détection des alertes
- anti-doublon
- synchronisation toutes les 15 minutes
"""

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from data_sources import collect_all_sources
from database import (
    init_database,
    save_events,
    cleanup_old_events,
    alert_already_processed,
    save_alert,
    cleanup_alert_history,
)

from intelligence import (
    analyze_event,
    build_alert_message,
)


# ============================================================
# CONFIGURATION
# ============================================================

INTERVAL = 15 * 60

PARIS_TZ = ZoneInfo("Europe/Paris")

MIN_ALERT_SCORE = 75


# ============================================================
# HEURE
# ============================================================

def paris_now():
    return datetime.now(PARIS_TZ)


def utc_now():
    return datetime.now(timezone.utc)


# ============================================================
# OUTILS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def event_key(event, analysis):
    """
    Clé logique d'un événement.

    Elle sert à empêcher deux entrées identiques
    de générer deux alertes.
    """

    title = clean_text(
        event.get("title")
    ).lower()

    event_date = clean_text(
        event.get("event_date")
    )

    category = clean_text(
        analysis.get("category")
    ).lower()

    country = clean_text(
        event.get("country")
        or event.get("country_code")
        or event.get("countryCode")
    ).upper()

    return (
        title,
        event_date,
        category,
        country,
    )


# ============================================================
# ANALYSE DES ÉVÉNEMENTS
# ============================================================

def analyze_events(events):
    analyzed = []

    print()
    print("[INTELLIGENCE] Analyse des événements...")

    for event in events:
        try:
            analysis = analyze_event(event)

            event["intelligence_score"] = analysis["score"]
            event["intelligence_category"] = analysis["category"]
            event["intelligence_direction"] = analysis["direction"]
            event["intelligence_monetary_bias"] = (
                analysis["monetary_bias"]
            )
            event["intelligence_surprise"] = (
                analysis["surprise"]
            )
            event["intelligence_alert_level"] = (
                analysis["alert_level"]
            )
            event["intelligence_assets"] = (
                analysis["assets"]
            )

            analyzed.append(
                (
                    event,
                    analysis,
                )
            )

        except Exception as error:
            print(
                "[INTELLIGENCE] Erreur analyse :",
                error,
            )

    print(
        f"[INTELLIGENCE] {len(analyzed)} événement(s) analysé(s)."
    )

    return analyzed


# ============================================================
# ALERTES
# ============================================================

def process_alerts(analyzed_events):
    alerts = []

    # Anti-doublon pendant UNE synchronisation.
    alert_keys_seen = set()

    for event, analysis in analyzed_events:

        score = analysis.get(
            "score",
            0,
        )

        level = analysis.get(
            "alert_level",
            "INFO",
        )

        if score < MIN_ALERT_SCORE:
            continue

        key = event_key(
            event,
            analysis,
        )

        # Même événement rencontré deux fois
        # pendant la même synchronisation.
        if key in alert_keys_seen:
            continue

        alert_keys_seen.add(key)

        external_id = clean_text(
            event.get("external_id")
        )

        # Si l'événement existe déjà dans
        # l'historique, aucune nouvelle alerte.
        if external_id and alert_already_processed(
            external_id
        ):
            continue

        message = build_alert_message(
            event,
            analysis,
        )

        if external_id:
            saved = save_alert(
                external_id,
                level,
                message,
            )

            if not saved:
                continue

        alerts.append(
            {
                "event": event,
                "analysis": analysis,
                "message": message,
            }
        )

    return alerts


# ============================================================
# AFFICHAGE
# ============================================================

def print_alerts(alerts):

    print()
    print("=" * 60)
    print("🚨 NOUVELLES ALERTES HEXAPULSE")
    print("=" * 60)

    if not alerts:
        print()
        print("Aucune nouvelle alerte.")
        return

    print()

    for alert in alerts:
        event = alert["event"]
        analysis = alert["analysis"]

        level = analysis["alert_level"]
        score = analysis["score"]

        print(
            f"[{level}] "
            f"{alert['message']}"
        )

    print()
    print(
        f"[ALERT] {len(alerts)} nouvelle(s) alerte(s)."
    )


# ============================================================
# SYNCHRONISATION
# ============================================================

def sync_hexapulse():

    print()
    print("=" * 60)
    print("HEXAPULSE BOT — SYNCHRONISATION")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # 1. RÉCUPÉRATION
    # --------------------------------------------------------

    try:
        events = collect_all_sources()

    except Exception as error:
        print(
            "[BOT] Erreur récupération données :",
            error,
        )
        return

    if not events:
        print(
            "[BOT] Aucun événement récupéré."
        )
        return

    print(
        f"[BOT] Événements récupérés : {len(events)}"
    )

    # --------------------------------------------------------
    # 2. SAUVEGARDE
    # --------------------------------------------------------

    try:
        saved = save_events(events)

    except Exception as error:
        print(
            "[BOT] Erreur sauvegarde :",
            error,
        )
        saved = 0

    print(
        f"[BOT] Événements enregistrés : {saved}"
    )

    # --------------------------------------------------------
    # 3. NETTOYAGE
    # --------------------------------------------------------

    try:
        cleanup_old_events()
        cleanup_alert_history()

    except Exception as error:
        print(
            "[BOT] Erreur nettoyage :",
            error,
        )

    # --------------------------------------------------------
    # 4. INTELLIGENCE
    # --------------------------------------------------------

    analyzed = analyze_events(
        events
    )

    print(
        f"[BOT] Événements analysés : {len(analyzed)}"
    )

    # --------------------------------------------------------
    # 5. ALERTES
    # --------------------------------------------------------

    alerts = process_alerts(
        analyzed
    )

    print_alerts(
        alerts
    )

    # --------------------------------------------------------
    # 6. HORODATAGE
    # --------------------------------------------------------

    print()
    print(
        f"[{paris_now().strftime('%H:%M:%S')}] "
        "Synchronisation terminée."
    )

    print(
        f"[BOT] Prochaine synchronisation "
        f"dans {INTERVAL // 60} minutes."
    )


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 60)
    print("🚀 HEXAPULSE BOT DÉMARRÉ")
    print("=" * 60)
    print()
    print(
        "Synchronisation automatique toutes les 15 minutes."
    )
    print(
        "Fuseau horaire : Europe/Paris"
    )
    print(
        "CTRL+C pour arrêter."
    )
    print()
    print("=" * 60)

    init_database()

    while True:

        try:
            sync_hexapulse()

        except KeyboardInterrupt:
            print()
            print(
                "🛑 HEXAPULSE BOT ARRÊTÉ."
            )
            break

        except Exception as error:
            print()
            print(
                "[BOT] Erreur générale :",
                error,
            )
            print(
                "[BOT] Nouvelle tentative dans 60 secondes."
            )

            time.sleep(60)
            continue

        try:
            time.sleep(
                INTERVAL
            )

        except KeyboardInterrupt:
            print()
            print(
                "🛑 HEXAPULSE BOT ARRÊTÉ."
            )
            break


if __name__ == "__main__":
    main()