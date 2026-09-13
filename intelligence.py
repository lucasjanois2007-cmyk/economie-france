# ============================================================
# HEXAPULSE — INTELLIGENCE ENGINE
# Version : Score HexaPulse V2
# ============================================================

import re


# ============================================================
# OUTILS
# ============================================================

def clean_text(value):
    """Nettoie une valeur texte."""
    if value is None:
        return ""

    return str(value).strip()


def normalize_number(value):
    """
    Transforme une valeur en nombre exploitable.

    Exemples :
    "2.5"      -> 2.5
    "2,5"      -> 2.5
    "1.234,5"  -> 1234.5
    "N/D"      -> None
    """
    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    invalid_values = {
        "n/d",
        "nd",
        "n.a.",
        "n/a",
        "-",
        "—",
        "none",
        "null",
    }

    if text.lower() in invalid_values:
        return None

    text = text.replace("%", "")
    text = text.replace(" ", "")

    # Format européen : 1.234,56
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    # Format européen simple : 2,5
    elif "," in text:
        text = text.replace(",", ".")

    # Garde uniquement les caractères utiles
    text = re.sub(r"[^0-9.\-+eE]", "", text)

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


# ============================================================
# CLASSIFICATION DES ÉVÉNEMENTS
# ============================================================

CATEGORY_KEYWORDS = {
    "INFLATION": [
        "cpi",
        "cpi m/m",
        "cpi y/y",
        "cpih",
        "hicp",
        "hicp m/m",
        "hicp y/y",
        "inflation",
        "inflation rate",
        "consumer price",
        "consumer prices",
        "harmonised inflation",
        "harmonized inflation",
        "core inflation",
        "core cpi",
        "producer price",
        "ppi",
        "rpi",
    ],

    "EMPLOI": [
        "unemployment",
        "unemployment rate",
        "employment",
        "employment change",
        "employment growth",
        "claimant count",
        "jobless",
        "jobs",
        "payroll",
        "nonfarm payroll",
        "non-farm payroll",
        "average weekly earnings",
        "weekly earnings",
        "wage",
        "wages",
        "earnings",
        "labour market",
        "labor market",
    ],

    "CROISSANCE": [
        "gdp",
        "gross domestic product",
        "economic growth",
        "growth rate",
        "quarterly growth",
        "annual growth",
    ],

    "ACTIVITE": [
        "pmi",
        "manufacturing",
        "services pmi",
        "composite pmi",
        "industrial production",
        "industrial output",
        "factory orders",
        "retail sales",
        "consumer confidence",
        "business confidence",
        "economic sentiment",
        "economic situation",
        "zew",
        "ifo",
        "business climate",
        "business expectations",
        "construction output",
        "construction",
        "capacity utilization",
        "capacity utilisation",
        "industrial confidence",
    ],

    "COMMERCE": [
        "trade balance",
        "trade balance eu",
        "trade balance n.s.a",
        "goods trade",
        "goods trade balance",
        "current account",
        "exports",
        "imports",
        "international trade",
        "balance of trade",
    ],

    "TAUX": [
        "ecb",
        "federal reserve",
        "fed",
        "bank of england",
        "boe",
        "bank of japan",
        "boj",
        "central bank",
        "interest rate",
        "interest rates",
        "policy rate",
        "deposit facility",
        "refinancing rate",
        "monetary policy",
        "monetary policy decision",
        "rate decision",
        "rate statement",
        "lagarde",
        "schnabel",
        "powell",
        "bailey",
        "president speech",
        "governor speech",
        "central bank speech",
    ],

    "OBLIGATIONS": [
        "auction",
        "note auction",
        "bond auction",
        "treasury auction",
        "government bond",
        "government bonds",
        "btf auction",
        "rfgb auction",
        "2-year note",
        "5-year note",
        "10-year note",
        "30-year note",
        "yield",
        "bond yield",
    ],
}


