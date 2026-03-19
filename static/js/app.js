/**
 * WAS Contábil — JS mínimo
 *
 * 1. HTMX config (CSRF token no header para Django)
 * 2. Dark mode toggle (localStorage)
 */

// ==============================================
// HTMX: CSRF Token no header de todas as requests
// ==============================================
document.addEventListener("DOMContentLoaded", function () {
  // Django com CSRF_COOKIE_HTTPONLY=True: lê o token do input hidden
  // gerado por {% csrf_token %} no base.html
  var csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
  var csrfToken = csrfInput ? csrfInput.value : "";

  // Configura HTMX para enviar CSRF token em todas as requests
  document.body.addEventListener("htmx:configRequest", function (event) {
    event.detail.headers["X-CSRFToken"] = csrfToken;
  });
});

// ==============================================
// Dark mode: inicializar a partir do localStorage
// ==============================================
(function () {
  // Aplica dark mode antes da renderização para evitar flash
  if (localStorage.getItem("darkMode") === "true") {
    document.documentElement.classList.add("dark");
  }
})();
