from datetime import datetime


# ============================================================
# HEXAPULSE INTELLIGENCE ENGINE
# ============================================================

IMPACT_SCORES = {
    "FAIBLE": 25,
    "MOYEN": 55,
    "FORT": 80,
}


# ============================================================
# NORMALISATION
# ============================================================

def normalize_impact(impact):

    value = str(
        impact or ""
    ).lower().strip()

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


# ============================================================
# CONVERSION DES NOMBRES
# ============================================================

def parse_number(value):

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("%", "")
    text = text.replace(",", ".")

    try:
        return float(text)

    except ValueError:
        return None


# ============================================================
# SURPRISE
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
# SCORE DE SURPRISE
# ============================================================

def calculate_surprise_score(surprise):

    if surprise is None:
        return 0

    absolute = abs(
        surprise
    )

    if absolute >= 5:
        return 20

    if absolute >= 2:
        return 15

    if absolute >= 1:
        return 10

    if absolute >= 0.5:
        return 5

    return 0


# ============================================================
# TYPE D'INDICATEUR
# ============================================================

def detect_indicator_type(title):

    text = str(
        title or ""
    ).lower()

    if any(
        word in text
        for word in [
            "inflation",
            "cpi",
            "hicp",
            "consumer price"
        ]
    ):
        return "INFLATION"

    if any(
        word in text
        for word in [
            "interest rate",
            "rate decision",
            "central bank",
            "ecb",
            "fed",
            "boe",
            "snb"
        ]
    ):
        return "TAUX"

    if any(
        word in text
        for word in [
            "gdp",
            "gross domestic"
        ]
    ):
        return "CROISSANCE"

    if any(
        word in text
        for word in [
            "employment",
            "unemployment",
            "payroll",
            "job",
            "jobs",
            "wage"
        ]
    ):
        return "EMPLOI"

    if any(
        word in text
        for word in [
            "pmi",
            "manufacturing",
            "services",
            "industrial"
        ]
    ):
        return "ACTIVITE"

    if any(
        word in text
        for word in [
            "retail sales",
            "consumer",
            "confidence"
        ]
    ):
        return "CONSOMMATION"

    if any(
        word in text
        for word in [
            "speech",
            "president",
            "governor",
            "official"
        ]
    ):
        return "BANQUE_CENTRALE"

    return "AUTRE"


# ============================================================
# DIRECTION ECONOMIQUE
# ============================================================

def determine_direction(
    event,
    indicator_type,
    surprise
):

    if surprise is None:
        return "NEUTRE"

    title = str(
        event.get("title", "")
    ).lower()

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------

    if indicator_type == "INFLATION":

        if surprise > 0:
            return "HAUSSIER"

        if surprise < 0:
            return "BAISSIER"

    # --------------------------------------------------------
    # CROISSANCE
    # --------------------------------------------------------

    if indicator_type == "CROISSANCE":

        if surprise > 0:
            return "HAUSSIER"

        if surprise < 0:
            return "BAISSIER"

    # --------------------------------------------------------
    # EMPLOI
    # --------------------------------------------------------

    if indicator_type == "EMPLOI":

        if "unemployment" in title:

            if surprise < 0:
                return "HAUSSIER"

            if surprise > 0:
                return "BAISSIER"

        if surprise > 0:
            return "HAUSSIER"

        if surprise < 0:
            return "BAISSIER"

    # --------------------------------------------------------
    # ACTIVITE
    # --------------------------------------------------------

    if indicator_type == "ACTIVITE":

        if surprise > 0:
            return "HAUSSIER"

        if surprise < 0:
            return "BAISSIER"

    # --------------------------------------------------------
    # CONSOMMATION
    # --------------------------------------------------------

    if indicator_type == "CONSOMMATION":

        if surprise > 0:
            return "HAUSSIER"

        if surprise < 0:
            return "BAISSIER"

    return "NEUTRE"


# ============================================================
# ACTIFS CONCERNES
# ============================================================

