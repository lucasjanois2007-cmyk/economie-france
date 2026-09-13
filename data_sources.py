import hashlib
import requests

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURATION
# ============================================================

BIQUOTE_URL = "https://biquote.io/api/calendar"

EUROPE_CODES = {
    "FR",
    "EU",
    "DE",
    "IT",
    "ES",
    "BE",
    "NL",
    "PT",
    "IE",
    "AT",
    "GR",
    "FI",
    "SE",
    "DK",
    "NO",
    "CH",
    "GB",
}

REQUEST_TIMEOUT = 20

UTC_TZ = timezone.utc


# ============================================================
# OUTILS
# ============================================================

def clean_value(value):
    """
    Nettoie une valeur reçue depuis une source externe.
    """
    if value is None:
        return ""

    return str(value).strip()


def normalize_impact(impact):
    """
    Transforme les différents formats d'impact
    en FAIBLE / MOYEN / FORT.
    """
    value = clean_value(impact).lower()

    if value in {
        "high",
        "fort",
        "forte",
        "3",
        "3.0",
        "red",
    }:
        return "FORT"

    if value in {
        "medium",
        "moyen",
        "moyenne",
        "2",
        "2.0",
        "orange",
    }:
        return "MOYEN"

    return "FAIBLE"


def normalize_country(value):
    """
    Normalise le code pays.
    """
    return clean_value(value).upper()


def normalize_date(value):
    """
    Normalise une date d'événement en ISO 8601 UTC.

    Objectif :
        2026-09-13 08:00:00
        ->
        2026-09-13T08:00:00+00:00

    Si la date reçue contient déjà un fuseau horaire,
    celui-ci est respecté puis converti en UTC.

    Si la date ne contient aucun fuseau horaire,
    elle est considérée comme UTC.
    """

    if value is None:
        return ""

    text = clean_value(value)

    if not text:
        return ""

    # --------------------------------------------------------
    # Nettoyage léger
    # --------------------------------------------------------

    text = text.replace("Z", "+00:00")

    # Certains formats utilisent un espace entre date et heure.
    # fromisoformat() accepte ce format.
    try:
        parsed = datetime.fromisoformat(text)

    except ValueError:

        # ----------------------------------------------------
        # Formats courants supplémentaires
        # ----------------------------------------------------

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ]

        parsed = None

        for date_format in formats:
            try:
                parsed = datetime.strptime(
                    text,
                    date_format
                )
                break

            except ValueError:
                continue

        if parsed is None:
            print(
                "[DATA] Date impossible à interpréter :",
                text
            )
            return text

    # --------------------------------------------------------
    # Si aucune timezone n'est fournie
    # --------------------------------------------------------

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=UTC_TZ
        )

    # --------------------------------------------------------
    # Conversion systématique en UTC
    # --------------------------------------------------------

    parsed = parsed.astimezone(UTC_TZ)

    return parsed.isoformat()


def normalize_title(value):
    """
    Normalise le titre pour éviter les doublons
    causés par des différences de casse ou d'espaces.
    """
    text = clean_value(value)

    text = " ".join(text.split())

    return text


# ============================================================
# IDENTIFIANT UNIQUE
# ============================================================

def generate_external_id(
    source,
    title,
    country,
    event_date,
    currency,
):
    """
    Génère un identifiant stable pour un événement.

    Même événement = même ID.
    """

    raw = "|".join([
        clean_value(source).lower(),
        normalize_title(title).lower(),
        normalize_country(country),
        normalize_date(event_date),
        clean_value(currency).upper(),
    ])

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:32]


# ============================================================
# CLE DE DEDOUBLONNAGE
# ============================================================

def generate_deduplication_key(event):
    """
    Clé utilisée pour détecter deux annonces
    représentant le même événement.
    """

    title = normalize_title(
        event.get("title")
    ).lower()

    country = normalize_country(
        event.get("country")
    )

    event_date = normalize_date(
        event.get("event_date")
    )

    currency = clean_value(
        event.get("currency")
    ).upper()

    return "|".join([
        title,
        country,
        event_date,
        currency,
    ])


# ============================================================
# EXTRACTION DES EVENEMENTS
# ============================================================

def extract_events(data):
    """
    Essaie de trouver automatiquement la liste
    des événements dans la réponse BiQuote.
    """

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    possible_keys = [
        "events",
        "data",
        "calendar",
        "results",
        "items",
    ]

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

    return []


# ============================================================
# NORMALISATION D'UN EVENEMENT
# ============================================================

