"""
HEXAPULSE — MOTEUR D'INTELLIGENCE ÉCONOMIQUE

Analyse les annonces économiques et produit :
- catégorie
- score d'importance
- surprise
- direction potentielle
- actifs concernés
- niveau d'alerte
"""

import re


# ============================================================
# MOTS-CLÉS PAR CATÉGORIE
# ============================================================

CATEGORY_KEYWORDS = {
    "TAUX": [
        "interest rate",
        "interest rates",
        "policy rate",
        "deposit facility",
        "refinancing rate",
        "fed rate",
        "federal funds",
        "rate decision",
        "central bank",
        "ecb",
        "fomc",
        "bank rate",
        "cash rate",
    ],
    "INFLATION": [
        "cpi",
        "inflation",
        "hicp",
        "consumer price",
        "consumer prices",
        "pce",
        "core inflation",
        "harmonised inflation",
    ],
    "EMPLOI": [
        "employment",
        "unemployment",
        "nonfarm payroll",
        "payroll",
        "jobs",
        "jobless",
        "initial claims",
        "employment change",
        "wage",
        "earnings",
    ],
    "CROISSANCE": [
        "gdp",
        "gross domestic product",
        "economic growth",
        "growth rate",
        "industrial production",
        "retail sales",
        "production",
    ],
    "ACTIVITÉ": [
        "pmi",
        "manufacturing pmi",
        "services pmi",
        "composite pmi",
        "business confidence",
        "consumer confidence",
        "economic sentiment",
        "ism",
    ],
    "COMMERCE": [
        "trade balance",
        "trade balance",
        "exports",
        "imports",
        "current account",
    ],
}


# ============================================================
# ACTIFS PAR ZONE
# ============================================================

ASSETS_BY_COUNTRY = {
    "FR": ["EUR/USD", "CAC 40", "S&P 500", "Obligations"],
    "DE": ["EUR/USD", "DAX", "S&P 500", "Obligations"],
    "IT": ["EUR/USD", "FTSE MIB", "S&P 500", "Obligations"],
    "ES": ["EUR/USD", "IBEX 35", "S&P 500", "Obligations"],
    "BE": ["EUR/USD", "CAC 40", "S&P 500", "Obligations"],
    "NL": ["EUR/USD", "AEX", "S&P 500", "Obligations"],
    "PT": ["EUR/USD", "PSI 20", "S&P 500", "Obligations"],
    "IE": ["EUR/USD", "EUR/USD", "S&P 500", "Obligations"],
    "AT": ["EUR/USD", "ATX", "S&P 500", "Obligations"],
    "GR": ["EUR/USD", "ATHEX", "S&P 500", "Obligations"],
    "FI": ["EUR/USD", "OMX Helsinki", "S&P 500", "Obligations"],
    "SE": ["EUR/SEK", "OMX Stockholm", "S&P 500", "Obligations"],
    "DK": ["EUR/DKK", "OMX Copenhagen", "S&P 500", "Obligations"],
    "NO": ["EUR/NOK", "OSEBX", "Brent", "Obligations"],
    "CH": ["EUR/CHF", "SMI", "S&P 500", "Obligations"],
    "GB": ["GBP/USD", "FTSE 100", "S&P 500", "Obligations"],
    "EU": ["EUR/USD", "CAC 40", "DAX", "S&P 500", "Obligations"],
}


# ============================================================
# OUTILS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_number(value):
    """
    Transforme différentes formes de nombres en float.
    Exemples :
    2.50
    2,50
    2.5%
    """
    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    text = text.replace("%", "")
    text = text.replace(",", ".")

    # Supprime les espaces
    text = text.replace(" ", "")

    try:
        return float(text)
    except ValueError:
        return None


# ============================================================
# CATÉGORIE
# ============================================================

def detect_category(event):
    title = clean_text(event.get("title")).lower()
    description = clean_text(event.get("description")).lower()

    text = f"{title} {description}"

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return "AUTRE"


# ============================================================
# IMPORTANCE DE BASE
# ============================================================

