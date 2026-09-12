import requests
from datetime import datetime, timezone
import hashlib


# ============================================================
# CONFIGURATION
# ============================================================

BIQUOTE_URL = "https://biquote.io/api/calendar"
TIMEOUT = 30

EUROPE_CODES = {
    "FR",  # France
    "EU",  # Union européenne
    "DE",  # Allemagne
    "IT",  # Italie
    "ES",  # Espagne
    "BE",  # Belgique
    "NL",  # Pays-Bas
    "PT",  # Portugal
    "IE",  # Irlande
    "AT",  # Autriche
    "GR",  # Grèce
    "FI",  # Finlande
    "SE",  # Suède
    "DK",  # Danemark
    "NO",  # Norvège
    "CH",  # Suisse
    "GB",  # Royaume-Uni
}


# ============================================================
# REQUÊTE API
# ============================================================

def fetch_json(url, params=None):
    """
    Récupère une réponse JSON depuis une API.
    """

    try:
        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "HexaPulse/1.0"
            }
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        print(f"[DATA] Erreur API : {error}")

        return None

    except ValueError:

        print("[DATA] Réponse JSON invalide.")

        return None


# ============================================================
# BIQUOTE
# ============================================================

def fetch_biquote():
    """
    Récupère le calendrier économique BiQuote.
    """

    print("[DATA] Interrogation de BiQuote...")

    data = fetch_json(BIQUOTE_URL)

    if data is None:

        print("[DATA] BiQuote indisponible.")

        return []

    print("[DATA] BiQuote : données reçues.")

    return data


# ============================================================
# NORMALISATION
# ============================================================

def normalize_source_event(event):

    if not isinstance(event, dict):
        return None

    title = (
        event.get("title")
        or event.get("name")
        or event.get("event")
        or "Annonce économique"
    )

    country = (
        event.get("country")
        or event.get("country_code")
        or event.get("countryCode")
        or ""
    )

    currency = (
        event.get("currency")
        or event.get("currency_code")
        or ""
    )

    impact = (
        event.get("impact")
        or event.get("importance")
        or "FAIBLE"
    )

    event_date = (
        event.get("event_date")
        or event.get("date")
        or event.get("datetime")
        or event.get("time")
    )

    actual = (
        event.get("actual")
        or event.get("value")
    )

    forecast = (
        event.get("forecast")
        or event.get("consensus")
        or event.get("expected")
    )

    previous = (
        event.get("previous")
        or event.get("prior")
    )

    description = (
        event.get("description")
        or event.get("details")
        or ""
    )

    return {
        "title": title,
        "country": str(country).upper(),
        "currency": currency,
        "impact": impact,
        "event_date": event_date,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "description": description,
        "source": "BiQuote",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# EXTRACTION DES ÉVÉNEMENTS
# ============================================================

def extract_events(data):

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    possible_keys = [
        "events",
        "data",
        "calendar",
        "results",
        "announcements"
    ]

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):

            for nested_key in possible_keys:

                nested_value = value.get(nested_key)

                if isinstance(nested_value, list):
                    return nested_value

    return []


# ============================================================
# ID UNIQUE
# ============================================================

def generate_external_id(event):

    raw = "|".join([
        str(event.get("source", "")),
        str(event.get("title", "")),
        str(event.get("country", "")),
        str(event.get("event_date", ""))
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# FILTRE EUROPE
# ============================================================

def filter_europe(events):

    filtered = []

    for event in events:

        country = str(
            event.get("country", "")
        ).upper().strip()

        if country in EUROPE_CODES:

            filtered.append(event)

    return filtered


# ============================================================
# COLLECTE GLOBALE
# ============================================================

def collect_all_sources():

    all_events = []


    # --------------------------------------------------------
    # BIQUOTE
    # --------------------------------------------------------

    biquote_data = fetch_biquote()

    biquote_events = extract_events(
        biquote_data
    )

    for event in biquote_events:

        normalized = normalize_source_event(event)

        if normalized:

            normalized["external_id"] = (
                generate_external_id(normalized)
            )

            all_events.append(normalized)


    print(
        f"[DATA] Total mondial : "
        f"{len(all_events)}"
    )


    # --------------------------------------------------------
    # FILTRE EUROPE
    # --------------------------------------------------------

    europe_events = filter_europe(
        all_events
    )


    print(
        f"[DATA] Événements Europe : "
        f"{len(europe_events)}"
    )


    return europe_events


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HEXAPULSE DATA ENGINE")
    print("=" * 60)
    print()

    events = collect_all_sources()

    print()

    if not events:

        print("Aucun événement européen récupéré.")

    else:

        print(
            f"{len(events)} événement(s) européen(s)."
        )

        print()

        for event in events[:10]:

            print(
                f"- {event['title']} "
                f"| {event['country']} "
                f"| {event['impact']}"
            )

    print()