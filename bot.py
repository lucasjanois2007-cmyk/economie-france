import time
from datetime import datetime
from zoneinfo import ZoneInfo

from data_sources import collect_all_sources
from intelligence import analyze_event

from database import (
    init_database,
    save_events,
    cleanup_old_events,
    cleanup_alert_history,
    alert_already_processed,
    save_alert,
)


# ============================================================
# CONFIGURATION
# ============================================================

INTERVAL = 15 * 60

# Fuseau horaire officiel HexaPulse
PARIS_TZ = ZoneInfo("Europe/Paris")


# ============================================================
# CREATION D'UNE ALERTE INTELLIGENTE
# ============================================================

def build_alert(event, analysis):

    score = analysis["score"]
    level = analysis["alert_level"]

    # --------------------------------------------------------
    # SEULEMENT IMPORTANT ET CRITIQUE
    # --------------------------------------------------------

    if level not in {
        "IMPORTANT",
        "CRITIQUE",
    }:
        return None

    title = event.get(
        "title",
        "Annonce économique",
    )

    direction = analysis["direction"]

    indicator_type = analysis["indicator_type"]

    assets = analysis["assets"]

    surprise = analysis["surprise"]

    if surprise is None:
        surprise_text = "N/D"
    else:
        surprise_text = f"{surprise:+.2f}"

    assets_text = (
        ", ".join(assets)
        if assets
        else "Marché général"
    )

    message = (
        f"{title} | "
        f"{indicator_type} | "
        f"Score : {score}/100 | "
        f"Direction : {direction} | "
        f"Surprise : {surprise_text} | "
        f"Actifs : {assets_text}"
    )

    return {
        "level": level,
        "message": message,
    }


# ============================================================
# TRAITEMENT DES ALERTES
# ============================================================

def process_alerts(events):

    new_alerts = []

    for event in events:

        try:

            # Analyse complète de l'événement
            analysis = analyze_event(event)

            # Ajout des informations directement
            # dans l'événement
            event["hexapulse_score"] = analysis["score"]

            event["indicator_type"] = (
                analysis["indicator_type"]
            )

            event["surprise"] = analysis["surprise"]

            event["direction"] = analysis["direction"]

            event["alert_level"] = (
                analysis["alert_level"]
            )

            event["market_assets"] = ", ".join(
                analysis["assets"]
            )

            # Construction de l'alerte
            alert = build_alert(
                event,
                analysis,
            )

            # Pas d'alerte si NORMAL ou SURVEILLER
            if not alert:
                continue

            external_id = event.get(
                "external_id"
            )

            if not external_id:
                continue

            # Évite les doublons
            if alert_already_processed(
                external_id
            ):
                continue

            # Sauvegarde de l'alerte
            saved = save_alert(
                external_id,
                alert["level"],
                alert["message"],
            )

            if saved:
                new_alerts.append(alert)

        except Exception as error:

            print(
                "[INTELLIGENCE] "
                f"Erreur analyse : {error}"
            )

    return new_alerts


# ============================================================
# AFFICHAGE DES ALERTES
# ============================================================

def display_alerts(alerts):

    if not alerts:

        print()
        print(
            "[ALERT] "
            "Aucune nouvelle alerte."
        )

        return

    print()
    print("=" * 60)
    print(
        "🚨 NOUVELLES ALERTES HEXAPULSE"
    )
    print("=" * 60)

    for alert in alerts[:10]:

        print()

        print(
            f"[{alert['level']}] "
            f"{alert['message']}"
        )

    print()

    print(
        f"[ALERT] "
        f"{len(alerts)} nouvelle(s) "
        f"alerte(s)."
    )


# ============================================================
# SYNCHRONISATION HEXAPULSE
# ============================================================

def sync_hexapulse():

    print()
    print("=" * 60)
    print(
        "HEXAPULSE BOT — SYNCHRONISATION"
    )
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # RECUPERATION DES DONNEES
        # ----------------------------------------------------

        events = collect_all_sources()

        if not events:

            print(
                "[BOT] "
                "Aucun événement récupéré."
            )

            return

        # ----------------------------------------------------
        # SAUVEGARDE SQLITE
        # ----------------------------------------------------

        saved = save_events(events)

        # ----------------------------------------------------
        # NETTOYAGE
        # ----------------------------------------------------

        cleanup_old_events()

        cleanup_alert_history()

        # ----------------------------------------------------
        # INTELLIGENCE HEXAPULSE
        # ----------------------------------------------------

        print()
        print(
            "[INTELLIGENCE] "
            "Analyse des événements..."
        )

        analyzed_count = 0

        for event in events:

            try:

                analysis = analyze_event(event)

                event["hexapulse_score"] = (
                    analysis["score"]
                )

                event["indicator_type"] = (
                    analysis["indicator_type"]
                )

                event["surprise"] = (
                    analysis["surprise"]
                )

                event["direction"] = (
                    analysis["direction"]
                )

                event["alert_level"] = (
                    analysis["alert_level"]
                )

                analyzed_count += 1

            except Exception as error:

                print(
                    "[INTELLIGENCE] "
                    f"Erreur : {error}"
                )

        print(
            f"[INTELLIGENCE] "
            f"{analyzed_count} événement(s) "
            f"analysé(s)."
        )

        # ----------------------------------------------------
        # ALERTES INTELLIGENTES
        # ----------------------------------------------------

        alerts = process_alerts(events)

        display_alerts(alerts)

        # ----------------------------------------------------
        # RESUME
        # ----------------------------------------------------

        # Heure française Europe/Paris
        now = datetime.now(PARIS_TZ).strftime(
            "%H:%M:%S"
        )

        print()

        print(
            f"[{now}] "
            "Synchronisation terminée."
        )

        print(
            f"[BOT] "
            f"Événements récupérés : "
            f"{len(events)}"
        )

        print(
            f"[BOT] "
            f"Événements enregistrés : "
            f"{saved}"
        )

        print(
            f"[BOT] "
            f"Événements analysés : "
            f"{analyzed_count}"
        )

        print(
            f"[BOT] "
            f"Nouvelles alertes : "
            f"{len(alerts)}"
        )

    except Exception as error:

        print()
        print(
            "[BOT] ERREUR"
        )

        print(
            f"[BOT] {error}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    init_database()

    print()
    print("=" * 60)
    print(
        "🚀 HEXAPULSE BOT DÉMARRÉ"
    )
    print("=" * 60)

    print()

    print(
        "Synchronisation automatique "
        "toutes les 15 minutes."
    )

    print(
        "Fuseau horaire : Europe/Paris"
    )

    print(
        "CTRL+C pour arrêter."
    )

    print()

    while True:

        sync_hexapulse()

        print()

        print(
            "[BOT] Prochaine synchronisation "
            "dans 15 minutes."
        )

        print()

        try:

            time.sleep(INTERVAL)

        except KeyboardInterrupt:

            print()

            print(
                "🛑 HEXAPULSE BOT ARRÊTÉ."
            )

            break


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    main()