def base_score(event, category):
    impact = clean_text(event.get("impact")).upper()

    score = 20

    if impact == "FORT":
        score += 45
    elif impact == "MOYEN":
        score += 25
    elif impact == "FAIBLE":
        score += 10

    important_categories = {
        "TAUX": 25,
        "INFLATION": 20,
        "EMPLOI": 20,
        "CROISSANCE": 15,
        "ACTIVITÉ": 10,
        "COMMERCE": 8,
        "AUTRE": 0,
    }

    score += important_categories.get(category, 0)

    title = clean_text(event.get("title")).lower()

    high_impact_words = [
        "central bank",
        "ecb",
        "fed",
        "fomc",
        "interest rate",
        "rate decision",
        "president",
        "lagarde",
        "powell",
        "nonfarm",
        "payroll",
    ]

    if any(word in title for word in high_impact_words):
        score += 10

    return min(score, 100)


# ============================================================
# SURPRISE
# ============================================================

def calculate_surprise(actual, forecast):
    actual_value = normalize_number(actual)
    forecast_value = normalize_number(forecast)

    if actual_value is None or forecast_value is None:
        return None

    return actual_value - forecast_value


def surprise_direction(category, surprise):
    if surprise is None:
        return "NEUTRE"

    if abs(surprise) < 0.000001:
        return "NEUTRE"

    # Inflation plus élevée que prévu :
    # généralement plus hawkish / pression sur les taux.
    if category == "INFLATION":
        return "HAUSSE" if surprise > 0 else "BAISSE"

    # Emploi :
    # plus fort = généralement positif pour la monnaie.
    if category == "EMPLOI":
        return "HAUSSE" if surprise > 0 else "BAISSE"

    # Croissance :
    if category in ("CROISSANCE", "ACTIVITÉ"):
        return "HAUSSE" if surprise > 0 else "BAISSE"

    return "HAUSSE" if surprise > 0 else "BAISSE"


# ============================================================
# DIRECTION MONÉTAIRE
# ============================================================

def monetary_bias(event, category, surprise):
    title = clean_text(event.get("title")).lower()

    if category != "TAUX":
        return "NEUTRE"

    # Décisions de taux
    if surprise is not None:
        if surprise > 0:
            return "HAWKISH"
        if surprise < 0:
            return "DOVISH"

    # Discours de banques centrales :
    # impossible de déduire honnêtement le ton sans le texte.
    if any(
        word in title
        for word in [
            "speech",
            "speaks",
            "remarks",
            "statement",
            "press conference",
        ]
    ):
        return "NEUTRE"

    return "NEUTRE"


# ============================================================
# ACTIFS
# ============================================================

def detect_assets(event):
    country = clean_text(
        event.get("country_code")
        or event.get("countryCode")
        or event.get("country")
    ).upper()

    assets = ASSETS_BY_COUNTRY.get(country)

    if assets:
        # Supprime les doublons en conservant l'ordre
        return list(dict.fromkeys(assets))

    return ["EUR/USD", "S&P 500", "Obligations"]


# ============================================================
# NIVEAU D'ALERTE
# ============================================================

def alert_level(score):
    if score >= 90:
        return "CRITIQUE"

    if score >= 75:
        return "IMPORTANT"

    if score >= 55:
        return "SURVEILLANCE"

    return "INFO"


# ============================================================
# ANALYSE PRINCIPALE
# ============================================================

def analyze_event(event):
    category = detect_category(event)

    score = base_score(event, category)

    actual = event.get("actual")
    forecast = event.get("forecast")

    surprise = calculate_surprise(actual, forecast)

    if surprise is not None:
        # Une surprise mesurable augmente l'intérêt de l'événement.
        score += 10

    direction = surprise_direction(
        category,
        surprise,
    )

    monetary = monetary_bias(
        event,
        category,
        surprise,
    )

    assets = detect_assets(event)

    level = alert_level(score)

    return {
        "category": category,
        "score": min(score, 100),
        "direction": direction,
        "monetary_bias": monetary,
        "surprise": surprise,
        "alert_level": level,
        "assets": assets,
    }


# ============================================================
# MESSAGE D'ALERTE
# ============================================================

def build_alert_message(event, analysis):
    title = clean_text(event.get("title")) or "Événement économique"

    category = analysis["category"]
    score = analysis["score"]
    direction = analysis["direction"]
    surprise = analysis["surprise"]
    assets = ", ".join(analysis["assets"])

    if surprise is None:
        surprise_text = "N/D"
    else:
        surprise_text = f"{surprise:+.4f}"

    return (
        f"{title} | "
        f"{category} | "
        f"Score : {score}/100 | "
        f"Direction : {direction} | "
        f"Surprise : {surprise_text} | "
        f"Actifs : {assets}"
    )


if __name__ == "__main__":
    print("HexaPulse Intelligence Engine OK")