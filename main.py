from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import hashlib
import requests

from database import (
    init_database,
    save_events,
    get_events
)


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "HexaPulse"
APP_VERSION = "2.0.0"

BIQUOTE_URL = "https://biquote.io/api/calendar"

PARIS_TZ = ZoneInfo("Europe/Paris")

CACHE_DURATION = 15 * 60

EUROPE_CODES = {
    "FR", "EU", "DE", "IT", "ES", "BE", "NL",
    "PT", "IE", "AT", "GR", "FI", "SE", "DK",
    "NO", "CH", "GB"
}


# ============================================================
# CHEMINS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description="Economic Intelligence",
    version=APP_VERSION
)


app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static"
)


# Dernière synchronisation
last_sync_time = None


# ============================================================
# INITIALISATION
# ============================================================

init_database()


# ============================================================
# HORLOGE
# ============================================================

def paris_now():

    return datetime.now(
        PARIS_TZ
    )


def utc_now():

    return datetime.now(
        timezone.utc
    )


# ============================================================
# NORMALISATION DATE
# ============================================================

def normalize_datetime(value):

    if not value:
        return None

    try:

        value = str(
            value
        ).strip()

        if value.endswith("Z"):

            value = (
                value[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            value
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            PARIS_TZ
        ).isoformat()

    except Exception:

        return None


# ============================================================
# NORMALISATION IMPACT
# ============================================================

def normalize_impact(value):

    if value is None:

        return "Faible"

    text = str(
        value
    ).strip().lower()

    if text in {
        "high",
        "fort",
        "forte",
        "important",
        "important!",
        "3",
        "3.0",
        "red"
    }:

        return "Fort"

    if text in {
        "medium",
        "moderate",
        "moyen",
        "moyenne",
        "2",
        "2.0",
        "orange"
    }:

        return "Moyen"

    return "Faible"


# ============================================================
# IDENTIFIANT UNIQUE
# ============================================================

def generate_external_id(event):

    existing_id = (
        event.get("id")
        or event.get("event_id")
        or event.get("uuid")
        or event.get("external_id")
    )

    if existing_id:

        return str(
            existing_id
        )

    raw = "|".join([
        str(
            event.get(
                "country",
                ""
            )
        ),

        str(
            event.get(
                "title",
                ""
            )
        ),

        str(
            event.get(
                "date",
                ""
            )
        ),

        str(
            event.get(
                "datetime",
                ""
            )
        ),

        str(
            event.get(
                "time",
                ""
            )
        )
    ])

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:32]


# ============================================================
# NORMALISATION EVENEMENT
# ============================================================

def normalize_event(event):

    if not isinstance(
        event,
        dict
    ):

        return None


    title = (
        event.get("title")
        or event.get("name")
        or event.get("event")
        or event.get("label")
        or "Annonce économique"
    )


    country = (
        event.get("country")
        or event.get("country_code")
        or event.get("code")
        or ""
    )

    country = str(
        country
    ).upper().strip()


    currency = (
        event.get("currency")
        or event.get("curr")
        or ""
    )

    currency = str(
        currency
    ).upper().strip()


    impact = normalize_impact(
        event.get("impact")
        or event.get("importance")
        or event.get("impact_level")
        or event.get("priority")
    )


    raw_date = (
        event.get("datetime")
        or event.get("date")
        or event.get("timestamp")
        or event.get("time")
    )


    event_date = normalize_datetime(
        raw_date
    )


    description = (
        event.get("description")
        or event.get("detail")
        or event.get("details")
        or ""
    )


    actual = event.get(
        "actual"
    )

    forecast = event.get(
        "forecast"
    )

    previous = event.get(
        "previous"
    )


    external_id = generate_external_id(
        event
    )


    source = (
        event.get("source")
        or "BiQuote"
    )


    return {

        "external_id": external_id,

        "title": str(
            title
        ),

        "country": country,

        "currency": currency,

        "impact": impact,

        "event_date": event_date,

        "actual": (
            ""
            if actual is None
            else str(actual)
        ),

        "forecast": (
            ""
            if forecast is None
            else str(forecast)
        ),

        "previous": (
            ""
            if previous is None
            else str(previous)
        ),

        "description": str(
            description
        ),

        "source": str(
            source
        ),

        "created_at":
            utc_now().isoformat()
    }


# ============================================================
# EXTRACTION EVENEMENTS
# ============================================================

def extract_events(data):

    if isinstance(
        data,
        list
    ):

        return data


    if not isinstance(
        data,
        dict
    ):

        return []


    possible_keys = [
        "events",
        "annonces",
        "data",
        "calendar",
        "results",
        "items"
    ]


    for key in possible_keys:

        value = data.get(
            key
        )


        if isinstance(
            value,
            list
        ):

            return value


        if isinstance(
            value,
            dict
        ):

            for nested_key in possible_keys:

                nested_value = value.get(
                    nested_key
                )

                if isinstance(
                    nested_value,
                    list
                ):

                    return nested_value


    return []


# ============================================================
# RECUPERATION BIQUOTE
# ============================================================

def fetch_external_events():

    try:

        response = requests.get(

            BIQUOTE_URL,

            timeout=15,

            headers={
                "User-Agent":
                    "HexaPulse/2.0"
            }
        )


        response.raise_for_status()


        data = response.json()


        raw_events = extract_events(
            data
        )


        normalized_events = []


        for event in raw_events:

            normalized = normalize_event(
                event
            )


            if not normalized:

                continue


            country = normalized[
                "country"
            ]


            if country not in EUROPE_CODES:

                continue


            if not normalized[
                "event_date"
            ]:

                continue


            normalized_events.append(
                normalized
            )


        return normalized_events


    except requests.RequestException as error:

        print(
            "Erreur connexion API BiQuote:",
            error
        )

        return []


    except Exception as error:

        print(
            "Erreur récupération annonces:",
            error
        )

        return []


