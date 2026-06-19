/* register.js — страница регистрации + оценка силы мастер-пароля. */
(function () {
  if (API.getToken()) {
    window.location.replace("/dashboard.html");
    return;
  }

  const form = document.getElementById("registerForm");
  const errBox = document.getElementById("errorBox");
  const masterInput = document.getElementById("master_password");
  const strengthBar = document.getElementById("strengthBar");
  const strengthLabel = document.getElementById("strengthLabel");

  function evalStrength(pwd) {
    let pool = 0;
    if (/[a-z]/.test(pwd)) pool += 26;
    if (/[A-Z]/.test(pwd)) pool += 26;
    if (/[0-9]/.test(pwd)) pool += 10;
    if (/[^A-Za-z0-9]/.test(pwd)) pool += 24;
    if (!pwd) return { cls: "", label: "Минимум 8 символов" };
    const entropy = pool ? pwd.length * Math.log2(pool) : 0;
    if (entropy < 40) return { cls: "weak", label: "Слабый пароль" };
    if (entropy < 60) return { cls: "medium", label: "Средний пароль" };
    if (entropy < 80) return { cls: "strong", label: "Сильный пароль" };
    return { cls: "very-strong", label: "Очень сильный пароль" };
  }

  masterInput.addEventListener("input", () => {
    const { cls, label } = evalStrength(masterInput.value);
    strengthBar.className = "strength-bar " + cls;
    strengthLabel.textContent = label;
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(errBox);
    const fd = new FormData(form);
    const username = fd.get("username").trim();
    const master = fd.get("master_password");
    const confirm = fd.get("confirm_password");

    if (master !== confirm) {
      showError(errBox, "Мастер-пароли не совпадают");
      return;
    }
    if (master.length < 8) {
      showError(errBox, "Мастер-пароль должен быть не короче 8 символов");
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Создаём…";
    try {
      const res = await API.register({ username, master_password: master });
      API.setToken(res.access_token, res.username);
      window.location.href = "/dashboard.html";
    } catch (err) {
      showError(errBox, err.message);
      btn.disabled = false;
      btn.textContent = "Зарегистрироваться";
    }
  });
})();
