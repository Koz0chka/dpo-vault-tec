/* auth.js — страница входа. */
(function () {
  if (API.getToken()) {
    window.location.replace("/dashboard.html");
    return;
  }

  const form = document.getElementById("loginForm");
  const errBox = document.getElementById("errorBox");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(errBox);
    const fd = new FormData(form);
    const payload = {
      username: fd.get("username").trim(),
      master_password: fd.get("master_password"),
    };
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Входим…";
    try {
      const res = await API.login(payload);
      API.setToken(res.access_token, res.username);
      window.location.href = "/dashboard.html";
    } catch (err) {
      showError(errBox, err.message);
      btn.disabled = false;
      btn.textContent = "Войти";
    }
  });
})();
