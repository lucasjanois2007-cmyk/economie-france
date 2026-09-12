import time
from datetime import datetime

from data_sources import collect_all_sources

from database import (
    init_database,
    save_events,
    cleanup_old_events,
    cleanup_alert_history,
    alert_already_processed,
    save_alert
)


# ============================================================
# CONFIGURATION
# ============================================================

INTERVAL = 15 * 60


# ============================================================
# NORMALISATION DE L'IMPACT
# ============================================================

def normalize_impact(impact):

    value = str(
        impact or ""
    ).lower().strip()

    if value in [
        "high",
        "fort",
        "forte",
        "3",
        "3.0",
        "red"
    ]:
        return "FORT"

    if value in [
        "medium",
        "moyen",
        "moyenne",
        "2",
        "2.0",
        "orange"
    ]:
        return "MOYEN"

    return "FAIBLE"


# ============================================================
# CONVERSION DES NOMBRES
# ============================================================

def parse_number(value):

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    text = text.replace(
        "%",
        ""
    )

    text = text.replace(
        ",",
        "."
    )

    try:

        return float(text)

    except ValueError:

        return None


# ============================================================
# CALCUL DE LA SURPRISE
# ============================================================

def calculate_surprise(event):

    actual = parse_number(
        event.get("actual")
    )

    forecast = parse_number(
        event.get("forecast")
    )

    if actual is None or forecast is None:
        return None

    return actual - forecast


# ============================================================
# DETECTION D'UNE ALERTE
# ============================================================

def detect_alert(event):

    impact = normalize_impact(
        event.get("impact")
    )

    surprise = calculate_surprise(
        event
    )

    title = event.get(
        "title",
        "Annonce économique"
    )

    # --------------------------------------------------------
    # IMPACT FORT
    # --------------------------------------------------------

    if impact == "FORT":

        if surprise is not None:

            if abs(surprise) >= 1:

                return {
                    "level": "CRITIQUE",

                    "message": (
                        f"{title} | "
                        f"Impact FORT | "
                        f"Surprise : "
                        f"{surprise:+.2f}"
                    )
                }

        return {
            "level": "FORT",

            "message": (
                f"{title} | "
                f"Impact FORT"
            )
        }

    # --------------------------------------------------------
    # SURPRISE IMPORTANTE
    # --------------------------------------------------------

    if surprise is not None:

        if abs(surprise) >= 2:

            return {
                "level": "SURPRISE",

                "message": (
                    f"{title} | "
                    f"Surprise importante : "
                    f"{surprise:+.2f}"
                )
            }

    return None


# ============================================================
# TRAITEMENT DES ALERTES
# ============================================================

def process_alerts(events):

    new_alerts = []

    for event in events:

        alert = detect_alert(
            event
        )

        if not alert:
            continue

        external_id = event.get(
            "external_id"
        )

        if not external_id:
            continue

        # ----------------------------------------------------
        # VERIFICATION DOUBLON
        # ----------------------------------------------------

        if alert_already_processed(
            external_id
        ):

            continue

        # ----------------------------------------------------
        # ENREGISTREMENT
        # ----------------------------------------------------

        saved = save_alert(
            external_id,
            alert["level"],
            alert["message"]
        )

        if saved:

            new_alerts.append(
                alert
            )

    return new_alerts


# ============================================================
# AFFICHAGE DES NOUVELLES ALERTES
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
    print("🚨 NOUVELLES ALERTES HEXAPULSE")
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
    print("HEXAPULSE BOT — SYNCHRONISATION")
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
        # SAUVEGARDE DES EVENEMENTS
        # ----------------------------------------------------

        saved = save_events(
            events
        )

        # ----------------------------------------------------
        # NETTOYAGE
        # ----------------------------------------------------

        cleanup_old_events()

        cleanup_alert_history()

        # ----------------------------------------------------
        # TRAITEMENT DES ALERTES
        # ----------------------------------------------------

        alerts = process_alerts(
            events
        )

        display_alerts(
            alerts
        )

        # ----------------------------------------------------
        # RAPPORT
        # ----------------------------------------------------

        now = datetime.now().strftime(
            "%H:%M:%S"
        )

        print()

        print(
            f"[{now}] "
            f"Synchronisation terminée."
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
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    init_database()

    print()
    print("=" * 60)
    print("🚀 HEXAPULSE BOT DÉMARRÉ")
    print("=" * 60)

    print()

    print(
        "Synchronisation automatique "
        "toutes les 15 minutes."
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

            time.sleep(
                INTERVAL
            )

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