from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import re

from database import (
    init_database,
    save_events,
    get_events
)

from intelligence import analyze_event
from data_sources import collect_all_sources


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "HexaPulse"
APP_VERSION = "2.2.0"

PARIS_TZ = ZoneInfo("Europe/Paris")

CACHE_DURATION = 15 * 60


# ============================================================
# CHEMINS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"

INDEX_FILE = STATIC_DIR / "index.html"


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description="Economic Intelligence",
    version=APP_VERSION
)


# ============================================================
# FICHIERS STATIQUES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ============================================================
# SYNCHRONISATION
# ============================================================

last_sync_time = None


# ============================================================
# INITIALISATION
# ============================================================

init_database()


# ============================================================
# HORLOGE
# ============================================================

def paris_now():
    return datetime.now(PARIS_TZ)


def utc_now():
    return datetime.now(timezone.utc)


# ============================================================
# NETTOYAGE TEXTE
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    text = str(value)

    # Décodage HTML plusieurs fois
    import html

    for _ in range(3):
        decoded = html.unescape(text)

        if decoded == text:
            break

        text = decoded

    # Suppression de Markdown parasite
    text = text.replace("**", "")
    text = text.replace("__", "")

    # Suppression de quelques caractères d'échappement
    text = text.replace("\\*", "*")
    text = text.replace("\\_", "_")
    text = text.replace("\\`", "`")
    text = text.replace("\\<", "<")
    text = text.replace("\\>", ">")
    text = text.replace("\\#", "#")

    # Espaces multiples
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# NORMALISATION DES EVENEMENTS
# ============================================================

def clean_event(event):
    """
    Nettoie un événement déjà normalisé par data_sources.py.
    """

    if not isinstance(event, dict):
        return None

    cleaned = dict(event)

    cleaned["title"] = clean_text(
        event.get("title", "Annonce économique")
    )

    cleaned["country"] = str(
        event.get("country", "")
    ).upper().strip()

    cleaned["currency"] = str(
        event.get("currency", "")
    ).upper().strip()

    cleaned["impact"] = clean_text(
        event.get("impact", "Faible")
    )

    cleaned["actual"] = clean_text(
        event.get("actual", "")
    )

    cleaned["forecast"] = clean_text(
        event.get("forecast", "")
    )

    cleaned["previous"] = clean_text(
        event.get("previous", "")
    )

    cleaned["description"] = clean_text(
        event.get("description", "")
    )

    cleaned["source"] = clean_text(
        event.get("source", "BiQuote")
    )

    return cleaned


# ============================================================
# SYNCHRONISATION DES DONNEES
# ============================================================

def sync_events(force=False):
    global last_sync_time

    now = utc_now()

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    if not force and last_sync_time:

        elapsed = (
            now - last_sync_time
        ).total_seconds()

        if elapsed < CACHE_DURATION:

            current_events = get_events(
                limit=200
            )

            return {
                "success": True,
                "synced": False,
                "reason": "cache",
                "count": len(current_events)
            }

    # --------------------------------------------------------
    # RECUPERATION VIA DATA SOURCES
    # --------------------------------------------------------

    try:

        print()
        print("[HEXAPULSE] Synchronisation des données...")
        print()

        events = collect_all_sources()

    except Exception as error:

        print(
            "[HEXAPULSE] Erreur récupération données :",
            error
        )

        return {
            "success": False,
            "synced": False,
            "reason": "source_error",
            "count": len(
                get_events(limit=200)
            )
        }

    # --------------------------------------------------------
    # AUCUNE DONNEE
    # --------------------------------------------------------

    if not events:

        print(
            "[HEXAPULSE] Aucun événement reçu."
        )

        return {
            "success": False,
            "synced": False,
            "reason": "api_empty",
            "count": len(
                get_events(limit=200)
            )
        }

    # --------------------------------------------------------
    # NETTOYAGE
    # --------------------------------------------------------

    cleaned_events = []

    for event in events:

        cleaned = clean_event(event)

        if cleaned:
            cleaned_events.append(cleaned)

    # --------------------------------------------------------
    # SAUVEGARDE
    # --------------------------------------------------------

    saved = save_events(
        cleaned_events
    )

    last_sync_time = now

    print(
        f"[HEXAPULSE] Événements reçus : "
        f"{len(cleaned_events)}"
    )

    print(
        f"[HEXAPULSE] Événements enregistrés : "
        f"{saved}"
    )

    print()

    return {
        "success": True,
        "synced": True,
        "count": len(cleaned_events),
        "saved": saved
    }


