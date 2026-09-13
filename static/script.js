const CONFIG = {
    API_URL: "/api/annonces",
    ALERTS_URL: "/api/alerts",
    TIMEZONE: "Europe/Paris"
};


// ============================================================
// ÉTAT
// ============================================================

let allEvents = [];
let currentFilter = "all";


// ============================================================
// DOM
// ============================================================

const eventsContainer =
    document.querySelector("#events-container") ||
    document.querySelector(".events-container") ||
    document.querySelector("#events");

const refreshButton =
    document.querySelector("#refresh") ||
    document.querySelector("#refresh-button") ||
    document.querySelector(".refresh-button");


// ============================================================
// DATE / HEURE
// ============================================================

function formatDate(value) {
    if (!value) {
        return "Date inconnue";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
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


// ============================================================
// TEXTE
// ============================================================

function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ============================================================
// INTELLIGENCE
// ============================================================

function getScore(event) {
    const score = Number(event.score);

    if (Number.isNaN(score)) {
        return null;
    }

    return score;
}


function getScoreClass(score) {
    if (score === null) {
        return "score-unknown";
    }

    if (score >= 80) {
        return "score-critical";
    }

    if (score >= 60) {
        return "score-high";
    }

    if (score >= 40) {
        return "score-medium";
    }

    return "score-low";
}


function getDirectionIcon(direction) {
    const value = String(direction || "").toUpperCase();

    if (
        value.includes("HAUSSE") ||
        value.includes("UP") ||
        value.includes("POSITIVE")
    ) {
        return "↑";
    }

    if (
        value.includes("BAISSE") ||
        value.includes("DOWN") ||
        value.includes("NEGATIVE")
    ) {
        return "↓";
    }

    return "→";
}


function getDirectionClass(direction) {
    const value = String(direction || "").toUpperCase();

    if (
        value.includes("HAUSSE") ||
        value.includes("UP") ||
        value.includes("POSITIVE")
    ) {
        return "direction-up";
    }

    if (
        value.includes("BAISSE") ||
        value.includes("DOWN") ||
        value.includes("NEGATIVE")
    ) {
        return "direction-down";
    }

    return "direction-neutral";
}


function formatSurprise(value) {
    if (value === null || value === undefined || value === "") {
        return "N/D";
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
        return String(value);
    }

    if (number > 0) {
        return `+${number}`;
    }

    return String(number);
}


function normalizeAssets(assets) {
    if (!assets) {
        return [];
    }

    if (Array.isArray(assets)) {
        return assets
            .map(item => String(item).trim())
            .filter(Boolean);
    }

    return String(assets)
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
}


// ============================================================
// IMPACT
// ============================================================

function normalizeImpact(impact) {
    const value = String(impact || "").toUpperCase();

    if (
        value.includes("FORT") ||
        value.includes("HIGH") ||
        value.includes("IMPORTANT")
    ) {
        return "FORT";
    }

    if (
        value.includes("MOYEN") ||
        value.includes("MEDIUM")
    ) {
        return "MOYEN";
    }

    if (
        value.includes("FAIBLE") ||
        value.includes("LOW")
    ) {
        return "FAIBLE";
    }

    return value || "N/D";
}


// ============================================================
// FILTRES
// ============================================================

function eventMatchesFilter(event) {
    if (currentFilter === "all") {
        return true;
    }

    const impact = normalizeImpact(event.impact);

    return impact === currentFilter;
}


function setupFilters() {
    const buttons = document.querySelectorAll(
        "[data-filter]"
    );

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            currentFilter = button.dataset.filter || "all";

            buttons.forEach(item => {
                item.classList.remove("active");
            });

            button.classList.add("active");

            renderEvents();
        });
    });
}


// ============================================================
// CARTE ÉVÉNEMENT
// ============================================================

function createEventCard(event) {
    const title = escapeHTML(
        event.title || "Événement économique"
    );

    const country = escapeHTML(
        event.country || "N/D"
    );

    const currency = escapeHTML(
        event.currency || "N/D"
    );

    const impact = normalizeImpact(event.impact);

    const category = escapeHTML(
        event.category || "AUTRE"
    );

    const direction = escapeHTML(
        event.direction || "NEUTRE"
    );

    const monetaryBias = escapeHTML(
        event.monetary_bias || "N/D"
    );

    const alertLevel = escapeHTML(
        event.alert_level || "N/D"
    );

    const score = getScore(event);

    const scoreDisplay =
        score === null
            ? "N/D"
            : `${score}/100`;

    const scoreClass = getScoreClass(score);

    const directionIcon =
        getDirectionIcon(event.direction);

    const directionClass =
        getDirectionClass(event.direction);

    const surprise = formatSurprise(
        event.surprise
    );

    const assets = normalizeAssets(
        event.assets
    );

    const assetsHTML = assets.length
        ? assets
            .map(asset =>
                `<span class="asset-tag">${escapeHTML(asset)}</span>`
            )
            .join("")
        : `<span class="empty-value">N/D</span>`;

    const actual = escapeHTML(
        event.actual ?? "N/D"
    );

    const forecast = escapeHTML(
        event.forecast ?? "N/D"
    );

    const previous = escapeHTML(
        event.previous ?? "N/D"
    );

    return `
        <article class="event-card">

            <div class="event-top">

                <div class="event-date">
                    ${formatDate(event.event_date)}
                </div>

                <div class="event-impact impact-${impact.toLowerCase()}">
                    ${impact}
                </div>

            </div>


            <div class="event-main">

                <div class="event-title">
                    ${title}
                </div>

                <div class="event-meta">
                    <span>${country}</span>
                    <span>${currency}</span>
                </div>

            </div>


            <div class="intelligence-panel">

                <div class="intelligence-header">

                    <div>
                        <div class="intelligence-label">
                            INTELLIGENCE HEXAPULSE
                        </div>

                        <div class="event-category">
                            ${category}
                        </div>
                    </div>

                    <div class="score-box ${scoreClass}">
                        <span class="score-number">
                            ${scoreDisplay}
                        </span>

                        <span class="score-label">
                            SCORE
                        </span>
                    </div>

                </div>


                <div class="intelligence-grid">

                    <div class="intel-item">

                        <span class="intel-label">
                            Direction
                        </span>

                        <span class="intel-value ${directionClass}">
                            ${directionIcon}
                            ${direction}
                        </span>

                    </div>


                    <div class="intel-item">

                        <span class="intel-label">
                            Alerte
                        </span>

                        <span class="intel-value">
                            ${alertLevel}
                        </span>

                    </div>


                    <div class="intel-item">

                        <span class="intel-label">
                            Surprise
                        </span>

                        <span class="intel-value">
                            ${surprise}
                        </span>

                    </div>


                    <div class="intel-item">

                        <span class="intel-label">
                            Biais monétaire
                        </span>

                        <span class="intel-value">
                            ${monetaryBias}
                        </span>

                    </div>

                </div>


                <div class="assets-section">

                    <span class="intel-label">
                        Actifs concernés
                    </span>

                    <div class="assets-list">
                        ${assetsHTML}
                    </div>

                </div>

            </div>


            <div class="event-data">

                <div class="data-item">
                    <span>Actual</span>
                    <strong>${actual}</strong>
                </div>

                <div class="data-item">
                    <span>Prévision</span>
                    <strong>${forecast}</strong>
                </div>

                <div class="data-item">
                    <span>Précédent</span>
                    <strong>${previous}</strong>
                </div>

            </div>

        </article>
    `;
}


// ============================================================
// AFFICHAGE
// ============================================================

function renderEvents() {
    if (!eventsContainer) {
        console.warn(
            "Conteneur des événements introuvable."
        );
        return;
    }

    const filteredEvents =
        allEvents.filter(eventMatchesFilter);

    if (!filteredEvents.length) {
        eventsContainer.innerHTML = `
            <div class="empty-state">
                Aucun événement correspondant.
            </div>
        `;

        return;
    }

    eventsContainer.innerHTML =
        filteredEvents
            .map(createEventCard)
            .join("");
}


// ============================================================
// STATISTIQUES
// ============================================================

function updateStats(events) {
    const total = events.length;

    const strongImpact = events.filter(
        event =>
            normalizeImpact(event.impact) === "FORT"
    ).length;

    const mediumImpact = events.filter(
        event =>
            normalizeImpact(event.impact) === "MOYEN"
    ).length;

    const highScore = events.filter(
        event => {
            const score = getScore(event);
            return score !== null && score >= 80;
        }
    ).length;


    const totalElements = document.querySelectorAll(
        "[data-stat='total'], #total-events"
    );

    totalElements.forEach(element => {
        element.textContent = total;
    });


    const strongElements = document.querySelectorAll(
        "[data-stat='strong'], #strong-impact"
    );

    strongElements.forEach(element => {
        element.textContent = strongImpact;
    });


    const mediumElements = document.querySelectorAll(
        "[data-stat='medium'], #medium-impact"
    );

    mediumElements.forEach(element => {
        element.textContent = mediumImpact;
    });


    const highScoreElements = document.querySelectorAll(
        "[data-stat='high-score'], #high-score"
    );

    highScoreElements.forEach(element => {
        element.textContent = highScore;
    });
}


// ============================================================
// CHARGEMENT DES DONNÉES
// ============================================================

async function loadEvents() {

    if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.classList.add("loading");
    }

    try {

        const response = await fetch(
            CONFIG.API_URL,
            {
                method: "GET",
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
                "L'API a retourné une erreur."
            );
        }

        allEvents = Array.isArray(data.events)
            ? data.events
            : [];

        updateStats(allEvents);

        renderEvents();

        updateLastRefresh(
            data.updated_at
        );

        console.log(
            `[HEXAPULSE] ${allEvents.length} événements chargés.`
        );

    } catch (error) {

        console.error(
            "[HEXAPULSE] Erreur API :",
            error
        );

        showError();

    } finally {

        if (refreshButton) {
            refreshButton.disabled = false;
            refreshButton.classList.remove("loading");
        }
    }
}


// ============================================================
// DERNIÈRE ACTUALISATION
// ============================================================

function updateLastRefresh(value) {

    const elements = document.querySelectorAll(
        "#last-update, [data-last-update]"
    );

    if (!elements.length) {
        return;
    }

    const formatted =
        formatDate(value);

    elements.forEach(element => {
        element.textContent =
            `Dernière mise à jour : ${formatted}`;
    });
}


// ============================================================
// ERREUR
// ============================================================

function showError() {

    if (!eventsContainer) {
        return;
    }

    eventsContainer.innerHTML = `
        <div class="error-state">

            <strong>
                Impossible de charger les annonces.
            </strong>

            <p>
                Vérifie que le serveur HexaPulse
                est bien démarré.
            </p>

            <button
                type="button"
                onclick="loadEvents()"
            >
                Réessayer
            </button>

        </div>
    `;
}


// ============================================================
// RAFRAÎCHISSEMENT
// ============================================================

function setupRefresh() {

    if (!refreshButton) {
        return;
    }

    refreshButton.addEventListener(
        "click",
        loadEvents
    );
}


// ============================================================
// AUTO REFRESH
// ============================================================

function startAutoRefresh() {

    // Actualisation toutes les 60 secondes
    setInterval(
        loadEvents,
        60 * 1000
    );
}


// ============================================================
// INITIALISATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        console.log(
            "[HEXAPULSE] Interface initialisée."
        );

        setupFilters();

        setupRefresh();

        loadEvents();

        startAutoRefresh();

    }
);