from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import (
    init_database,
    get_events,
    get_event_count,
    get_alert_history,
)
from data_sources import collect_all_sources
from intelligence import analyze_event


# ============================================================
# HEXAPULSE
# ============================================================

APP_NAME = "HexaPulse"
APP_VERSION = "3.0.0"

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

PARIS_TZ = ZoneInfo("Europe/Paris")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="HexaPulse — Economic Intelligence API",
)


# ============================================================
# INITIALISATION
# ============================================================

init_database()


# ============================================================
# FRONTEND
# ============================================================

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )


@app.get("/", include_in_schema=False)
def homepage():
    index_file = STATIC_DIR / "index.html"

    if index_file.exists():
        return FileResponse(index_file)

    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
    }


# ============================================================
# OUTILS
# ============================================================

def paris_now():
    return datetime.now(PARIS_TZ)


def enrich_event(event):
    """
    Sécurité supplémentaire :
    si une ancienne ligne SQLite ne possède pas encore
    les données d'intelligence, on les recalcule ici.
    """

    event = dict(event)

    if not event.get("category") or event.get("score") is None:
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

    return event


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "hexapulse",
        "version": APP_VERSION,
        "timezone": "Europe/Paris",
        "server_time": paris_now().isoformat(),
    }


# ============================================================
# TIME
# ============================================================

@app.get("/api/time")
def api_time():
    now = paris_now()

    return {
        "success": True,
        "timezone": "Europe/Paris",
        "datetime": now.isoformat(),
        "date": now.strftime("%d/%m/%Y"),
        "time": now.strftime("%H:%M"),
    }


# ============================================================
# ANNONCES
# ============================================================

@app.get("/api/annonces")
def api_annonces(limit: int = 500):
    events = get_events(limit)

    enriched_events = [
        enrich_event(event)
        for event in events
    ]

    return {
        "success": True,
        "count": len(enriched_events),
        "total": get_event_count(),
        "updated_at": paris_now().isoformat(),
        "timezone": "Europe/Paris",
        "events": enriched_events,
    }


# ============================================================
# EVENTS
# ============================================================

@app.get("/api/events")
def api_events(limit: int = 500):
    events = get_events(limit)

    enriched_events = [
        enrich_event(event)
        for event in events
    ]

    return {
        "success": True,
        "count": len(enriched_events),
        "events": enriched_events,
    }


# ============================================================
# ALERTES
# ============================================================

@app.get("/api/alerts")
def api_alerts(limit: int = 100):
    alerts = get_alert_history(limit)

    return {
        "success": True,
        "count": len(alerts),
        "alerts": alerts,
        "timezone": "Europe/Paris",
    }


# ============================================================
# PREMIUM
# ============================================================

@app.get("/api/premium")
def api_premium():
    return {
        "success": True,
        "available": True,
        "message": "HexaPulse Premium",
        "features": [
            "Alertes économiques avancées",
            "Analyse intelligente",
            "Scores d'impact",
            "Surprises économiques",
            "Actifs concernés",
            "Biais monétaire",
            "Water Watchlist",
        ],
    }


@app.get("/api/premium/watchlist")
def api_premium_watchlist():
    return {
        "success": True,
        "watchlist": [
            {
                "asset": "EUR/USD",
                "category": "TAUX",
            },
            {
                "asset": "CAC 40",
                "category": "ACTIVITÉ",
            },
            {
                "asset": "S&P 500",
                "category": "CROISSANCE",
            },
            {
                "asset": "Obligations",
                "category": "TAUX",
            },
        ],
    }


# ============================================================
# SYNCHRONISATION MANUELLE
# ============================================================

@app.get("/api/sync")
def api_sync():
    """
    Endpoint de test pour récupérer les données.
    Le bot reste le moteur principal de synchronisation.
    """

    try:
        events = collect_all_sources()

        enriched_events = []

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

            enriched_events.append(event)

        return {
            "success": True,
            "count": len(enriched_events),
            "events": enriched_events,
            "timezone": "Europe/Paris",
            "updated_at": paris_now().isoformat(),
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# ============================================================
# API INFO
# ============================================================

@app.get("/api")
def api_info():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
        "timezone": "Europe/Paris",
        "endpoints": [
            "/health",
            "/api/time",
            "/api/annonces",
            "/api/events",
            "/api/alerts",
            "/api/premium",
            "/api/premium/watchlist",
            "/api/sync",
        ],
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
        reload=True,
    )