def detect_category(title, country="", source=""):
    """
    Détermine la catégorie économique d'un événement.
    """

    text = " ".join([
        clean_text(title),
        clean_text(country),
        clean_text(source),
    ]).lower()

    # Priorité 1 : banques centrales / taux
    rate_keywords = [
        "ecb",
        "federal reserve",
        "fed",
        "bank of england",
        "boe",
        "bank of japan",
        "boj",
        "central bank",
        "interest rate",
        "interest rates",
        "policy rate",
        "monetary policy",
        "rate decision",
        "rate statement",
        "lagarde",
        "schnabel",
        "powell",
        "bailey",
        "president speech",
        "governor speech",
        "central bank speech",
    ]

    if any(keyword in text for keyword in rate_keywords):
        return "TAUX"

    # Priorité 2 : obligations / adjudications
    bond_keywords = [
        "auction",
        "note auction",
        "bond auction",
        "treasury auction",
        "government bond",
        "btf auction",
        "rfgb auction",
    ]

    if any(keyword in text for keyword in bond_keywords):
        return "OBLIGATIONS"

    # Puis catégories économiques
    priority = [
        "INFLATION",
        "EMPLOI",
        "CROISSANCE",
        "ACTIVITE",
        "COMMERCE",
    ]

    for category in priority:
        for keyword in CATEGORY_KEYWORDS[category]:
            if keyword in text:
                return category

    return "AUTRE"


# ============================================================
# SCORE DE BASE PAR CATÉGORIE
# ============================================================

CATEGORY_SCORES = {
    "TAUX": 65,
    "INFLATION": 55,
    "EMPLOI": 52,
    "CROISSANCE": 52,
    "ACTIVITE": 42,
    "COMMERCE": 32,
    "OBLIGATIONS": 30,
    "AUTRE": 18,
}


# ============================================================
# IMPORTANCE DU TITRE
# ============================================================

def title_score_bonus(title, category):
    """
    Ajoute des points selon l'importance précise du titre.
    """

    text = clean_text(title).lower()
    bonus = 0

    # Banque centrale
    if category == "TAUX":

        if any(word in text for word in [
            "rate decision",
            "interest rate decision",
            "policy decision",
            "rate statement",
        ]):
            bonus += 15

        elif any(word in text for word in [
            "interest rate",
            "policy rate",
            "monetary policy",
        ]):
            bonus += 10

        elif any(word in text for word in [
            "president speech",
            "governor speech",
            "central bank speech",
            "lagarde speech",
            "powell speech",
            "bailey speech",
            "schnabel speech",
        ]):
            bonus += 10

    # Inflation
    elif category == "INFLATION":

        if any(word in text for word in [
            "cpi y/y",
            "cpi m/m",
            "hicp y/y",
            "hicp m/m",
            "inflation rate",
        ]):
            bonus += 8

        if "core" in text:
            bonus += 4

    # Emploi
    elif category == "EMPLOI":

        if any(word in text for word in [
            "nonfarm payroll",
            "non-farm payroll",
            "payroll",
            "unemployment rate",
            "employment change",
        ]):
            bonus += 8

        elif any(word in text for word in [
            "average weekly earnings",
            "wages",
            "earnings",
        ]):
            bonus += 5

    # Croissance
    elif category == "CROISSANCE":

        if "gdp" in text:
            bonus += 10

    # Activité
    elif category == "ACTIVITE":

        if any(word in text for word in [
            "pmi",
            "retail sales",
            "industrial production",
            "zew",
            "ifo",
        ]):
            bonus += 4

    return bonus


# ============================================================
# IMPACT FOURNI PAR LA SOURCE
# ============================================================

def impact_bonus(impact):
    """
    Traduit l'impact fourni par BiQuote en points.
    """

    text = clean_text(impact).upper()

    if text == "FORT":
        return 15

    if text == "MOYEN":
        return 7

    if text == "FAIBLE":
        return 0

    return 0


# ============================================================
# SURPRISE ACTUEL / PRÉVISION
# ============================================================

def calculate_surprise(actual, forecast):
    """
    Surprise économique :

    Surprise = Actuel - Prévision
    """

    actual_value = normalize_number(actual)
    forecast_value = normalize_number(forecast)

    if actual_value is None or forecast_value is None:
        return None

    return actual_value - forecast_value


# ============================================================
# INTENSITÉ DE LA SURPRISE
# ============================================================