# ============================================================
# INTELLIGENCE HEXAPULSE
# ============================================================

def enrich_events_with_intelligence(events):

    enriched_events = []

    for event in events:

        try:

            analysis = analyze_event(
                event
            )

            enriched_event = dict(event)

            enriched_event["hexapulse_score"] = (
                analysis["score"]
            )

            enriched_event["indicator_type"] = (
                analysis["indicator_type"]
            )

            enriched_event["surprise"] = (
                analysis["surprise"]
            )

            enriched_event["direction"] = (
                analysis["direction"]
            )

            enriched_event["assets"] = (
                analysis["assets"]
            )

            enriched_event["alert_level"] = (
                analysis["alert_level"]
            )

            enriched_event["intelligence_message"] = (
                clean_text(
                    analysis["message"]
                )
            )

            enriched_events.append(
                enriched_event
            )

        except Exception as error:

            print(
                "[INTELLIGENCE] Erreur analyse :",
                error
            )

            enriched_events.append(
                event
            )

    return enriched_events


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.get("/")
def home():

    if not INDEX_FILE.exists():

        return {
            "error": "index.html introuvable",
            "path": str(INDEX_FILE),
            "static_directory": str(STATIC_DIR)
        }

    return FileResponse(
        path=str(INDEX_FILE),
        media_type="text/html"
    )


# ============================================================
# ALERTES
# ============================================================

@app.get("/api/alerts")
def api_alerts():

    events = get_events(
        limit=200
    )

    enriched_events = (
        enrich_events_with_intelligence(
            events
        )
    )

    alerts = []

    seen_alerts = set()

    for event in enriched_events:

        alert_level = event.get(
            "alert_level"
        )

        # Seulement les vraies alertes
        if alert_level not in {
            "IMPORTANT",
            "CRITIQUE"
        }:
            continue

        title = clean_text(
            event.get(
                "title",
                "Annonce économique"
            )
        )

        country = str(
            event.get(
                "country",
                ""
            )
        ).strip().upper()

        event_date = str(
            event.get(
                "event_date",
                ""
            )
        ).strip()

        # Déduplication
        alert_key = (
            re.sub(
                r"\s+",
                " ",
                title.lower()
            ).strip(),
            country,
            event_date
        )

        if alert_key in seen_alerts:
            continue

        seen_alerts.add(
            alert_key
        )

        message = clean_text(
            event.get(
                "intelligence_message",
                ""
            )
        )

        alerts.append({

            "type": "intelligence",

            "level": alert_level,

            "title": title,

            "country": country,

            "event_date": event_date,

            "score": event.get(
                "hexapulse_score",
                0
            ),

            "indicator_type": event.get(
                "indicator_type",
                "AUTRE"
            ),

            "surprise": event.get(
                "surprise"
            ),

            "direction": event.get(
                "direction",
                "NEUTRE"
            ),

            "assets": event.get(
                "assets",
                []
            ),

            "message": message
        })

    # Tri
    alerts.sort(
        key=lambda alert: (
            0
            if alert["level"] == "CRITIQUE"
            else 1,

            -int(
                alert.get(
                    "score",
                    0
                )
            )
        )
    )

    return {
        "success": True,
        "count": len(alerts),
        "alerts": alerts[:20]
    }


# ============================================================
# PREMIUM
# ============================================================