def detect_assets(event, indicator_type):

    country = str(
        event.get("country", "")
    ).upper()

    currency = str(
        event.get("currency", "")
    ).upper()

    assets = []

    # --------------------------------------------------------
    # EUROPE
    # --------------------------------------------------------

    if country in {
        "FR",
        "DE",
        "IT",
        "ES",
        "BE",
        "NL",
        "PT",
        "IE",
        "AT",
        "FI",
        "GR",
    } or country == "EU":

        assets.extend([
            "EUR/USD",
            "CAC 40"
        ])

    # --------------------------------------------------------
    # SUISSE
    # --------------------------------------------------------

    if country == "CH":

        assets.extend([
            "USD/CHF",
            "EUR/CHF",
            "S&P 500"
        ])

    # --------------------------------------------------------
    # ROYAUME-UNI
    # --------------------------------------------------------

    if country == "GB":

        assets.extend([
            "GBP/USD",
            "FTSE 100"
        ])

    # --------------------------------------------------------
    # IMPACT BANQUE CENTRALE
    # --------------------------------------------------------

    if indicator_type in {
        "TAUX",
        "BANQUE_CENTRALE"
    }:

        assets.extend([
            "EUR/USD",
            "S&P 500",
            "Obligations"
        ])

    # --------------------------------------------------------
    # SUPPRESSION DOUBLONS
    # --------------------------------------------------------

    return list(
        dict.fromkeys(
            assets
        )
    )


# ============================================================
# NIVEAU D'ALERTE
# ============================================================

def determine_alert_level(score):

    if score >= 90:
        return "CRITIQUE"

    if score >= 70:
        return "IMPORTANT"

    if score >= 45:
        return "SURVEILLER"

    return "NORMAL"


# ============================================================
# MESSAGE INTELLIGENT
# ============================================================

def build_message(
    event,
    indicator_type,
    direction,
    surprise,
    score
):

    title = event.get(
        "title",
        "Annonce économique"
    )

    if surprise is not None:

        surprise_text = (
            f"{surprise:+.2f}"
        )

    else:

        surprise_text = "N/D"

    return (
        f"{title} | "
        f"{indicator_type} | "
        f"Surprise : {surprise_text} | "
        f"Direction : {direction} | "
        f"Score : {score}/100"
    )


# ============================================================
# ANALYSE COMPLETE
# ============================================================

def analyze_event(event):

    impact = normalize_impact(
        event.get("impact")
    )

    indicator_type = (
        detect_indicator_type(
            event.get("title")
        )
    )

    surprise = calculate_surprise(
        event
    )

    base_score = IMPACT_SCORES.get(
        impact,
        25
    )

    surprise_score = (
        calculate_surprise_score(
            surprise
        )
    )

    score = min(
        100,
        base_score + surprise_score
    )

    direction = (
        determine_direction(
            event,
            indicator_type,
            surprise
        )
    )

    assets = detect_assets(
        event,
        indicator_type
    )

    alert_level = (
        determine_alert_level(
            score
        )
    )

    message = build_message(
        event,
        indicator_type,
        direction,
        surprise,
        score
    )

    return {
        "score": score,
        "impact": impact,
        "indicator_type": indicator_type,
        "surprise": surprise,
        "direction": direction,
        "assets": assets,
        "alert_level": alert_level,
        "message": message,
        "analyzed_at": datetime.utcnow().isoformat()
    }


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("HEXAPULSE INTELLIGENCE ENGINE")
    print("=" * 60)
    print()

    test_event = {
        "title": "Inflation Rate YoY",
        "country": "FR",
        "currency": "EUR",
        "impact": "high",
        "actual": "2.8",
        "forecast": "2.3",
        "previous": "2.5"
    }

    result = analyze_event(
        test_event
    )

    print(
        f"Score : "
        f"{result['score']}/100"
    )

    print(
        f"Type : "
        f"{result['indicator_type']}"
    )

    print(
        f"Surprise : "
        f"{result['surprise']}"
    )

    print(
        f"Direction : "
        f"{result['direction']}"
    )

    print(
        f"Niveau : "
        f"{result['alert_level']}"
    )

    print(
        f"Actifs : "
        f"{', '.join(result['assets'])}"
    )

    print()

    print(
        result["message"]
    )

    print()