def surprise_strength(category, title, surprise):
    """
    Transforme la surprise économique en points de score.

    Le seuil dépend de la catégorie afin d'éviter qu'une petite
    différence sur un indicateur soit considérée comme énorme.
    """

    if surprise is None:
        return 0

    magnitude = abs(surprise)

    text = clean_text(title).lower()

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------
    if category == "INFLATION":

        # 0.1 point = petite surprise
        # 0.3 point = notable
        # 0.5 point = forte
        # 1 point = très forte

        if magnitude >= 1.0:
            return 20

        if magnitude >= 0.5:
            return 15

        if magnitude >= 0.3:
            return 10

        if magnitude >= 0.1:
            return 5

        return 2

    # --------------------------------------------------------
    # CHÔMAGE
    # --------------------------------------------------------
    if category == "EMPLOI" and "unemployment" in text:

        if magnitude >= 1.0:
            return 20

        if magnitude >= 0.5:
            return 15

        if magnitude >= 0.3:
            return 10

        if magnitude >= 0.1:
            return 5

        return 2

    # --------------------------------------------------------
    # EMPLOI / PAYROLL
    # --------------------------------------------------------
    if category == "EMPLOI":

        if magnitude >= 500000:
            return 20

        if magnitude >= 250000:
            return 15

        if magnitude >= 100000:
            return 10

        if magnitude >= 50000:
            return 5

        return 2

    # --------------------------------------------------------
    # GDP
    # --------------------------------------------------------
    if category == "CROISSANCE":

        if magnitude >= 1.0:
            return 20

        if magnitude >= 0.5:
            return 15

        if magnitude >= 0.3:
            return 10

        if magnitude >= 0.1:
            return 5

        return 2

    # --------------------------------------------------------
    # PMI / ACTIVITÉ
    # --------------------------------------------------------
    if category == "ACTIVITE":

        if magnitude >= 5:
            return 15

        if magnitude >= 2:
            return 10

        if magnitude >= 1:
            return 5

        return 2

    # --------------------------------------------------------
    # COMMERCE
    # --------------------------------------------------------
    if category == "COMMERCE":

        if magnitude >= 10:
            return 12

        if magnitude >= 5:
            return 8

        if magnitude >= 2:
            return 5

        return 2

    # --------------------------------------------------------
    # TAUX
    # --------------------------------------------------------
    # Un événement de banque centrale avec actual/forecast
    # mérite déjà une forte pondération.
    if category == "TAUX":

        if magnitude >= 1:
            return 15

        if magnitude >= 0.5:
            return 10

        if magnitude >= 0.25:
            return 5

        return 2

    return 0


# ============================================================
# DIRECTION ÉCONOMIQUE
# ============================================================

def surprise_direction(category, title, surprise):
    """
    Détermine la direction économique de la surprise.

    Attention :
    pour le chômage, une hausse du chômage est négative.
    """

    if surprise is None:
        return "NEUTRE"

    if surprise == 0:
        return "NEUTRE"

    text = clean_text(title).lower()

    # Chômage :
    # chômage plus élevé = économie plus faible
    if category == "EMPLOI" and "unemployment" in text:
        if surprise > 0:
            return "BAISSE"

        return "HAUSSE"

    # Inflation :
    # inflation supérieure aux attentes = pression haussière
    if category == "INFLATION":
        if surprise > 0:
            return "HAUSSE"

        return "BAISSE"

    # Emploi, croissance, activité, commerce
    if category in {
        "EMPLOI",
        "CROISSANCE",
        "ACTIVITE",
        "COMMERCE",
    }:
        if surprise > 0:
            return "HAUSSE"

        return "BAISSE"

    # Taux / obligations :
    # on évite de fabriquer une direction sans contexte suffisant
    return "NEUTRE"


# ============================================================
# BIAIS MONÉTAIRE
# ============================================================

def monetary_bias(category, title, surprise):
    """
    Estime le biais monétaire :

    HAWKISH = politique monétaire potentiellement plus restrictive
    DOVISH  = politique monétaire potentiellement plus accommodante
    """

    text = clean_text(title).lower()

    # --------------------------------------------------------
    # Avec surprise
    # --------------------------------------------------------

    if surprise is not None:

        # Inflation
        if category == "INFLATION":

            if surprise > 0:
                return "HAWKISH"

            if surprise < 0:
                return "DOVISH"

        # Chômage
        if category == "EMPLOI" and "unemployment" in text:

            if surprise > 0:
                return "DOVISH"

            if surprise < 0:
                return "HAWKISH"

        # Emploi
        if category == "EMPLOI":

            if surprise > 0:
                return "HAWKISH"

            if surprise < 0:
                return "DOVISH"

        # Croissance
        if category == "CROISSANCE":

            if surprise > 0:
                return "HAWKISH"

            if surprise < 0:
                return "DOVISH"

        # Activité
        if category == "ACTIVITE":

            if surprise > 0:
                return "HAWKISH"

            if surprise < 0:
                return "DOVISH"

    # --------------------------------------------------------
    # Signaux explicites dans le titre
    # --------------------------------------------------------

    hawkish_words = [
        "hawkish",
        "restrictive",
        "tightening",
        "higher for longer",
    ]

    dovish_words = [
        "dovish",
        "accommodative",
        "easing",
        "rate cut",
        "cuts rates",
    ]

    if any(word in text for word in hawkish_words):
        return "HAWKISH"

    if any(word in text for word in dovish_words):
        return "DOVISH"

    return "NEUTRE"


