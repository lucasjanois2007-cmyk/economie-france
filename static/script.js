const CONFIG = {
    API_URL: "/api/annonces",
    ALERTS_URL: "/api/alerts",
    TIMEZONE: "Europe/Paris"
};

let allEvents = [];
let currentFilter = "all";


// ============================================================
// NETTOYAGE DES TEXTES
// ============================================================

function cleanText(value) {
    if (value === null || value === undefined) {
        return "";
    }

    let text = String(value);

    // Décodage des entités HTML
    const textarea = document.createElement("textarea");

    for (let i = 0; i < 3; i++) {
        textarea.innerHTML = text;
        const decoded = textarea.value;

        if (decoded === text) {
            break;
        }

        text = decoded;
    }

    // Suppression Markdown parasite
    text = text.replace(/\*\*/g, "");
    text = text.replace(/__/g, "");
    text = text.replace(/`/g, "");

    // Suppression des backslashes parasites
    text = text.replace(/\\/g, "");

    // Nettoyage des espaces
    text = text.replace(/\s+/g, " ").trim();

    return text;
}


// ============================================================
// NETTOYAGE SPECIAL DES ALERTES
// ============================================================

function cleanAlertMessage(message) {
    let text = cleanText(message);

    // Correction des anciens messages corrompus du type :
    // ECB President Lagarde Speech -CB President Lagarde Speech
    // ECB President Lagarde Speech ECB President Lagarde Speech
    const titleMatch = text.match(/^(.+?)\s*\|\s*(.+)$/);

    if (titleMatch) {
        let title = titleMatch[1].trim();
        let rest = titleMatch[2].trim();

        // Si le début du deuxième morceau répète le titre
        if (rest.includes(title)) {
            rest = rest.replace(title, "").trim();
        }

        // Correction d'un éventuel "CB" / "-CB" parasite
        if (
            title.toLowerCase().includes("lagarde") &&
            rest.startsWith("CB President")
        ) {
            rest = rest.replace(/^CB President\s+Lagarde\s+Speech\s*\|?\s*/i, "");
        }

        text = `${title} | ${rest}`;
    }

    // Cas spécifique d'un titre répété avant le premier "|"
    const duplicatePattern = /^(.+?)\s+\1\s*\|/i;

    if (duplicatePattern.test(text)) {
        text = text.replace(
            duplicatePattern,
            "$1 |"
        );
    }

    return text.trim();
}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {
    return cleanText(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// IMPACT
// ============================================================

function normalizeImpact(impact) {
    const value = cleanText(impact).toLowerCase();

    if (
        value === "high" ||
        value === "fort" ||
        value === "forte"
    ) {
        return "FORT";
    }

    if (
        value === "medium" ||
        value === "moyen" ||
        value === "moyenne"
    ) {
        return "MOYEN";
    }

    return "FAIBLE";
}

function getImpactClass(impact) {
    const normalized = normalizeImpact(impact);

    if (normalized === "FORT") {
        return "impact-high";
    }

    if (normalized === "MOYEN") {
        return "impact-medium";
    }

    return "impact-low";
}


// ============================================================
// PAYS
// ============================================================

function getCountry(event) {
    return cleanText(
        event.country ||
        event.country_code ||
        event.region ||
        "EU"
    );
}


// ============================================================
// DATES
// ============================================================

function parseDate(event) {
    const value =
        event.event_date ||
        event.date ||
        event.datetime ||
        event.time;

    if (!value) {
        return null;
    }

    const date = new Date(value);

    if (isNaN(date.getTime())) {
        return null;
    }

    return date;
}

function formatDate(event) {
    const date = parseDate(event);

    if (!date) {
        return "Date inconnue";
    }

    return new Intl.DateTimeFormat("fr-FR", {
        timeZone: CONFIG.TIMEZONE,
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    }).format(date);
}

function isPast(event) {
    const date = parseDate(event);

    if (!date) {
        return false;
    }

    return date.getTime() < Date.now();
}


// ============================================================
// SCORE
// ============================================================

function getScore(event) {
    if (
        event.hexapulse_score !== undefined &&
        event.hexapulse_score !== null
    ) {
        return Number(event.hexapulse_score);
    }

    const impact = normalizeImpact(event.impact);

    if (impact === "FORT") {
        return 80;
    }

    if (impact === "MOYEN") {
        return 55;
    }

    return 25;
}


// ============================================================
// EVENEMENTS
// ============================================================

function sortEvents(events) {
    return [...events].sort((a, b) => {
        const dateA = parseDate(a);
        const dateB = parseDate(b);

        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;

        return dateA - dateB;
    });
}

function filterEvents(events) {
    if (currentFilter === "all") {
        return events;
    }

    return events.filter(event => {
        const impact = normalizeImpact(event.impact);

        return impact === currentFilter;
    });
}


// ============================================================
// CARTE EVENEMENT
// ============================================================

function renderEvent(event) {
    const title = cleanText(
        event.title || "Annonce économique"
    );

    const country = getCountry(event);
    const impact = normalizeImpact(event.impact);
    const impactClass = getImpactClass(event.impact);
    const date = formatDate(event);
    const score = getScore(event);

    const indicatorType = cleanText(
        event.indicator_type || "AUTRE"
    );

    const direction = cleanText(
        event.direction || "NEUTRE"
    );

    const alertLevel = cleanText(
        event.alert_level || "NORMAL"
    );

    const actual = cleanText(event.actual || "N/D");
    const forecast = cleanText(event.forecast || "N/D");
    const previous = cleanText(event.previous || "N/D");

    const surprise =
        event.surprise !== undefined &&
        event.surprise !== null
            ? cleanText(event.surprise)
            : "N/D";

    const assets = Array.isArray(event.assets)
        ? event.assets.map(cleanText).join(", ")
        : cleanText(event.assets || "");

    return `
        <article class="event-card">
            <div class="event-top">
                <span class="event-country">
                    ${escapeHtml(country)}
                </span>

                <span class="event-impact ${impactClass}">
                    ${escapeHtml(impact)}
                </span>
            </div>

            <h3 class="event-title">
                ${escapeHtml(title)}
            </h3>

            <div class="event-date">
                ${escapeHtml(date)}
            </div>

            <div class="event-details">

                <div class="detail-row">
                    <span>Score HexaPulse</span>
                    <strong>${escapeHtml(score)}/100</strong>
                </div>

                <div class="detail-row">
                    <span>Indicateur</span>
                    <strong>${escapeHtml(indicatorType)}</strong>
                </div>

                <div class="detail-row">
                    <span>Direction</span>
                    <strong>${escapeHtml(direction)}</strong>
                </div>

                <div class="detail-row">
                    <span>Niveau</span>
                    <strong>${escapeHtml(alertLevel)}</strong>
                </div>

                <div class="detail-row">
                    <span>Actuel</span>
                    <strong>${escapeHtml(actual)}</strong>
                </div>

                <div class="detail-row">
                    <span>Prévision</span>
                    <strong>${escapeHtml(forecast)}</strong>
                </div>

                <div class="detail-row">
                    <span>Précédent</span>
                    <strong>${escapeHtml(previous)}</strong>
                </div>

                <div class="detail-row">
                    <span>Surprise</span>
                    <strong>${escapeHtml(surprise)}</strong>
                </div>

                ${
                    assets
                        ? `
                            <div class="detail-row">
                                <span>Actifs concernés</span>
                                <strong>${escapeHtml(assets)}</strong>
                            </div>
                        `
                        : ""
                }

            </div>
        </article>
    `;
}


// ============================================================
// AFFICHAGE EVENEMENTS
// ============================================================

function renderEvents() {
    const container =
        document.getElementById("eventsContainer") ||
        document.getElementById("events");

    if (!container) {
        return;
    }

    const filtered = filterEvents(
        sortEvents(allEvents)
    );

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                Aucun événement trouvé.
            </div>
        `;
        return;
    }

    container.innerHTML = filtered
        .map(renderEvent)
        .join("");
}