def normalize_event(raw_event):
    """
    Transforme un événement brut en format HexaPulse.
    """

    if not isinstance(raw_event, dict):
        return None

    title = normalize_title(
        raw_event.get("title")
        or raw_event.get("event")
        or raw_event.get("name")
        or ""
    )

    country = normalize_country(
        raw_event.get("country")
        or raw_event.get("country_code")
        or raw_event.get("countryCode")
        or raw_event.get("code")
        or raw_event.get("region")
        or ""
    )

    currency = clean_value(
        raw_event.get("currency")
        or raw_event.get("currency_code")
        or raw_event.get("currencyCode")
        or ""
    ).upper()

    impact = normalize_impact(
        raw_event.get("impact")
        or raw_event.get("importance")
        or raw_event.get("priority")
    )

    event_date = normalize_date(
        raw_event.get("event_date")
        or raw_event.get("datetime")
        or raw_event.get("date")
        or raw_event.get("time")
    )

    actual = clean_value(
        raw_event.get("actual")
    )

    forecast = clean_value(
        raw_event.get("forecast")
        or raw_event.get("consensus")
    )

    previous = clean_value(
        raw_event.get("previous")
    )

    description = clean_value(
        raw_event.get("description")
        or raw_event.get("comment")
        or ""
    )

    if not title:
        return None

    # IMPORTANT :
    # On ne transforme PLUS automatiquement
    # un pays inconnu en "EU".

    event = {
        "title": title,
        "country": country,
        "currency": currency,
        "impact": impact,
        "event_date": event_date,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "description": description,
        "source": "BiQuote",
        "created_at": datetime.now(
            UTC_TZ
        ).isoformat(),
    }

    event["external_id"] = generate_external_id(
        source=event["source"],
        title=event["title"],
        country=event["country"],
        event_date=event["event_date"],
        currency=event["currency"],
    )

    return event


# ============================================================
# FILTRE EUROPE
# ============================================================

def is_european_event(event):
    """
    Vérifie si l'événement appartient à notre zone surveillée.
    """

    country = normalize_country(
        event.get("country")
    )

    return country in EUROPE_CODES


# ============================================================
# DEDOUBLONNAGE
# ============================================================

def deduplicate_events(events):
    """
    Supprime les événements identiques.
    """

    unique_events = []
    seen = set()

    duplicates = 0

    for event in events:

        key = generate_deduplication_key(
            event
        )

        if key in seen:
            duplicates += 1
            continue

        seen.add(key)
        unique_events.append(event)

    return unique_events, duplicates


# ============================================================
# BIQUOTE
# ============================================================

def fetch_biquote():
    """
    Récupère les événements depuis BiQuote.
    """

    print("[DATA] Interrogation de BiQuote...")

    try:

        response = requests.get(
            BIQUOTE_URL,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        print("[DATA] BiQuote : données reçues.")

        return data

    except requests.RequestException as error:

        print(
            "[DATA] Erreur BiQuote :",
            error
        )

        return None

    except ValueError as error:

        print(
            "[DATA] Réponse JSON invalide :",
            error
        )

        return None


# ============================================================
# COLLECTE BIQUOTE
# ============================================================

def collect_biquote_events():
    """
    Récupère, normalise et filtre les événements BiQuote.
    """

    data = fetch_biquote()

    if data is None:
        return []

    raw_events = extract_events(data)

    # ========================================================
    # DEBUG DES CHAMPS PAYS
    # ========================================================

    print()
    print("[DEBUG] Exemples de pays reçus par BiQuote :")

    for raw_event in raw_events[:20]:

        if not isinstance(raw_event, dict):
            continue

        print(
            "country=",
            raw_event.get("country"),
            "| country_code=",
            raw_event.get("country_code"),
            "| countryCode=",
            raw_event.get("countryCode"),
            "| code=",
            raw_event.get("code"),
            "| region=",
            raw_event.get("region"),
        )

    print()

    # ========================================================
    # TOTAL MONDIAL
    # ========================================================

    print(
        f"[DATA] Total mondial : {len(raw_events)}"
    )

    events = []

    # ========================================================
    # NORMALISATION + FILTRE EUROPE
    # ========================================================

    for raw_event in raw_events:

        event = normalize_event(
            raw_event
        )

        if event is None:
            continue

        if not is_european_event(event):
            continue

        events.append(event)

    print(
        f"[DATA] Événements Europe : {len(events)}"
    )

    # ========================================================
    # DEDOUBLONNAGE
    # ========================================================

    unique_events, duplicates = (
        deduplicate_events(events)
    )

    print(
        f"[DATA] Doublons supprimés : {duplicates}"
    )

    print(
        f"[DATA] Événements uniques : "
        f"{len(unique_events)}"
    )

    return unique_events


# ============================================================
# DATA ENGINE
# ============================================================

def collect_all_sources():
    """
    Point d'entrée principal du Data Engine HexaPulse.
    """

    events = collect_biquote_events()

    print()
    print(
        f"[DATA ENGINE] "
        f"{len(events)} événement(s) prêt(s)."
    )

    return events


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HEXAPULSE DATA ENGINE")
    print("=" * 60)
    print()

    events = collect_all_sources()

    print()
    print(
        f"{len(events)} événement(s) européen(s) unique(s)."
    )
    print()

    for event in events[:10]:

        print(
            f"- {event['title']} "
            f"| {event['country']} "
            f"| {event['impact']} "
            f"| {event['event_date']}"
        )

    print()