# ============================================================
# ACTIFS IMPACTÉS
# ============================================================

ASSETS_BY_COUNTRY = {
    "FR": [
        "EUR/USD",
        "CAC 40",
        "Obligations françaises",
    ],

    "EU": [
        "EUR/USD",
        "Euro Stoxx 50",
        "CAC 40",
        "Obligations européennes",
    ],

    "DE": [
        "EUR/USD",
        "DAX",
        "Obligations allemandes",
    ],

    "IT": [
        "EUR/USD",
        "FTSE MIB",
        "Obligations italiennes",
    ],

    "ES": [
        "EUR/USD",
        "IBEX 35",
        "Obligations espagnoles",
    ],

    "GB": [
        "GBP/USD",
        "FTSE 100",
        "Gilts",
    ],

    "CH": [
        "USD/CHF",
        "SMI",
        "Obligations suisses",
    ],

    "SE": [
        "EUR/SEK",
        "OMX Stockholm",
    ],

    "NO": [
        "EUR/NOK",
        "OSE",
    ],

    "DK": [
        "EUR/DKK",
        "OMXC",
    ],

    "PL": [
        "EUR/PLN",
        "WIG20",
    ],
}


def detect_assets(country, category):
    """
    Détermine les actifs potentiellement concernés.
    """

    country_code = clean_text(country).upper()

    assets = list(
        ASSETS_BY_COUNTRY.get(
            country_code,
            ["EUR/USD", "CAC 40", "S&P 500"],
        )
    )

    # Les banques centrales ont généralement un impact
    # plus large que le seul marché domestique.
    if category == "TAUX":

        if "S&P 500" not in assets:
            assets.append("S&P 500")

        if "Obligations" not in " ".join(assets):
            assets.append("Obligations")

    return assets


# ============================================================
# NIVEAU D'ALERTE
# ============================================================

def alert_level(score):
    """
    Transforme le score en niveau d'alerte.
    """

    if score >= 85:
        return "CRITICAL"

    if score >= 70:
        return "ALERT"

    if score >= 50:
        return "IMPORTANT"

    return "NORMAL"


# ============================================================
# SCORE HEXAPULSE V2
# ============================================================

def calculate_score(
    title,
    country,
    impact,
    category,
    actual,
    forecast,
    previous=None,
):
    """
    Score HexaPulse V2.

    Le score cherche à mesurer le potentiel de réaction du marché.

    Il prend en compte :

    - importance de la catégorie
    - impact fourni par la source
    - importance précise du titre
    - disponibilité des données
    - surprise économique
    - intensité de la surprise

    Score final : 0 à 100.
    """

    score = CATEGORY_SCORES.get(category, 18)

    # --------------------------------------------------------
    # Impact source
    # --------------------------------------------------------

    score += impact_bonus(impact)

    # --------------------------------------------------------
    # Importance du titre
    # --------------------------------------------------------

    score += title_score_bonus(title, category)

    # --------------------------------------------------------
    # Disponibilité des données
    # --------------------------------------------------------

    actual_value = normalize_number(actual)
    forecast_value = normalize_number(forecast)

    if actual_value is not None and forecast_value is not None:
        score += 8

    elif actual_value is not None:
        score += 3

    # --------------------------------------------------------
    # Surprise
    # --------------------------------------------------------

    surprise = calculate_surprise(actual, forecast)

    score += surprise_strength(
        category,
        title,
        surprise,
    )

    # --------------------------------------------------------
    # Cas particuliers
    # --------------------------------------------------------

    # Les speeches n'ont généralement pas de surprise
    # numérique : leur score repose donc sur leur importance.
    if category == "TAUX" and "speech" in clean_text(title).lower():
        if score < 65:
            score = 65

    # Les adjudications obligataires restent importantes,
    # mais ne doivent pas automatiquement dépasser les
    # grandes annonces macro.
    if category == "OBLIGATIONS" and score > 65:
        score = 65

    # --------------------------------------------------------
    # Limites
    # --------------------------------------------------------

    score = max(0, min(100, score))

    return int(score)


