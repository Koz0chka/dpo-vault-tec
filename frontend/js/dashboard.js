/* dashboard.js — главная страница: генератор, список, CRUD. */
(function () {
  if (!API.getToken()) {
    window.location.replace("/");
    return;
  }

  /* ----- Элементы DOM ----- */
  const userBadge     = document.getElementById("userBadge");
  const logoutBtn     = document.getElementById("logoutBtn");
  const listEl        = document.getElementById("passwordList");
  const countBadge    = document.getElementById("countBadge");
  const searchInput   = document.getElementById("searchInput");

  const genBtn        = document.getElementById("generateBtn");
  const genInput      = document.getElementById("generatedPassword");
  const copyGenBtn    = document.getElementById("copyGenBtn");
  const saveGenBtn    = document.getElementById("saveGenBtn");
  const lenRange      = document.getElementById("lengthRange");
  const lenLabel      = document.getElementById("lenLabel");
  const genStrength   = document.getElementById("genStrength");

  const createModal   = document.getElementById("createModal");
  const createForm    = document.getElementById("createForm");
  const createValue   = document.getElementById("createValue");
  const createError   = document.getElementById("createError");

  const renameModal   = document.getElementById("renameModal");
  const renameForm    = document.getElementById("renameForm");
  const renameError   = document.getElementById("renameError");

  /* ----- Состояние ----- */
  let allItems = [];          // без расшифрованных значений
  let lastGenerated = "";

  userBadge.textContent = "@" + API.getUsername();

  /* ===========================================================
     УТИЛИТЫ
     =========================================================== */

  function initials(name) {
    return (name || "?").trim().slice(0, 2).toUpperCase();
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso.replace(" ", "T") + "Z");
      return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
    } catch { return iso; }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Скопировано в буфер обмена", "success");
    } catch {
      // Фолбэк для старых браузеров
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); showToast("Скопировано", "success"); }
      catch { showToast("Не удалось скопировать", "error"); }
      document.body.removeChild(ta);
    }
  }

  /* ===========================================================
     ГЕНЕРАТОР
     =========================================================== */

  lenRange.addEventListener("input", () => { lenLabel.textContent = lenRange.value; });

  function strengthClass(s) {
    return ({
      "weak": "badge--weak",
      "medium": "badge--medium",
      "strong": "badge--strong",
      "very-strong": "badge--very-strong",
    })[s] || "badge--medium";
  }
  function strengthLabelRu(s) {
    return ({
      "weak": "слабый",
      "medium": "средний",
      "strong": "сильный",
      "very-strong": "очень сильный",
    })[s] || s;
  }

  async function doGenerate() {
    const payload = {
      length: parseInt(lenRange.value, 10),
      use_lower:    document.getElementById("opt_lower").checked,
      use_upper:    document.getElementById("opt_upper").checked,
      use_digits:   document.getElementById("opt_digits").checked,
      use_symbols:  document.getElementById("opt_symbols").checked,
      avoid_ambiguous: document.getElementById("opt_amb").checked,
    };
    genBtn.disabled = true;
    try {
      const res = await API.generate(payload);
      genInput.value = res.password;
      lastGenerated = res.password;
      genStrength.className = "badge " + strengthClass(res.strength);
      genStrength.textContent = strengthLabelRu(res.strength);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      genBtn.disabled = false;
    }
  }

  genBtn.addEventListener("click", doGenerate);

  copyGenBtn.addEventListener("click", () => {
    if (!genInput.value) { showToast("Сначала сгенерируйте пароль", "error"); return; }
    copyToClipboard(genInput.value);
  });

  saveGenBtn.addEventListener("click", () => {
    if (!lastGenerated) { showToast("Сначала сгенерируйте пароль", "error"); return; }
    openCreateModal("", lastGenerated);
  });

  /* ===========================================================
     СПИСОК ПАРОЛЕЙ
     =========================================================== */

  async function refreshList() {
    try {
      allItems = await API.listPasswords();
    } catch (err) {
      if (err.status === 401) { handleUnauth(); return; }
      listEl.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
      return;
    }
    renderList();
  }

  function renderList() {
    const q = (searchInput.value || "").trim().toLowerCase();
    const items = q ? allItems.filter((i) => i.name.toLowerCase().includes(q)) : allItems;
    countBadge.textContent = String(allItems.length);

    if (items.length === 0) {
      listEl.innerHTML = allItems.length === 0
        ? `<div class="empty-state">Пока нет сохранённых паролей.<br>Сгенерируйте новый или нажмите «Сохранить как новый пароль».</div>`
        : `<div class="empty-state">Ничего не найдено по запросу «${escapeHtml(q)}».</div>`;
      return;
    }

    listEl.innerHTML = items.map((item) => `
      <div class="pwd-item" data-id="${item.id}">
        <div class="pwd-item__name">
          <span class="pwd-item__icon">${escapeHtml(initials(item.name))}</span>
          <span class="pwd-item__name-text">${escapeHtml(item.name)}</span>
        </div>
        <div class="pwd-item__value masked" data-id="${item.id}">••••••••</div>
        <div class="pwd-item__meta">Обновлён ${formatDate(item.updated_at)}</div>
        <div class="pwd-item__actions">
          <button class="icon-btn reveal-btn" title="Показать">
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </button>
          <button class="icon-btn copy-btn" title="Скопировать">
            <svg viewBox="0 0 24 24" width="16" height="16"><rect x="9" y="9" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </button>
          <button class="icon-btn rename-btn" title="Переименовать">
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 20 L4 16 L16 4 L20 8 L8 20 Z" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </button>
          <button class="icon-btn danger delete-btn" title="Удалить">
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 7 H20 M9 7 V4 H15 V7 M6 7 L7 20 H17 L18 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </button>
        </div>
      </div>
    `).join("");

    /* Привязка обработчиков. */
    listEl.querySelectorAll(".pwd-item").forEach((row) => {
      const id = parseInt(row.dataset.id, 10);
      const valueEl = row.querySelector(".pwd-item__value");

      row.querySelector(".reveal-btn").addEventListener("click", async () => {
        if (valueEl.dataset.revealed === "1") {
          valueEl.textContent = "••••••••";
          valueEl.dataset.revealed = "0";
          valueEl.classList.add("masked");
          return;
        }
        try {
          const entry = await API.getPassword(id);
          valueEl.textContent = entry.value;
          valueEl.dataset.revealed = "1";
          valueEl.classList.remove("masked");
        } catch (err) {
          showToast(err.message, "error");
        }
      });

      row.querySelector(".copy-btn").addEventListener("click", async () => {
        try {
          const entry = await API.getPassword(id);
          await copyToClipboard(entry.value);
        } catch (err) {
          showToast(err.message, "error");
        }
      });

      row.querySelector(".rename-btn").addEventListener("click", () => {
        openRenameModal(id, row.querySelector(".pwd-item__name-text").textContent);
      });

      row.querySelector(".delete-btn").addEventListener("click", async () => {
        if (!confirm("Удалить эту запись безвозвратно?")) return;
        try {
          await API.deletePassword(id);
          allItems = allItems.filter((i) => i.id !== id);
          renderList();
          showToast("Запись удалена", "success");
        } catch (err) {
          showToast(err.message, "error");
        }
      });
    });
  }

  searchInput.addEventListener("input", renderList);

  /* ===========================================================
     МОДАЛКА: СОЗДАНИЕ
     =========================================================== */

  function openCreateModal(name = "", value = "") {
    createForm.reset();
    createForm.elements["name"].value = name;
    createValue.value = value;
    hideError(createError);
    createModal.hidden = false;
    setTimeout(() => createForm.elements["name"].focus(), 30);
  }

  createForm.querySelector(".generate-inline").addEventListener("click", async () => {
    try {
      const res = await API.generate({
        length: 16,
        use_lower: true, use_upper: true, use_digits: true, use_symbols: true,
      });
      createValue.value = res.password;
    } catch (err) { showToast(err.message, "error"); }
  });

  createForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(createError);
    const fd = new FormData(createForm);
    const payload = { name: fd.get("name").trim(), value: fd.get("value") };
    try {
      await API.createPassword(payload);
      createModal.hidden = true;
      await refreshList();
      showToast("Пароль сохранён", "success");
    } catch (err) {
      showError(createError, err.message);
    }
  });

  /* ===========================================================
     МОДАЛКА: ПЕРЕИМЕНОВАНИЕ
     =========================================================== */

  function openRenameModal(id, currentName) {
    renameForm.reset();
    renameForm.elements["id"].value = id;
    renameForm.elements["new_name"].value = currentName;
    hideError(renameError);
    renameModal.hidden = false;
    setTimeout(() => renameForm.elements["new_name"].focus(), 30);
  }

  renameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(renameError);
    const id = parseInt(renameForm.elements["id"].value, 10);
    const newName = renameForm.elements["new_name"].value.trim();
    try {
      const updated = await API.renamePassword(id, newName);
      const idx = allItems.findIndex((i) => i.id === id);
      if (idx !== -1) allItems[idx] = { ...allItems[idx], ...updated };
      renameModal.hidden = true;
      renderList();
      showToast("Переименовано", "success");
    } catch (err) {
      showError(renameError, err.message);
    }
  });

  /* ===========================================================
     ОБЩИЕ: ЗАКРЫТИЕ МОДАЛОК, ВЫХОД, ОШИБКИ АВТОРИЗАЦИИ
     =========================================================== */

  document.querySelectorAll("[data-close]").forEach((el) => {
    el.addEventListener("click", () => {
      createModal.hidden = true;
      renameModal.hidden = true;
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      createModal.hidden = true;
      renameModal.hidden = true;
    }
  });

  function handleUnauth() {
    API.clearToken();
    window.location.replace("/");
  }

  logoutBtn.addEventListener("click", async () => {
    try { await API.logout(); } catch { /* игнорируем */ }
    handleUnauth();
  });

  /* ===========================================================
     СТАРТ
     =========================================================== */
  refreshList();
})();