// ============================================================
// STATISTIQUES
// ============================================================

function updateStats() {
    const total = allEvents.length;

    const strong = allEvents.filter(
        event => normalizeImpact(event.impact) === "FORT"
    ).length;

    const medium = allEvents.filter(
        event => normalizeImpact(event.impact) === "MOYEN"
    ).length;

    const totalElement =
        document.getElementById("totalEvents");

    const strongElement =
        document.getElementById("strongEvents");

    const mediumElement =
        document.getElementById("mediumEvents");

    if (totalElement) {
        totalElement.textContent = total;
    }

    if (strongElement) {
        strongElement.textContent = strong;
    }

    if (mediumElement) {
        mediumElement.textContent = medium;
    }
}


// ============================================================
// CHARGEMENT DES EVENEMENTS
// ============================================================

async function loadEvents() {
    try {
        const response = await fetch(
            `${CONFIG.API_URL}?_=${Date.now()}`,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(
                "Réponse API invalide"
            );
        }

        allEvents = Array.isArray(data.events)
            ? data.events
            : [];

        renderEvents();
        updateStats();

    } catch (error) {
        console.error(
            "Erreur chargement événements :",
            error
        );
    }
}


// ============================================================
// ALERTES
// ============================================================

function renderAlerts(alerts) {
    const container =
        document.getElementById("alertsContainer") ||
        document.getElementById("alerts");

    if (!container) {
        return;
    }

    if (!Array.isArray(alerts) || alerts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                Aucune alerte importante.
            </div>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => {

        const message = cleanAlertMessage(
            alert.alert_message ||
            alert.message ||
            alert.intelligence_message ||
            ""
        );

        const level = cleanText(
            alert.alert_level ||
            alert.level ||
            "IMPORTANT"
        );

        return `
            <div class="alert-card">
                <div class="alert-message">
                    ${escapeHtml(message)}
                </div>

                <div class="alert-level">
                    ${escapeHtml(level)}
                </div>
            </div>
        `;
    }).join("");
}

