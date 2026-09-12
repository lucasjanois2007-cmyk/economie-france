// ============================================================
// HEXAPULSE — SCRIPT PRINCIPAL
// ============================================================

const CONFIG = {
    apiUrl: "/api/annonces",
    alertsUrl: "/api/alerts",
    timezone: "Europe/Paris",
    liveWindowMinutes: 30,
    statusRefreshMs: 60 * 1000,
    alertsRefreshMs: 60 * 1000
};

let events = [];

let filters = {
    country: "ALL",
    impact: "ALL",
    search: ""
};


// ============================================================
// OUTILS
// ============================================================

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function displayValue(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    return escapeHtml(value);
}


function normalizeImpact(value) {

    const text = String(
        value || ""
    ).toLowerCase().trim();

    if (
        text === "fort" ||
        text === "forte" ||
        text === "high" ||
        text === "3" ||
        text === "3.0"
    ) {
        return "Fort";
    }

    if (
        text === "moyen" ||
        text === "moyenne" ||
        text === "medium" ||
        text === "2" ||
        text === "2.0"
    ) {
        return "Moyen";
    }

    return "Faible";
}


function getImpactClass(impact) {

    const normalized = normalizeImpact(
        impact
    );

    if (normalized === "Fort") {
        return "impact-high";
    }

    if (normalized === "Moyen") {
        return "impact-medium";
    }

    return "impact-low";
}


function getCountry(event) {

    return String(
        event?.country || "—"
    ).toUpperCase();
}


// ============================================================
// DATES
// ============================================================

