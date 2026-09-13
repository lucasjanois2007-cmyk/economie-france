import time
from datetime import datetime
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
from intelligence import analyze_event, build_alert_message


INTERVAL = 15 * 60
PARIS_TZ = ZoneInfo("Europe/Paris")


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def event_key(event, analysis):
    """
    Crée une clé stable pour éviter les doublons
    d'alertes pendant une même synchronisation.
    """

    title = clean_text(event.get("title")).lower()
    event_date = clean_text(event.get("event_date"))
    category = clean_text(analysis.get("category")).lower()
    country = clean_text(event.get("country")).upper()

    return f"{title}|{event_date}|{category}|{country}"


def analyze_events(events):
    """
    Analyse chaque événement et ajoute les données
    d'intelligence directement dans l'événement.
    """

    print()
    print("[INTELLIGENCE] Analyse des événements...")

    analyzed = []

    for event in events:
        analysis = analyze_event(event)

        event["category"] = analysis["category"]
        event["score"] = analysis["score"]
        event["direction"] = analysis["direction"]
        event["monetary_bias"] = analysis["monetary_bias"]
        event["surprise"] = analysis["surprise"]
        event["alert_level"] = analysis["alert_level"]

        assets = analysis.get("assets", [])

        if isinstance(assets, list):
            event["assets"] = ", ".join(assets)
        else:
            event["assets"] = str(assets or "")

        analyzed.append(event)

    print(
        f"[INTELLIGENCE] "
        f"{len(analyzed)} événement(s) analysé(s)."
    )

    return analyzed


def process_alerts(events):
    """
    Détecte les événements importants et crée les alertes.

    Deux protections contre les doublons :
    1. historique SQLite
    2. clé locale pendant la synchronisation
    """

    print()
    print("============================================================")
    print("🚨 NOUVELLES ALERTES HEXAPULSE")
    print("==============================")
    print()

    new_alerts = []
    alert_keys_seen = set()

    for event in events:
        analysis = {
            "category": event.get("category"),
            "score": event.get("score"),
            "direction": event.get("direction"),
            "monetary_bias": event.get("monetary_bias"),
            "surprise": event.get("surprise"),
            "alert_level": event.get("alert_level"),
            "assets": (
                event.get("assets", "").split(", ")
                if event.get("assets")
                else []
            ),
        }

        level = analysis.get("alert_level")

        # On ignore les événements sans niveau d'alerte important
        if level not in ("IMPORTANT", "ALERT", "CRITICAL"):
            continue

        key = event_key(event, analysis)

        # Protection contre les doublons dans la même synchronisation
        if key in alert_keys_seen:
            continue

        alert_keys_seen.add(key)

        external_id = clean_text(event.get("external_id"))

        # Protection contre les alertes déjà enregistrées
        if external_id and alert_already_processed(external_id):
            continue

        message = build_alert_message(event, analysis)

        alert = {
            "event": event,
            "analysis": analysis,
            "message": message,
        }

        new_alerts.append(alert)

        # Enregistrement dans l'historique
        if external_id:
            save_alert(
                external_id,
                level,
                message,
            )

    if new_alerts:
        for alert in new_alerts:
            event = alert["event"]
            analysis = alert["analysis"]

            print(
                f"[{analysis['alert_level']}] "
                f"{event.get('title', 'Événement')} | "
                f"{analysis['category']} | "
                f"Score : {analysis['score']}/100 | "
                f"Direction : {analysis['direction']} | "
                f"Surprise : "
                f"{analysis['surprise'] if analysis['surprise'] is not None else 'N/D'} | "
                f"Actifs : "
                f"{', '.join(analysis['assets']) if analysis['assets'] else 'N/D'}"
            )

        print()
        print(
            f"[ALERT] {len(new_alerts)} nouvelle(s) alerte(s)."
        )

    else:
        print("[ALERT] Aucune nouvelle alerte.")

    return new_alerts


def sync_hexapulse():
    """
    Effectue une synchronisation complète :

    BiQuote
        ↓
    Data Engine
        ↓
    Intelligence
        ↓
    SQLite
        ↓
    Alertes
    """

    print()
    print("============================================================")
    print("HEXAPULSE BOT — SYNCHRONISATION")
    print("===============================")
    print()

    # ---------------------------------------------------------
    # 1. Récupération des données
    # ---------------------------------------------------------

    events = collect_all_sources()

    print()
    print(
        f"[BOT] Événements récupérés : {len(events)}"
    )

    if not events:
        print("[BOT] Aucun événement récupéré.")
        return

    # ---------------------------------------------------------
    # 2. Analyse intelligente
    # ---------------------------------------------------------

    analyzed_events = analyze_events(events)

    # ---------------------------------------------------------
    # 3. Sauvegarde en base
    # ---------------------------------------------------------

    saved_count = save_events(analyzed_events)

    print(
        f"[BOT] Événements enregistrés : {saved_count}"
    )

    # ---------------------------------------------------------
    # 4. Nettoyage
    # ---------------------------------------------------------

    cleanup_old_events()
    cleanup_alert_history()

    # ---------------------------------------------------------
    # 5. Alertes
    # ---------------------------------------------------------

    new_alerts = process_alerts(analyzed_events)

    # ---------------------------------------------------------
    # 6. Résumé
    # ---------------------------------------------------------

    print()
    print(
        f"[BOT] Événements analysés : "
        f"{len(analyzed_events)}"
    )

    print(
        f"[BOT] Nouvelles alertes : "
        f"{len(new_alerts)}"
    )

    now = datetime.now(PARIS_TZ)

    print()
    print(
        f"[{now.strftime('%H:%M:%S')}] "
        f"Synchronisation terminée."
    )


def main():
    """
    Lance le bot en boucle toutes les 15 minutes.
    """

    print()
    print("=" * 60)
    print("🚀 HEXAPULSE BOT DÉMARRÉ")
    print("=" * 60)
    print()
    print("Synchronisation automatique toutes les 15 minutes.")
    print("Fuseau horaire : Europe/Paris")
    print("CTRL+C pour arrêter.")
    print()
    print("=" * 60)

    # Initialisation de la base
    init_database()

    while True:
        try:
            sync_hexapulse()

            print()
            print(
                "[BOT] Prochaine synchronisation "
                "dans 15 minutes."
            )
            print()

            time.sleep(INTERVAL)

        except KeyboardInterrupt:
            print()
            print("🛑 HEXAPULSE BOT ARRÊTÉ.")
            break

        except Exception as error:
            print()
            print(
                f"[BOT] Erreur pendant la synchronisation : "
                f"{error}"
            )

            print()
            print(
                "[BOT] Nouvelle tentative dans 60 secondes."
            )

            time.sleep(60)


if __name__ == "__main__":
    main()