async function loadAlerts() {
    try {
        const response = await fetch(
            `${CONFIG.ALERTS_URL}?_=${Date.now()}`,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        const alerts =
            Array.isArray(data)
                ? data
                : (
                    Array.isArray(data.alerts)
                        ? data.alerts
                        : []
                );

        renderAlerts(alerts);

    } catch (error) {
        console.error(
            "Erreur chargement alertes :",
            error
        );
    }
}


// ============================================================
// ACTUALISATION
// ============================================================

async function refreshAll() {
    await loadEvents();
    await loadAlerts();
}

window.refreshAll = refreshAll;


// ============================================================
// FILTRES
// ============================================================

function setupFilters() {
    const buttons =
        document.querySelectorAll(
            "[data-filter]"
        );

    buttons.forEach(button => {
        button.addEventListener(
            "click",
            () => {

                currentFilter =
                    button.dataset.filter ||
                    "all";

                buttons.forEach(btn => {
                    btn.classList.remove(
                        "active"
                    );
                });

                button.classList.add("active");

                renderEvents();
            }
        );
    });
}


// ============================================================
// PREMIUM
// ============================================================

function setupPremium() {
    const button =
        document.getElementById(
            "premiumButton"
        );

    const message =
        document.getElementById(
            "premiumMessage"
        );

    if (!button) {
        return;
    }

    button.addEventListener(
        "click",
        () => {

            if (message) {
                message.textContent =
                    "Le Premium HexaPulse sera bientôt disponible.";
            }
        }
    );
}


// ============================================================
// WATER INTELLIGENCE
// ============================================================

function setupWater() {
    const button =
        document.getElementById(
            "waterButton"
        );

    const section =
        document.getElementById(
            "waterSection"
        );

    if (!button || !section) {
        return;
    }

    button.addEventListener(
        "click",
        () => {
            section.classList.toggle(
                "active"
            );
        }
    );
}


// ============================================================
// INITIALISATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupFilters();
        setupPremium();
        setupWater();

        refreshAll();

        // Actualisation automatique
        setInterval(
            refreshAll,
            60 * 1000
        );
    }
);