function parseEventDate(value) {

    if (!value) {
        return null;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}


function formatEventDate(value) {

    const date = parseEventDate(value);

    if (!date) {
        return "Date inconnue";
    }

    return new Intl.DateTimeFormat(
        "fr-FR",
        {
            timeZone: CONFIG.timezone,
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    ).format(date);
}


function getEventStatus(event) {

    const date = parseEventDate(
        event?.event_date
    );

    if (!date) {
        return "upcoming";
    }

    const now = Date.now();

    const difference =
        date.getTime() - now;

    const liveWindow =
        CONFIG.liveWindowMinutes * 60 * 1000;

    if (
        difference <= 0 &&
        Math.abs(difference) <= liveWindow
    ) {
        return "live";
    }

    if (difference < 0) {
        return "past";
    }

    return "upcoming";
}


// ============================================================
// TRI
// ============================================================

function sortEvents(eventList) {

    return [...eventList].sort(
        (a, b) => {

            const dateA =
                parseEventDate(
                    a.event_date
                )?.getTime() || 0;

            const dateB =
                parseEventDate(
                    b.event_date
                )?.getTime() || 0;

            return dateA - dateB;
        }
    );
}


// ============================================================
// FILTRES
// ============================================================

function filterEvents() {

    const search =
        filters.search
            .toLowerCase()
            .trim();

    return events.filter(
        event => {

            const countryMatch =
                filters.country === "ALL" ||
                getCountry(event) ===
                filters.country;

            const impactMatch =
                filters.impact === "ALL" ||
                normalizeImpact(
                    event.impact
                ) === filters.impact;

            const searchable = [
                event.title,
                event.country,
                event.currency,
                event.description
            ]
                .join(" ")
                .toLowerCase();

            const searchMatch =
                !search ||
                searchable.includes(search);

            return (
                countryMatch &&
                impactMatch &&
                searchMatch
            );
        }
    );
}


// ============================================================
// STATISTIQUES
// ============================================================

function updateStats() {

    const strong = events.filter(
        event =>
            normalizeImpact(
                event.impact
            ) === "Fort"
    ).length;

    const medium = events.filter(
        event =>
            normalizeImpact(
                event.impact
            ) === "Moyen"
    ).length;

    const total = events.length;

    const values =
        document.querySelectorAll(
            ".stat-value"
        );

    if (values.length >= 4) {

        values[0].textContent = total;
        values[1].textContent = strong;
        values[2].textContent = medium;
        values[3].textContent = "LIVE";
    }
}


// ============================================================
// CALCULS
// ============================================================

function parseNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    let text = String(value)
        .replace("%", "")
        .replace(",", ".")
        .trim();

    const number =
        Number.parseFloat(text);

    return Number.isFinite(number)
        ? number
        : null;
}


function calculateDifference(
    actual,
    forecast
) {

    const a =
        parseNumber(actual);

    const f =
        parseNumber(forecast);

    if (a === null || f === null) {
        return null;
    }

    return a - f;
}


// ============================================================
// TYPE D'INDICATEUR
// ============================================================

function getIndicatorType(title) {

    const text = String(
        title || ""
    ).toLowerCase();

    if (
        text.includes("inflation") ||
        text.includes("cpi") ||
        text.includes("hicp") ||
        text.includes("prices") ||
        text.includes("prix")
    ) {
        return "inflation";
    }

    if (
        text.includes("interest rate") ||
        text.includes("interest rates") ||
        text.includes("rate decision") ||
        text.includes("taux") ||
        text.includes("ecb") ||
        text.includes("bce") ||
        text.includes("fed") ||
        text.includes("central bank")
    ) {
        return "rates";
    }

    if (
        text.includes("unemployment") ||
        text.includes("chômage")
    ) {
        return "unemployment";
    }

    if (
        text.includes("employment") ||
        text.includes("jobs") ||
        text.includes("payroll") ||
        text.includes("nonfarm") ||
        text.includes("wages") ||
        text.includes("salaires")
    ) {
        return "employment";
    }

    if (
        text.includes("gdp") ||
        text.includes("pib") ||
        text.includes("growth") ||
        text.includes("croissance")
    ) {
        return "gdp";
    }

    if (
        text.includes("pmi") ||
        text.includes("manufacturing") ||
        text.includes("services") ||
        text.includes("activity") ||
        text.includes("activité")
    ) {
        return "pmi";
    }

    if (
        text.includes("retail sales") ||
        text.includes("ventes au détail")
    ) {
        return "retail";
    }

    if (
        text.includes("confidence") ||
        text.includes("sentiment") ||
        text.includes("confiance")
    ) {
        return "confidence";
    }

    if (
        text.includes("industrial production") ||
        text.includes("production industrielle")
    ) {
        return "industrial";
    }

    return "generic";
}


// ============================================================
// SURPRISE
// ============================================================

function getSurpriseLevel(
    difference
) {

    if (difference === null) {
        return "neutral";
    }

    const absolute =
        Math.abs(difference);

    if (absolute >= 2) {
        return "strong";
    }

    if (absolute >= 1) {
        return "medium";
    }

    return "weak";
}


function getEconomicDirection(
    event,
    difference
) {

    if (difference === null) {
        return {
            direction: "neutral",
            label: "Pas assez de données"
        };
    }

    const type =
        getIndicatorType(
            event.title
        );

    const higher =
        difference > 0;

    if (type === "inflation") {

        return higher
            ? {
                direction: "negative",
                label: "Pression inflationniste"
            }
            : {
                direction: "positive",
                label: "Désinflation"
            };
    }

    if (type === "rates") {

        return higher
            ? {
                direction: "negative",
                label: "Orientation hawkish"
            }
            : {
                direction: "positive",
                label: "Orientation dovish"
            };
    }

    if (type === "unemployment") {

        return higher
            ? {
                direction: "negative",
                label: "Marché du travail plus faible"
            }
            : {
                direction: "positive",
                label: "Marché du travail plus solide"
            };
    }

    if (
        type === "employment" ||
        type === "gdp" ||
        type === "pmi" ||
        type === "retail" ||
        type === "confidence" ||
        type === "industrial"
    ) {

        return higher
            ? {
                direction: "positive",
                label: "Donnée meilleure que prévu"
            }
            : {
                direction: "negative",
                label: "Donnée moins bonne que prévu"
            };
    }

    return higher
        ? {
            direction: "positive",
            label: "Au-dessus des prévisions"
        }
        : {
            direction: "negative",
            label: "Sous les prévisions"
        };
}


function getSurpriseAnalysis(event) {

    const difference =
        calculateDifference(
            event.actual,
            event.forecast
        );

    if (difference === null) {
        return null;
    }

    const level =
        getSurpriseLevel(
            difference
        );

    const direction =
        getEconomicDirection(
            event,
            difference
        );

    return {
        difference,
        level,
        ...direction
    };
}


// ============================================================
// SCORE HEXAPULSE
// ============================================================

function calculateHexapulseScore(
    event
) {

    let score = 35;

    const impact =
        normalizeImpact(
            event.impact
        );

    if (impact === "Fort") {
        score += 35;
    }

    if (impact === "Moyen") {
        score += 20;
    }

    const surprise =
        getSurpriseAnalysis(
            event
        );

    if (surprise) {

        const absolute =
            Math.abs(
                surprise.difference
            );

        if (absolute >= 2) {
            score += 25;
        } else if (absolute >= 1) {
            score += 15;
        } else if (absolute >= 0.5) {
            score += 8;
        }
    }

    if (
        getEventStatus(event) ===
        "live"
    ) {
        score += 5;
    }

    return Math.min(
        100,
        Math.max(0, score)
    );
}


function getScoreClass(score) {

    if (score >= 80) {
        return "score-high";
    }

    if (score >= 55) {
        return "score-medium";
    }

    return "score-low";
}


// ============================================================
// ANALYSE MARCHÉ
// ============================================================

function getMarketAssets(
    event
) {

    const currency =
        String(
            event.currency || ""
        ).toUpperCase();

    const country =
        getCountry(event);

    const assets = [];

    if (currency === "USD") {
        assets.push("USD");
    }

    if (currency === "EUR") {
        assets.push("EUR");
    }

    if (currency === "GBP") {
        assets.push("GBP");
    }

    if (currency === "CHF") {
        assets.push("CHF");
    }

    if (
        country === "FR" ||
        country === "DE" ||
        country === "IT" ||
        country === "ES"
    ) {
        assets.push("CAC 40");
        assets.push("EURO STOXX 50");
    }

    if (
        country === "GB"
    ) {
        assets.push("FTSE 100");
    }

    if (
        country === "CH"
    ) {
        assets.push("SMI");
    }

    return [
        ...new Set(assets)
    ];
}


function getMarketAnalysis(
    event
) {

    const surprise =
        getSurpriseAnalysis(
            event
        );

    const assets =
        getMarketAssets(
            event
        );

    if (!surprise) {

        return {
            message:
                "Surveille les actifs concernés.",
            assets
        };
    }

    let message =
        surprise.label + ".";

    if (
        surprise.direction ===
        "positive"
    ) {
        message +=
            " Réaction potentiellement favorable aux actifs concernés.";
    }

    if (
        surprise.direction ===
        "negative"
    ) {
        message +=
            " Réaction potentiellement défavorable aux actifs concernés.";
    }

    return {
        message,
        assets
    };
}


// ============================================================
// CARTE ÉVÉNEMENT
// ============================================================

function createEventCard(event) {

    const status =
        getEventStatus(event);

    const impact =
        normalizeImpact(
            event.impact
        );

    const score =
        calculateHexapulseScore(
            event
        );

    const surprise =
        getSurpriseAnalysis(
            event
        );

    const market =
        getMarketAnalysis(
            event
        );

    let statusLabel =
        "À venir";

    if (status === "live") {
        statusLabel = "EN DIRECT";
    }

    if (status === "past") {
        statusLabel = "Passé";
    }

    const surpriseHtml =
        surprise
            ? `
                <div class="surprise-analysis">

                    <div class="surprise-title">
                        Surprise économique
                    </div>

                    <div class="
                        surprise-result
                        surprise-${escapeHtml(
                            surprise.direction
                        )}
                    ">
                        ${escapeHtml(
                            surprise.label
                        )}
                    </div>

                    <div class="surprise-message">
                        Écart :
                        ${surprise.difference >= 0 ? "+" : ""}
                        ${surprise.difference.toFixed(2)}
                    </div>
                </div>
            `
            : "";


    const assetsHtml =
        market.assets.length
            ? `
                <div class="analysis-assets">
                    ${market.assets.map(
                        asset => `
                            <span class="analysis-asset">
                                ${escapeHtml(asset)}
                            </span>
                        `
                    ).join("")}
                </div>
            `
            : "";


    return `
        <article class="event-card">

            <div class="event-main">

                <div class="event-time">
                    ${formatEventDate(
                        event.event_date
                    )}
                </div>

                <div class="event-content">

                    <div class="event-top">

                        <h3 class="event-title">
                            ${displayValue(
                                event.title
                            )}
                        </h3>

                        <div class="event-badges">

                            <span class="
                                event-impact
                                ${getImpactClass(
                                    impact
                                )}
                            ">
                                ${escapeHtml(
                                    impact
                                )}
                            </span>

                            <span class="event-status">
                                ${statusLabel}
                            </span>

                        </div>

                    </div>

                    <div class="event-meta">

                        <span>
                            ${escapeHtml(
                                getCountry(event)
                            )}
                        </span>

                        <span>
                            ${escapeHtml(
                                event.currency || "—"
                            )}
                        </span>

                        <span>
                            ${escapeHtml(
                                event.source || "BiQuote"
                            )}
                        </span>

                    </div>

                    <div class="event-values">

                        <div class="event-value">
                            <small>Actuel</small>
                            <strong>
                                ${displayValue(
                                    event.actual
                                )}
                            </strong>
                        </div>

                        <div class="event-value">
                            <small>Prévision</small>
                            <strong>
                                ${displayValue(
                                    event.forecast
                                )}
                            </strong>
                        </div>

                        <div class="event-value">
                            <small>Précédent</small>
                            <strong>
                                ${displayValue(
                                    event.previous
                                )}
                            </strong>
                        </div>

                    </div>

                    <div class="event-details">

                        ${
                            event.description
                                ? `
                                    <p>
                                        ${displayValue(
                                            event.description
                                        )}
                                    </p>
                                `
                                : ""
                        }

                        <div class="market-analysis">

                            <div class="analysis-header">
                                <span class="analysis-label">
                                    HEXAPULSE INTELLIGENCE
                                </span>
                            </div>

                            <div class="analysis-message">
                                ${escapeHtml(
                                    market.message
                                )}
                            </div>

                            ${assetsHtml}

                        </div>

                        <div class="hexapulse-score">

                            <div class="score-header">

                                <span class="score-title">
                                    HexaPulse Score
                                </span>

                                <strong class="
                                    score-value
                                    ${getScoreClass(
                                        score
                                    )}
                                ">
                                    ${score}/100
                                </strong>

                            </div>

                            <div class="score-bar">
                                <div
                                    class="
                                        score-bar-fill
                                        ${getScoreClass(
                                            score
                                        )}
                                    "
                                    style="
                                        width:${score}%;
                                    "
                                ></div>
                            </div>

                        </div>

                        ${surpriseHtml}

                    </div>

                </div>

                <div class="event-arrow">
                    →
                </div>

            </div>

        </article>
    `;
}


// ============================================================
// RENDU DES ÉVÉNEMENTS
// ============================================================

function renderEvents() {

    const container =
        document.getElementById(
            "eventsContainer"
        );

    if (!container) {
        return;
    }

    const filtered =
        sortEvents(
            filterEvents()
        );


    if (!filtered.length) {

        container.innerHTML = `
            <div class="empty-state">
                Aucun événement trouvé.
            </div>
        `;

        return;
    }


    container.innerHTML =
        filtered.map(
            createEventCard
        ).join("");
}


// ============================================================
// FILTRES DYNAMIQUES
// ============================================================

function setupFilters() {

    const filterButtons =
        document.querySelectorAll(
            ".filter-btn"
        );

    filterButtons.forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    const type =
                        button.dataset.filter;

                    const value =
                        button.dataset.value ||
                        "ALL";

                    if (
                        type === "country"
                    ) {
                        filters.country =
                            value;
                    }

                    if (
                        type === "impact"
                    ) {
                        filters.impact =
                            value;
                    }

                    document
                        .querySelectorAll(
                            `.filter-btn[data-filter="${type}"]`
                        )
                        .forEach(
                            item =>
                                item.classList.remove(
                                    "active"
                                )
                        );

                    button.classList.add(
                        "active"
                    );

                    renderEvents();
                }
            );
        }
    );


    const searchInput =
        document.querySelector(
            ".filter-search"
        );

    if (searchInput) {

        searchInput.addEventListener(
            "input",
            event => {

                filters.search =
                    event.target.value;

                renderEvents();
            }
        );
    }
}


