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
    if (dom.registerForm) {
        dom.registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleRegister();
        });
    }

    if (dom.loginForm) {
        dom.loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleLogin();
        });
    }

    if (dom.logoutBtn) {
        dom.logoutBtn.addEventListener("click", handleLogout);
    }

    if (dom.shortenForm) {
        dom.shortenForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleShorten();
        });
    }

    if (dom.searchForm) {
        dom.searchForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleSearch();
        });
    }

    if (dom.infoForm) {
        dom.infoForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleGetInfo();
        });
    }

    if (dom.statsForm) {
        dom.statsForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            await handleGetStats();
        });
    }
}

function updateAuthUI() {
    const isAuthenticated = Boolean(token);

    if (dom.authStatus) {
        dom.authStatus.textContent = isAuthenticated
            ? `Выполнен вход: ${currentUser || "user"}`
            : "Вход не выполнен";
        dom.authStatus.className = isAuthenticated ? "logged-in" : "logged-out";
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

    const contentType = response.headers.get("content-type") || "";
    let payload = null;

    if (contentType.includes("application/json")) {
        try {
            payload = await response.json();
        } catch {
            payload = null;
        }
    }

    if (!response.ok) {
        throw new Error(extractErrorMessage(payload, response.status));
    }

    return payload;
}

function extractErrorMessage(payload, status) {
    if (!payload) {
        return `HTTP error ${status}`;
    }

    if (typeof payload.detail === "string") {
        return payload.detail;
    }

    if (Array.isArray(payload.detail)) {
        return payload.detail
            .map((item) => item.msg || JSON.stringify(item))
            .join("; ");
    }

    if (typeof payload.message === "string") {
        return payload.message;
    }

    return JSON.stringify(payload);
}

function showMessage(element, message, type = "error") {
    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = "block";

    if (type === "success" || type === "info") {
        setTimeout(() => {
            if (element.textContent === message) {
                element.style.display = "none";
            }
        }, 5000);
    }
}

function clearMessage(element) {
    if (!element) {
        return;
    }

    element.textContent = "";
    element.className = "message";
    element.style.display = "none";
}

function clearAllMessages() {
    [
        dom.registerMessage,
        dom.loginMessage,
        dom.shortenMessage,
        dom.searchResults,
        dom.infoResults,
        dom.statsResults
    ].forEach(clearMessage);
}

function formatJson(data) {
    return JSON.stringify(data, null, 2);
}

function formatDate(value) {
    if (!value) {
        return "Не указано";
    }

    try {
        return new Date(value).toLocaleString();
    } catch {
        return value;
    }
}

function buildResultItem(label, value) {
    return `
        <div class="result-item">
            <div class="label">${escapeHtml(label)}</div>
            <div class="value">${value}</div>
        </div>
    `;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderLinkCard(data) {
    const owner = data.owner_user_id ? escapeHtml(data.owner_user_id) : "Анонимно";
    const expiresAt = data.expires_at ? escapeHtml(formatDate(data.expires_at)) : "Не ограничен";
    const lastUsedAt = data.last_used_at ? escapeHtml(formatDate(data.last_used_at)) : "Никогда";
    const fullShortUrl = escapeHtml(data.full_short_url);
    const originalUrl = escapeHtml(data.original_url);
    const shortCode = escapeHtml(data.short_code);
    const clicks = Number.isFinite(data.clicks) ? data.clicks : 0;

    return `
        <div class="result-grid">
            ${buildResultItem("Короткий код", shortCode)}
            ${buildResultItem("Исходный URL", originalUrl)}
            ${buildResultItem("Короткая ссылка", `<a href="${fullShortUrl}" target="_blank" rel="noopener noreferrer">${fullShortUrl}</a>`)}
            ${buildResultItem("Создана", escapeHtml(formatDate(data.created_at)))}
            ${buildResultItem("Обновлена", escapeHtml(formatDate(data.updated_at)))}
            ${buildResultItem("Истекает", expiresAt)}
            ${buildResultItem("Переходы", String(clicks))}
            ${buildResultItem("Последний переход", lastUsedAt)}
            ${buildResultItem("Владелец", owner)}
        </div>
    `;
}

function setLoading(button, isLoading, loadingText, defaultText) {
    if (!button) {
        return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading ? loadingText : defaultText;
}

async function handleRegister() {
    clearMessage(dom.registerMessage);

    const email = dom.registerEmail.value.trim();
    const password = dom.registerPassword.value;

    if (!email || !password) {
        showMessage(dom.registerMessage, "Заполните все поля.", "error");
        return;
    }

    if (password.length < 8) {
        showMessage(dom.registerMessage, "Пароль должен содержать не менее 8 символов.", "error");
        return;
    }

    if (new TextEncoder().encode(password).length > 72) {
        showMessage(dom.registerMessage, "Пароль не должен превышать 72 байта в кодировке UTF-8.", "error");
        return;
    }

    setLoading(dom.registerBtn, true, "Регистрация...", "Register");

    try {
        const data = await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        showMessage(dom.registerMessage, `Регистрация выполнена. Идентификатор пользователя: ${data.user_id}`, "success");
        dom.registerForm.reset();
        dom.loginEmail.value = email;
        dom.loginPassword.value = password;
    } catch (error) {
        showMessage(dom.registerMessage, `Ошибка регистрации: ${error.message}`, "error");
    } finally {
        setLoading(dom.registerBtn, false, "Регистрация...", "Register");
    }
}

async function handleLogin() {
    clearMessage(dom.loginMessage);

    const email = dom.loginEmail.value.trim();
    const password = dom.loginPassword.value;

    if (!email || !password) {
        showMessage(dom.loginMessage, "Заполните все поля.", "error");
        return;
    }

    setLoading(dom.loginBtn, true, "Вход...", "Login");

    try {
        const data = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        token = data.access_token;
        currentUser = email;

        localStorage.setItem("token", token);
        localStorage.setItem("currentUser", currentUser);

        updateAuthUI();
        dom.loginForm.reset();
        showMessage(dom.loginMessage, "Вход выполнен успешно.", "success");
    } catch (error) {
        showMessage(dom.loginMessage, `Ошибка входа: ${error.message}`, "error");
    } finally {
        setLoading(dom.loginBtn, false, "Вход...", "Login");
    }
}

function handleLogout() {
    token = null;
    currentUser = null;

    localStorage.removeItem("token");
    localStorage.removeItem("currentUser");

    updateAuthUI();
    clearAllMessages();
    showMessage(dom.loginMessage, "Выход выполнен.", "info");
}

async function handleShorten() {
    clearMessage(dom.shortenMessage);

    const originalUrl = dom.originalUrl.value.trim();
    const customAlias = dom.customAlias.value.trim();
    const expiresAtRaw = dom.expiresAt.value;

    if (!originalUrl) {
        showMessage(dom.shortenMessage, "Укажите исходный URL.", "error");
        return;
    }

    const body = {
        original_url: originalUrl
    };

    if (customAlias) {
        body.custom_alias = customAlias;
    }

    if (expiresAtRaw) {
        const localDate = new Date(expiresAtRaw);
        if (Number.isNaN(localDate.getTime())) {
            showMessage(dom.shortenMessage, "Некорректная дата истечения.", "error");
            return;
        }

        if (localDate.getSeconds() !== 0 || localDate.getMilliseconds() !== 0) {
            localDate.setSeconds(0, 0);
        }

        body.expires_at = localDate.toISOString();
    }

    setLoading(dom.shortenBtn, true, "Создание...", "Shorten Link");

    try {
        const data = await apiRequest("/links/shorten", {
            method: "POST",
            body: JSON.stringify(body)
        });

        displayShortenResult(data);
        dom.shortenForm.reset();
        showMessage(dom.shortenMessage, "Короткая ссылка создана.", "success");
    } catch (error) {
        showMessage(dom.shortenMessage, `Ошибка создания ссылки: ${error.message}`, "error");
    } finally {
        setLoading(dom.shortenBtn, false, "Создание...", "Shorten Link");
    }
}

function displayShortenResult(data) {
    if (!dom.resultCard || !dom.shortLink || !dom.resultJson) {
        return;
    }

    dom.resultCard.style.display = "block";
    dom.shortLink.href = data.full_short_url;
    dom.shortLink.textContent = data.full_short_url;
    dom.resultJson.textContent = formatJson(data);
}

async function handleSearch() {
    clearMessage(dom.searchResults);

    const originalUrl = dom.searchUrl.value.trim();

    if (!originalUrl) {
        showMessage(dom.searchResults, "Укажите URL для поиска.", "error");
        return;
    }

    setLoading(dom.searchBtn, true, "Поиск...", "Search");

    try {
        const encodedUrl = encodeURIComponent(originalUrl);
        const data = await apiRequest(`/links/search?original_url=${encodedUrl}&page=1&size=10`);
        displaySearchResults(data);
    } catch (error) {
        showMessage(dom.searchResults, `Ошибка поиска: ${error.message}`, "error");
    } finally {
        setLoading(dom.searchBtn, false, "Поиск...", "Search");
    }
}

function displaySearchResults(data) {
    if (!dom.searchResults) {
        return;
    }

    if (!data.items || data.items.length === 0) {
        dom.searchResults.innerHTML = '<div class="message info">Ссылки не найдены.</div>';
        return;
    }

    const itemsHtml = data.items
        .map((item) => {
            const fullShortUrl = escapeHtml(item.full_short_url);
            const originalUrl = escapeHtml(item.original_url);
            const shortCode = escapeHtml(item.short_code);
            const clicks = Number.isFinite(item.clicks) ? item.clicks : 0;

            return `
                <div class="result-item">
                    <div class="label">Короткий код</div>
                    <div class="value">${shortCode}</div>
                    <div class="label">Исходный URL</div>
                    <div class="value">${originalUrl}</div>
                    <div class="label">Короткая ссылка</div>
                    <div class="value"><a href="${fullShortUrl}" target="_blank" rel="noopener noreferrer">${fullShortUrl}</a></div>
                    <div class="label">Создана</div>
                    <div class="value">${escapeHtml(formatDate(item.created_at))}</div>
                    <div class="label">Переходы</div>
                    <div class="value">${clicks}</div>
                </div>
            `;
        })
        .join("");

    dom.searchResults.innerHTML = `
        <div class="message success">Найдено ссылок: ${data.items.length}</div>
        <div class="result-grid">${itemsHtml}</div>
    `;
}

async function handleGetInfo() {
    clearMessage(dom.infoResults);

    const shortCode = dom.infoShortCode.value.trim();

    if (!shortCode) {
        showMessage(dom.infoResults, "Укажите короткий код.", "error");
        return;
    }

    setLoading(dom.infoBtn, true, "Загрузка...", "Get Info");

    try {
        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}`);
        displayInfoResults(data);
    } catch (error) {
        showMessage(dom.infoResults, `Ошибка получения информации: ${error.message}`, "error");
    } finally {
        setLoading(dom.infoBtn, false, "Загрузка...", "Get Info");
    }
}

function displayInfoResults(data) {
    if (!dom.infoResults) {
        return;
    }

    dom.infoResults.innerHTML = `
        <div class="message success">Информация о ссылке получена.</div>
        ${renderLinkCard(data)}
    `;
}

async function handleGetStats() {
    clearMessage(dom.statsResults);

    const shortCode = dom.statsShortCode.value.trim();

    if (!shortCode) {
        showMessage(dom.statsResults, "Укажите короткий код.", "error");
        return;
    }

    setLoading(dom.statsBtn, true, "Загрузка...", "Get Stats");

    try {
        const data = await apiRequest(`/links/${encodeURIComponent(shortCode)}/stats`);
        displayStatsResults(data);
    } catch (error) {
        showMessage(dom.statsResults, `Ошибка получения статистики: ${error.message}`, "error");
    } finally {
        setLoading(dom.statsBtn, false, "Загрузка...", "Get Stats");
    }
}

function displayStatsResults(data) {
    if (!dom.statsResults) {
        return;
    }

    dom.statsResults.innerHTML = `
        <div class="message success">Статистика ссылки получена.</div>
        ${renderLinkCard(data)}
    `;
}