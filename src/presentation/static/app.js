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
    element.className = "message";
    element.style.display = "none";
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatDate(value) {
    if (!value) return "Не указано";

    try {
        return new Date(value).toLocaleString();
    } catch {
        return value;
    }
}

function renderLinkInfo(data) {
    const fullShortUrl = escapeHtml(data.full_short_url);

    return `
        <div class="result-grid">
            <div class="result-item">
                <div class="label">Код</div>
                <div class="value">${escapeHtml(data.short_code)}</div>
            </div>
            <div class="result-item">
                <div class="label">URL</div>
                <div class="value">${escapeHtml(data.original_url)}</div>
            </div>
            <div class="result-item">
                <div class="label">Короткая ссылка</div>
                <div class="value">
                    <a href="${fullShortUrl}" target="_blank" rel="noopener noreferrer">${fullShortUrl}</a>
                </div>
            </div>
            <div class="result-item">
                <div class="label">Создана</div>
                <div class="value">${formatDate(data.created_at)}</div>
            </div>
            <div class="result-item">
                <div class="label">Обновлена</div>
                <div class="value">${formatDate(data.updated_at)}</div>
            </div>
            <div class="result-item">
                <div class="label">Истекает</div>
                <div class="value">${formatDate(data.expires_at)}</div>
            </div>
            <div class="result-item">
                <div class="label">Владелец</div>
                <div class="value">${data.owner_user_id ? escapeHtml(data.owner_user_id) : "Не указан"}</div>
            </div>
            <div class="result-item">
                <div class="label">Проект</div>
                <div class="value">${data.project_id ? escapeHtml(data.project_id) : "Не указан"}</div>
            </div>
            <div class="result-item">
                <div class="label">Удалена</div>
                <div class="value">${data.is_deleted ? "Да" : "Нет"}</div>
            </div>
            <div class="result-item">
                <div class="label">Просрочена</div>
                <div class="value">${data.is_expired ? "Да" : "Нет"}</div>
            </div>
        </div>
    `;
}

function renderLinkStats(data) {
    const fullShortUrl = escapeHtml(data.full_short_url);

    return `
        <div class="result-grid">
            <div class="result-item">
                <div class="label">Код</div>
                <div class="value">${escapeHtml(data.short_code)}</div>
            </div>
            <div class="result-item">
                <div class="label">Короткая ссылка</div>
                <div class="value">
                    <a href="${fullShortUrl}" target="_blank" rel="noopener noreferrer">${fullShortUrl}</a>
                </div>
            </div>
            <div class="result-item">
                <div class="label">Переходы</div>
                <div class="value">${data.clicks ?? 0}</div>
            </div>
            <div class="result-item">
                <div class="label">Последний переход</div>
                <div class="value">${formatDate(data.last_used_at)}</div>
            </div>
        </div>
    `;
}

function renderSearchResults(data) {
    if (!data.items?.length) {
        return '<div class="message info">Ничего не найдено</div>';
    }

    const itemsHtml = data.items.map((item) => {
        const fullShortUrl = escapeHtml(item.full_short_url);

        return `
            <div class="result-item">
                <div class="label">Код</div>
                <div class="value">${escapeHtml(item.short_code)}</div>
                <div class="label">URL</div>
                <div class="value">${escapeHtml(item.original_url)}</div>
                <div class="label">Короткая ссылка</div>
                <div class="value">
                    <a href="${fullShortUrl}" target="_blank" rel="noopener noreferrer">${fullShortUrl}</a>
                </div>
                <div class="label">Создана</div>
                <div class="value">${formatDate(item.created_at)}</div>
                <div class="label">Истекает</div>
                <div class="value">${formatDate(item.expires_at)}</div>
                <div class="label">Владелец</div>
                <div class="value">${item.owner_user_id ? escapeHtml(item.owner_user_id) : "Не указан"}</div>
                <div class="label">Проект</div>
                <div class="value">${item.project_id ? escapeHtml(item.project_id) : "Не указан"}</div>
                <div class="label">Удалена</div>
                <div class="value">${item.is_deleted ? "Да" : "Нет"}</div>
                <div class="label">Просрочена</div>
                <div class="value">${item.is_expired ? "Да" : "Нет"}</div>
            </div>
        `;
    }).join("");

    return `<div class="result-grid">${itemsHtml}</div>`;
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
        currentUser = email;

        localStorage.setItem("token", token);
        localStorage.setItem("currentUser", email);

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
    clearMessage(dom.shortenMessage);

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
    clearMessage(dom.searchResults);

    const originalUrl = dom.searchUrl.value.trim();

    try {
        const encoded = encodeURIComponent(originalUrl);
        const data = await apiRequest(`/links/search?original_url=${encoded}`);

        dom.searchResults.style.display = "block";
        dom.searchResults.innerHTML = renderSearchResults(data);
    } catch (error) {
        showMessage(dom.searchResults, error.message);
    }
}

async function handleGetInfo() {
    clearMessage(dom.infoResults);

    const shortCode = dom.infoShortCode.value.trim();

    try {
        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}`);

        dom.infoResults.style.display = "block";
        dom.infoResults.innerHTML = renderLinkInfo(data);
    } catch (error) {
        showMessage(dom.infoResults, error.message);
    }
}

async function handleGetStats() {
    clearMessage(dom.statsResults);

    const shortCode = dom.statsShortCode.value.trim();

    try {
        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}/stats`);

        dom.statsResults.style.display = "block";
        dom.statsResults.innerHTML = renderLinkStats(data);
    } catch (error) {
        showMessage(dom.statsResults, error.message);
    }
}