// ============================================================
// CHARGEMENT DES DONNÉES
// ============================================================

async function loadEvents() {

    const container =
        document.getElementById(
            "eventsContainer"
        );

    if (container) {

        container.innerHTML = `
            <div class="loading-state">
                Chargement des annonces...
            </div>
        `;
    }


    try {

        const response =
            await fetch(
                CONFIG.apiUrl,
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        if (
            !data.success ||
            !Array.isArray(data.events)
        ) {
            throw new Error(
                "Réponse API invalide"
            );
        }

        events =
            data.events;

        updateStats();
        renderEvents();
        loadAlerts();

    } catch (error) {

        console.error(
            "Erreur HexaPulse :",
            error
        );

        if (container) {

            container.innerHTML = `
                <div class="error-state">
                    Impossible de charger
                    les annonces.
                    <br><br>
                    Vérifie que le serveur
                    HexaPulse est lancé.
                </div>
            `;
        }
    }
}


// ============================================================
// ALERTES HEXAPULSE
// ============================================================

async function loadAlerts() {

    try {

        const response =
            await fetch(
                CONFIG.alertsUrl,
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            return;
        }

        const data =
            await response.json();

        if (
            !data.success ||
            !Array.isArray(
                data.alerts
            )
        ) {
            return;
        }

        renderSiteAlerts(
            data.alerts
        );

    } catch (error) {

        console.error(
            "Erreur alertes :",
            error
        );
    }
}


function renderSiteAlerts(
    alerts
) {

    let container =
        document.getElementById(
            "hexapulseLiveAlerts"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );

        container.id =
            "hexapulseLiveAlerts";


        const eventsContainer =
            document.getElementById(
                "eventsContainer"
            );


        if (
            eventsContainer &&
            eventsContainer.parentNode
        ) {

            eventsContainer.parentNode.insertBefore(
                container,
                eventsContainer
            );
        }
    }


    if (!alerts.length) {

        container.innerHTML = "";

        return;
    }


    container.innerHTML = `

        <div class="live-alert-header">

            <span class="live-alert-dot"></span>

            <span>
                ALERTES HEXAPULSE
            </span>

            <span class="live-alert-count">
                ${alerts.length}
            </span>

        </div>

        <div class="live-alert-list">

            ${alerts.slice(0, 5).map(
                alert => `

                    <div class="live-alert-item">

                        <div class="live-alert-level">

                            ${escapeHtml(
                                alert.level
                            )}

                        </div>

                        <div class="live-alert-content">

                            <strong>
                                ${escapeHtml(
                                    alert.title
                                )}
                            </strong>

                            <span>
                                ${escapeHtml(
                                    alert.message
                                )}
                            </span>

                        </div>

                    </div>

                `
            ).join("")}

        </div>
    `;
}