# ============================================================
# ANALYSE COMPLÈTE D'UN ÉVÉNEMENT
# ============================================================

def analyze_event(event):
    """
    Analyse un événement HexaPulse complet.

    Retourne :

    {
        category,
        score,
        direction,
        monetary_bias,
        surprise,
        alert_level,
        assets
    }
    """

    title = clean_text(
        event.get("title")
        or event.get("name")
        or ""
    )

    country = clean_text(
        event.get("country")
        or event.get("country_code")
        or ""
    )

    source = clean_text(
        event.get("source")
        or ""
    )

    impact = clean_text(
        event.get("impact")
        or ""
    )

    actual = event.get("actual")
    forecast = event.get("forecast")
    previous = event.get("previous")

    category = detect_category(
        title=title,
        country=country,
        source=source,
    )

    surprise = calculate_surprise(
        actual,
        forecast,
    )

    direction = surprise_direction(
        category,
        title,
        surprise,
    )

    bias = monetary_bias(
        category,
        title,
        surprise,
    )

    score = calculate_score(
        title=title,
        country=country,
        impact=impact,
        category=category,
        actual=actual,
        forecast=forecast,
        previous=previous,
    )

    level = alert_level(score)

    assets = detect_assets(
        country=country,
        category=category,
    )

    return {
        "category": category,
        "score": score,
        "direction": direction,
        "monetary_bias": bias,
        "surprise": surprise,
        "alert_level": level,
        "assets": assets,
    }


# ============================================================
# MESSAGE D'ALERTE
# ============================================================

def build_alert_message(event, analysis):
    """
    Génère un message lisible pour une alerte HexaPulse.
    """

    title = clean_text(
        event.get("title")
        or event.get("name")
        or "Événement économique"
    )

    category = analysis.get(
        "category",
        "AUTRE",
    )

    score = analysis.get(
        "score",
        0,
    )

    direction = analysis.get(
        "direction",
        "NEUTRE",
    )

    bias = analysis.get(
        "monetary_bias",
        "NEUTRE",
    )

    surprise = analysis.get(
        "surprise"
    )

    level = analysis.get(
        "alert_level",
        "NORMAL",
    )

    if surprise is None:
        surprise_text = "N/D"
    else:
        surprise_text = f"{surprise:+.2f}"

    return (
        f"[{level}] {title} | "
        f"{category} | "
        f"Score : {score}/100 | "
        f"Direction : {direction} | "
        f"Biais monétaire : {bias} | "
        f"Surprise : {surprise_text}"
    )


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HEXAPULSE — INTELLIGENCE ENGINE V2")
    print("=" * 60)
    print()

    test_events = [

        {
            "title": "CPI y/y",
            "country": "GB",
            "impact": "FORT",
            "actual": "3.2",
            "forecast": "3.0",
            "previous": "3.1",
        },

        {
            "title": "Unemployment Rate",
            "country": "GB",
            "impact": "FORT",
            "actual": "4.3",
            "forecast": "4.2",
            "previous": "4.1",
        },

        {
            "title": "ZEW Economic Sentiment Indicator",
            "country": "DE",
            "impact": "MOYEN",
            "actual": "45.0",
            "forecast": "40.0",
            "previous": "38.0",
        },

        {
            "title": "Trade Balance",
            "country": "EU",
            "impact": "MOYEN",
            "actual": "18.0",
            "forecast": "15.0",
            "previous": "12.0",
        },

        {
            "title": "ECB President Lagarde Speech",
            "country": "EU",
            "impact": "FORT",
            "actual": None,
            "forecast": None,
            "previous": None,
        },

        {
            "title": "10-Year Note Auction",
            "country": "DE",
            "impact": "FAIBLE",
            "actual": None,
            "forecast": None,
            "previous": None,
        },
    ]

    for event in test_events:

        analysis = analyze_event(event)

        print("-" * 60)
        print(f"Événement : {event['title']}")
        print(f"Pays      : {event['country']}")
        print(f"Catégorie : {analysis['category']}")
        print(f"Score     : {analysis['score']}/100")
        print(f"Direction : {analysis['direction']}")
        print(f"Biais     : {analysis['monetary_bias']}")
        print(f"Surprise  : {analysis['surprise']}")
        print(f"Niveau    : {analysis['alert_level']}")
        print(f"Actifs    : {', '.join(analysis['assets'])}")
        print()

    print("=" * 60)
    print("TEST TERMINÉ")
    print("=" * 60)