# ============================================================
# SYNCHRONISATION
# ============================================================

def sync_events(
    force=False
):

    global last_sync_time


    now = utc_now()


    if (
        not force
        and last_sync_time
    ):

        elapsed = (
            now
            - last_sync_time
        ).total_seconds()


        if elapsed < CACHE_DURATION:

            return {

                "success": True,

                "synced": False,

                "reason": "cache",

                "count":
                    len(
                        get_events()
                    )
            }


    events = fetch_external_events()


    if not events:

        return {

            "success": False,

            "synced": False,

            "reason": "api_empty",

            "count":
                len(
                    get_events()
                )
        }


    saved = save_events(
        events
    )


    last_sync_time = now


    return {

        "success": True,

        "synced": True,

        "count": len(
            events
        ),

        "saved": saved
    }


# ============================================================
# ALERTES
# ============================================================

@app.get("/api/alerts")
def api_alerts():

    events = get_events(
        limit=200
    )

    alerts = []


    for event in events:

        impact = str(
            event.get(
                "impact"
            )
            or ""
        ).lower()


        actual = event.get(
            "actual"
        )

        forecast = event.get(
            "forecast"
        )


        # ----------------------------------------------------
        # IMPACT FORT
        # ----------------------------------------------------

        if impact in {
            "high",
            "fort",
            "3",
            "3.0"
        }:

            alerts.append({

                "type": "impact",

                "level": "FORT",

                "title": event.get(
                    "title",
                    "Annonce économique"
                ),

                "country": event.get(
                    "country",
                    ""
                ),

                "event_date":
                    event.get(
                        "event_date"
                    ),

                "message":
                    "Annonce économique "
                    "à fort impact potentiel."
            })


        # ----------------------------------------------------
        # SURPRISE
        # ----------------------------------------------------

        try:

            if actual and forecast:

                actual_number = float(
                    str(actual)
                    .replace(",", ".")
                    .replace("%", "")
                    .strip()
                )


                forecast_number = float(
                    str(forecast)
                    .replace(",", ".")
                    .replace("%", "")
                    .strip()
                )


                difference = (
                    actual_number
                    - forecast_number
                )


                if abs(
                    difference
                ) >= 1:

                    alerts.append({

                        "type":
                            "surprise",

                        "level":
                            "SURPRISE",

                        "title":
                            event.get(
                                "title",
                                "Annonce économique"
                            ),

                        "country":
                            event.get(
                                "country",
                                ""
                            ),

                        "event_date":
                            event.get(
                                "event_date"
                            ),

                        "message":
                            (
                                "Écart vs prévision : "
                                f"{difference:+.2f}"
                            )
                    })


        except (
            ValueError,
            TypeError
        ):

            pass


    return {

        "success": True,

        "count": len(
            alerts
        ),

        "alerts":
            alerts[:20]
    }


# ============================================================
# PREMIUM — INFORMATIONS
# ============================================================

@app.get("/api/premium")
def api_premium():

    return {

        "success": True,

        "premium": {

            "enabled": True,

            "status": "preview",

            "name":
                "HexaPulse Premium",

            "features": [

                {
                    "id":
                        "custom_alerts",

                    "name":
                        "Alertes personnalisées",

                    "description":
                        "Choisis les pays, "
                        "indicateurs et niveaux "
                        "d'impact à surveiller."
                },

                {
                    "id":
                        "advanced_analysis",

                    "name":
                        "Analyse avancée",

                    "description":
                        "Analyse automatique "
                        "des annonces économiques."
                },

                {
                    "id":
                        "watchlists",

                    "name":
                        "Watchlists",

                    "description":
                        "Surveille tes indicateurs "
                        "et thèmes favoris."
                },

                {
                    "id":
                        "water_intelligence",

                    "name":
                        "Water Intelligence",

                    "description":
                        "Surveillance approfondie "
                        "du secteur de l'eau."
                },

                {
                    "id":
                        "surprise_alerts",

                    "name":
                        "Surprise Alerts",

                    "description":
                        "Détection des écarts "
                        "entre données et prévisions."
                },

                {
                    "id":
                        "advanced_score",

                    "name":
                        "HexaPulse Score avancé",

                    "description":
                        "Score économique enrichi "
                        "et analyse directionnelle."
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
                "name":
                    "Inflation",

                "type":
                    "indicator",

                "status":
                    "active"
            },

            {
                "name":
                    "Taux directeurs",

                "type":
                    "central_bank",

                "status":
                    "active"
            },

            {
                "name":
                    "Marché du travail",

                "type":
                    "employment",

                "status":
                    "active"
            },

            {
                "name":
                    "Water Intelligence",

                "type":
                    "sector",

                "status":
                    "active"
            }

        ]
    }


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        STATIC_DIR
        / "index.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {

        "status": "ok",

        "service":
            APP_NAME,

        "version":
            APP_VERSION,

        "timezone":
            "Europe/Paris"
    }


# ============================================================
# HEURE PARIS
# ============================================================

@app.get("/api/time")
def api_time():

    now = paris_now()


    return {

        "success": True,

        "timezone":
            "Europe/Paris",

        "datetime":
            now.isoformat(),

        "date":
            now.strftime(
                "%d/%m/%Y"
            ),

        "time":
            now.strftime(
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


    return {

        "success": True,

        "service":
            APP_NAME,

        "timezone":
            "Europe/Paris",

        "count":
            len(events),

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

        "name":
            APP_NAME,

        "version":
            APP_VERSION,

        "description":
            "Economic Intelligence",

        "timezone":
            "Europe/Paris",

        "premium":
            True,

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