// ============================================================
// BOUTON ACTUALISER
// ============================================================

function setupRefresh() {

    const button =
        document.querySelector(
            "[data-refresh]"
        ) ||
        document.querySelector(
            "button"
        );


    if (!button) {
        return;
    }


    button.addEventListener(
        "click",
        async () => {

            button.disabled = true;

            const originalText =
                button.textContent;

            button.textContent =
                "Actualisation...";


            try {

                await fetch(
                    "/api/sync",
                    {
                        cache: "no-store"
                    }
                );

            } catch (error) {

                console.error(error);

            }


            await loadEvents();


            button.disabled = false;

            button.textContent =
                originalText;
        }
    );
}


// ============================================================
// RAFRAÎCHISSEMENT DU STATUT
// ============================================================

function refreshStatus() {

    renderEvents();
    loadAlerts();
}


// ============================================================
// WATER INTELLIGENCE
// ============================================================

const WATER_KEYWORDS = {

    "Stress hydrique": [
        "water",
        "drought",
        "sécheresse",
        "stress hydrique",
        "eau",
        "water scarcity"
    ],

    "Infrastructures": [
        "water infrastructure",
        "infrastructure",
        "pipeline",
        "reservoir",
        "irrigation"
    ],

    "Dessalement": [
        "desalination",
        "dessalement"
    ],

    "Technologies": [
        "water technology",
        "water treatment",
        "filtration",
        "purification",
        "traitement de l'eau"
    ],

    "Réglementation": [
        "water regulation",
        "regulation",
        "directive",
        "réglementation"
    ],

    "Agriculture": [
        "agriculture",
        "agricultural",
        "crop",
        "irrigation",
        "récolte"
    ]
};


const WATER_THEMES = [
    "Stress hydrique",
    "Infrastructures",
    "Dessalement",
    "Technologies",
    "Réglementation",
    "Agriculture"
];


function getWaterCategories(
    event
) {

    const text = [
        event.title,
        event.description
    ]
        .join(" ")
        .toLowerCase();

    const categories = [];

    for (
        const [category, keywords]
        of Object.entries(
            WATER_KEYWORDS
        )
    ) {

        if (
            keywords.some(
                keyword =>
                    text.includes(
                        keyword
                    )
            )
        ) {
            categories.push(
                category
            );
        }
    }

    return categories;
}


function getWaterRiskScore(
    event
) {

    const categories =
        getWaterCategories(
            event
        );

    let score = 0;

    score +=
        categories.length * 15;

    if (
        normalizeImpact(
            event.impact
        ) === "Fort"
    ) {
        score += 30;
    }

    if (
        normalizeImpact(
            event.impact
        ) === "Moyen"
    ) {
        score += 15;
    }

    return Math.min(
        100,
        score
    );
}


function getWaterRiskLabel(
    score
) {

    if (score >= 70) {
        return "Élevé";
    }

    if (score >= 40) {
        return "Modéré";
    }

    return "Faible";
}


function getWaterSignals() {

    return events
        .map(event => ({
            event,
            categories:
                getWaterCategories(
                    event
                ),
            score:
                getWaterRiskScore(
                    event
                )
        }))
        .filter(
            item =>
                item.categories.length > 0
        )
        .sort(
            (a, b) =>
                b.score - a.score
        );
}