@app.get("/api/premium")
def api_premium():

    return {

        "success": True,

        "premium": {

            "enabled": True,

            "status": "preview",

            "name": "HexaPulse Premium",

            "price": "4.99 EUR",

            "features": [

                {
                    "id": "custom_alerts",
                    "name": "Alertes personnalisées",
                    "description":
                        "Choisis les pays, indicateurs et niveaux d’impact à surveiller."
                },

                {
                    "id": "advanced_analysis",
                    "name": "Analyse avancée",
                    "description":
                        "Analyse automatique des annonces économiques."
                },

                {
                    "id": "watchlists",
                    "name": "Watchlists",
                    "description":
                        "Surveille tes indicateurs et thèmes favoris."
                },

                {
                    "id": "water_intelligence",
                    "name": "Water Intelligence",
                    "description":
                        "Surveillance approfondie du secteur de l’eau."
                },

                {
                    "id": "surprise_alerts",
                    "name": "Surprise Alerts",
                    "description":
                        "Détection des écarts entre données et prévisions."
                },

                {
                    "id": "advanced_score",
                    "name": "HexaPulse Score avancé",
                    "description":
                        "Score économique enrichi et analyse directionnelle."
                }
            ]
        }
    }


# ============================================================
# PREMIUM — WATCHLIST
# ============================================================

@app.get("/api/premium/watchlist")
def premium_watchlist():

    return {

        "success": True,

        "premium": True,

        "watchlist": [

            {
                "name": "Inflation",
                "type": "indicator",
                "status": "active"
            },

            {
                "name": "Taux directeurs",
                "type": "central_bank",
                "status": "active"
            },

            {
                "name": "Marché du travail",
                "type": "employment",
                "status": "active"
            },

            {
                "name": "Water Intelligence",
                "type": "sector",
                "status": "active"
            }
        ]
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {

        "status": "ok",

        "service": APP_NAME,

        "version": APP_VERSION,

        "timezone": "Europe/Paris"
    }


# ============================================================
# HEURE PARIS
# ============================================================

@app.get("/api/time")
def api_time():

    now = paris_now()

    return {

        "success": True,

        "timezone": "Europe/Paris",

        "datetime": now.isoformat(),

        "date": now.strftime(
            "%d/%m/%Y"
        ),

        "time": now.strftime(
            "%H:%M"
        )
    }


# ============================================================
# ANNONCES
# ============================================================

@app.get("/api/annonces")
def api_annonces():

    sync_result = sync_events()

    events = get_events(
        limit=200
    )

    events = (
        enrich_events_with_intelligence(
            events
        )
    )

    return {

        "success": True,

        "service": APP_NAME,

        "timezone": "Europe/Paris",

        "count": len(events),

        "updated_at":
            paris_now().isoformat(),

        "sync":
            sync_result,

        "events":
            events
    }


# ============================================================
# EVENTS
# ============================================================

@app.get("/api/events")
def api_events():

    return api_annonces()


# ============================================================
# SYNCHRONISATION FORCEE
# ============================================================

@app.get("/api/sync")
def api_sync():

    result = sync_events(
        force=True
    )

    events = get_events(
        limit=200
    )

    events = (
        enrich_events_with_intelligence(
            events
        )
    )

    return {

        "success":
            result.get(
                "success",
                False
            ),

        "sync":
            result,

        "count":
            len(events),

        "timezone":
            "Europe/Paris",

        "updated_at":
            paris_now().isoformat(),

        "events":
            events
    }


# ============================================================
# API INFORMATIONS
# ============================================================

@app.get("/api")
def api_info():

    return {

        "name": APP_NAME,

        "version": APP_VERSION,

        "description":
            "Economic Intelligence",

        "timezone":
            "Europe/Paris",

        "premium": True,

        "intelligence": True,

        "endpoints": [

            "/",
            "/health",
            "/api",
            "/api/time",
            "/api/annonces",
            "/api/events",
            "/api/sync",
            "/api/alerts",
            "/api/premium",
            "/api/premium/watchlist"
        ]
    }


# ============================================================
# LANCEMENT LOCAL
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )