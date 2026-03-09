const API_BASE = window.location.origin;

let token = localStorage.getItem("token");
let currentUser = localStorage.getItem("currentUser") || null;
let dom = {};

document.addEventListener("DOMContentLoaded", () => {
    dom = {
        appTitle: document.getElementById("app-title"),
        authStatus: document.getElementById("auth-status"),
        logoutBtn: document.getElementById("logout-btn"),

        registerForm: document.getElementById("register-form"),
        registerEmail: document.getElementById("register-email"),
        registerPassword: document.getElementById("register-password"),
        registerBtn: document.getElementById("register-btn"),
        registerMessage: document.getElementById("register-message"),

        loginForm: document.getElementById("login-form"),
        loginEmail: document.getElementById("login-email"),
        loginPassword: document.getElementById("login-password"),
        loginBtn: document.getElementById("login-btn"),
        loginMessage: document.getElementById("login-message"),

        shortenForm: document.getElementById("shorten-form"),
        originalUrl: document.getElementById("original-url"),
        customAlias: document.getElementById("custom-alias"),
        expiresAt: document.getElementById("expires-at"),
        shortenBtn: document.getElementById("shorten-btn"),
        shortenMessage: document.getElementById("shorten-message"),

        resultCard: document.getElementById("result-card"),
        shortLink: document.getElementById("short-link"),
        resultJson: document.getElementById("result-json"),

        searchForm: document.getElementById("search-form"),
        searchUrl: document.getElementById("search-url"),
        searchBtn: document.getElementById("search-btn"),
        searchResults: document.getElementById("search-results"),

        infoForm: document.getElementById("info-form"),
        infoShortCode: document.getElementById("info-short-code"),
        infoBtn: document.getElementById("info-btn"),
        infoResults: document.getElementById("info-results"),

        statsForm: document.getElementById("stats-form"),
        statsShortCode: document.getElementById("stats-short-code"),
        statsBtn: document.getElementById("stats-btn"),
        statsResults: document.getElementById("stats-results")
    };

    setupEventListeners();
    updateAuthUI();
});

function setupEventListeners() {

    dom.registerForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleRegister();
    });

    dom.loginForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleLogin();
    });

    dom.logoutBtn?.addEventListener("click", handleLogout);

    dom.shortenForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleShorten();
    });

    dom.searchForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleSearch();
    });

    dom.infoForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleGetInfo();
    });

    dom.statsForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleGetStats();
    });
}

function updateAuthUI() {

    const isAuthenticated = Boolean(token);

    if (dom.authStatus) {
        dom.authStatus.textContent = isAuthenticated
            ? `Выполнен вход: ${currentUser || "user"}`
            : "Вход не выполнен";
    }

    if (dom.logoutBtn) {
        dom.logoutBtn.style.display = isAuthenticated ? "inline-flex" : "none";
    }
}

async function apiRequest(endpoint, options = {}) {

    const url = `${API_BASE}${endpoint}`;

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    let payload = null;

    try {
        payload = await response.json();
    } catch {}

    if (!response.ok) {
        throw new Error(payload?.detail || `HTTP ${response.status}`);
    }

    return payload;
}

function showMessage(element, message, type = "error") {

    if (!element) return;

    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = "block";
}

function clearMessage(element) {

    if (!element) return;

    element.textContent = "";
    element.style.display = "none";
}

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

function formatDate(value) {

    if (!value) return "Не указано";

    return new Date(value).toLocaleString();
}

function renderLinkCard(data) {

    const fullShortUrl = escapeHtml(data.full_short_url);

    return `
        <div class="result-grid">
            <div>Код: ${escapeHtml(data.short_code)}</div>
            <div>URL: ${escapeHtml(data.original_url)}</div>
            <div>Короткая ссылка: <a href="${fullShortUrl}" target="_blank">${fullShortUrl}</a></div>
            <div>Создана: ${formatDate(data.created_at)}</div>
            <div>Переходы: ${data.clicks ?? 0}</div>
            <div>Последний переход: ${formatDate(data.last_used_at)}</div>
        </div>
    `;
}

async function handleRegister() {

    clearMessage(dom.registerMessage);

    const email = dom.registerEmail.value.trim();
    const password = dom.registerPassword.value;

    try {

        const data = await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        showMessage(dom.registerMessage, `Пользователь создан: ${data.user_id}`, "success");

    } catch (error) {

        showMessage(dom.registerMessage, error.message);
    }
}

async function handleLogin() {

    clearMessage(dom.loginMessage);

    const email = dom.loginEmail.value.trim();
    const password = dom.loginPassword.value;

    try {

        const data = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        token = data.access_token;

        localStorage.setItem("token", token);
        localStorage.setItem("currentUser", email);

        currentUser = email;

        updateAuthUI();

        showMessage(dom.loginMessage, "Вход выполнен", "success");

    } catch (error) {

        showMessage(dom.loginMessage, error.message);
    }
}

function handleLogout() {

    token = null;
    currentUser = null;

    localStorage.removeItem("token");
    localStorage.removeItem("currentUser");

    updateAuthUI();
}

async function handleShorten() {

    const body = {
        original_url: dom.originalUrl.value.trim()
    };

    if (dom.customAlias.value) {
        body.custom_alias = dom.customAlias.value.trim();
    }

    if (dom.expiresAt.value) {
        body.expires_at = new Date(dom.expiresAt.value).toISOString();
    }

    try {

        const data = await apiRequest("/links/shorten", {
            method: "POST",
            body: JSON.stringify(body)
        });

        dom.resultCard.style.display = "block";
        dom.shortLink.href = data.full_short_url;
        dom.shortLink.textContent = data.full_short_url;
        dom.resultJson.textContent = JSON.stringify(data, null, 2);

    } catch (error) {

        showMessage(dom.shortenMessage, error.message);
    }
}

async function handleSearch() {

    const originalUrl = dom.searchUrl.value.trim();

    try {

        const encoded = encodeURIComponent(originalUrl);

        const data = await apiRequest(`/links/search?original_url=${encoded}`);

        dom.searchResults.style.display = "block";

        if (!data.items?.length) {

            dom.searchResults.innerHTML = "Ничего не найдено";
            return;
        }

        dom.searchResults.innerHTML = data.items.map(item => `
            <div>
                ${escapeHtml(item.short_code)} →
                <a href="${escapeHtml(item.full_short_url)}" target="_blank">
                ${escapeHtml(item.full_short_url)}
                </a>
            </div>
        `).join("");

    } catch (error) {

        showMessage(dom.searchResults, error.message);
    }
}

async function handleGetInfo() {

    const shortCode = dom.infoShortCode.value.trim();

    try {

        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}`);

        dom.infoResults.style.display = "block";
        dom.infoResults.innerHTML = renderLinkCard(data);

    } catch (error) {

        showMessage(dom.infoResults, error.message);
    }
}

async function handleGetStats() {

    const shortCode = dom.statsShortCode.value.trim();

    try {

        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}/stats`);

        dom.statsResults.style.display = "block";
        dom.statsResults.innerHTML = renderLinkCard(data);

    } catch (error) {

        showMessage(dom.statsResults, error.message);
    }
}