function renderWaterIntelligence() {

    const sections =
        document.querySelectorAll(
            "section"
        );

    let waterSection = null;

    sections.forEach(
        section => {

            const text =
                section.textContent
                    .toLowerCase();

            if (
                text.includes(
                    "water watchlist"
                ) ||
                text.includes(
                    "stress hydrique"
                )
            ) {
                waterSection =
                    section;
            }
        }
    );


    if (!waterSection) {
        return;
    }


    let panel =
        document.getElementById(
            "hexapulseWaterPanel"
        );


    if (!panel) {

        panel =
            document.createElement(
                "div"
            );

        panel.id =
            "hexapulseWaterPanel";

        waterSection.appendChild(
            panel
        );
    }


    const signals =
        getWaterSignals();


    if (!signals.length) {

        panel.innerHTML = `
            <div class="water-intelligence-panel">
                <strong>
                    WATER INTELLIGENCE
                </strong>

                <p>
                    Aucun signal eau détecté
                    dans les annonces actuelles.
                </p>
            </div>
        `;

        return;
    }


    panel.innerHTML = `

        <div class="water-intelligence-panel">

            <div class="water-panel-header">

                <div>
                    <span class="analysis-label">
                        WATER INTELLIGENCE
                    </span>

                    <h3>
                        Signaux détectés
                    </h3>
                </div>

                <span class="water-signal-count">
                    ${signals.length}
                </span>

            </div>

            <div class="water-signals">

                ${signals.slice(0, 8).map(
                    item => `

                        <div class="water-signal">

                            <div>

                                <strong>
                                    ${escapeHtml(
                                        item.event.title
                                    )}
                                </strong>

                                <small>
                                    ${item.categories
                                        .map(
                                            category =>
                                                escapeHtml(
                                                    category
                                                )
                                        )
                                        .join(" · ")}
                                </small>

                            </div>

                            <span>
                                ${item.score}/100
                            </span>

                        </div>

                    `
                ).join("")}

            </div>

        </div>
    `;
}


// ============================================================
// INITIALISATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupFilters();

        setupRefresh();

        loadEvents();

        renderWaterIntelligence();


        setInterval(
            refreshStatus,
            CONFIG.statusRefreshMs
        );


        setInterval(
            loadAlerts,
            CONFIG.alertsRefreshMs
        );

    }
);
// ============================================================
// HEXAPULSE PREMIUM
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    const premiumButton =
        document.getElementById("premiumButton");

    const premiumMessage =
        document.getElementById("premiumMessage");

    if (!premiumButton) {
        return;
    }

    premiumButton.addEventListener("click", async () => {

        premiumButton.disabled = true;

        premiumButton.innerHTML = `
            Chargement...
        `;

        if (premiumMessage) {
            premiumMessage.textContent = "";
        }

        try {

            const response = await fetch("/api/premium");

            if (!response.ok) {
                throw new Error("Erreur Premium");
            }

            const data = await response.json();

            if (premiumMessage) {

                premiumMessage.innerHTML = `
                    <div class="premium-success">
                        <strong>HexaPulse Premium</strong>
                        <br>
                        ${data.message || "Fonctionnalités Premium disponibles."}
                        <br><br>
                        <strong>4,99 € / mois</strong>
                    </div>
                `;

            }

        } catch (error) {

            console.error(
                "[PREMIUM]",
                error
            );

            if (premiumMessage) {

                premiumMessage.textContent =
                    "Impossible de charger Premium pour le moment.";

            }

        }

        premiumButton.disabled = false;

        premiumButton.innerHTML = `
            Découvrir Premium
            <span>→</span>
        `;

    });

});