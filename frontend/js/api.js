/* api.js — минимальная обёртка над fetch + хранение токена в localStorage. */

const API = (function () {
  const TOKEN_KEY = "pv_token";
  const USER_KEY  = "pv_username";

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    if (username) localStorage.setItem(USER_KEY, username);
  }
  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function getUsername() { return localStorage.getItem(USER_KEY) || ""; }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body !== undefined) opts.body = JSON.stringify(body);

    let res;
    try {
      res = await fetch(path, opts);
    } catch (e) {
      throw new Error("Не удалось связаться с сервером");
    }

    if (res.status === 204) return null;

    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      try { data = await res.json(); } catch { data = null; }
    }

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || `Ошибка ${res.status}`;
      const err = new Error(msg);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  return {
    getToken, setToken, clearToken, getUsername,

    health:        () => request("GET", "/api/health"),
    register: (b)  => request("POST", "/api/auth/register", b),
    login:    (b)  => request("POST", "/api/auth/login", b),
    logout:   ()   => request("POST", "/api/auth/logout"),

    listPasswords: () => request("GET", "/api/passwords"),
    getPassword:  (id) => request("GET", `/api/passwords/${id}`),
    createPassword: (b) => request("POST", "/api/passwords", b),
    renamePassword: (id, new_name) => request("PATCH", `/api/passwords/${id}/name`, { new_name }),
    updatePassword: (id, new_value) => request("PATCH", `/api/passwords/${id}/value`, { new_value }),
    deletePassword: (id) => request("DELETE", `/api/passwords/${id}`),
    generate: (b) => request("POST", "/api/passwords/generate", b),
  };
})();

/* Утилиты для UI — доступны всем страницам. */
function showError(boxEl, message) {
  if (!boxEl) return;
  boxEl.textContent = message;
  boxEl.hidden = false;
}
function hideError(boxEl) {
  if (!boxEl) return;
  boxEl.hidden = true;
  boxEl.textContent = "";
}
function showToast(message, kind = "info", timeout = 2200) {
  const t = document.getElementById("toast");
  if (!t) { alert(message); return; }
  t.textContent = message;
  t.className = "toast" + (kind ? ` toast--${kind}` : "");
  t.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { t.hidden = true; }, timeout);
}

/* Переключение видимости пароля. */
function bindPasswordToggles(root = document) {
  root.querySelectorAll(".toggle-pwd").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      const input = document.getElementById(target) || document.querySelector(`input[name="${target}"]`);
      if (!input) return;
      input.type = input.type === "password" ? "text" : "password";
    });
  });
}

document.addEventListener("DOMContentLoaded", () => bindPasswordToggles());
