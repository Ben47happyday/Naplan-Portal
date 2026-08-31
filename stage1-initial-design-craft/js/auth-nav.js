// Shared auth-aware header: swaps the Log in/Sign up links for a
// profile/logout link when a session is active. Include on every page.

// Resolves API paths against wherever this app is actually mounted —
// domain root in dev, or a sub-path (e.g. /solutions/naplanhub/) in
// production — instead of hardcoding a root-absolute "/api/...".
const NAPLAN_BASE_PATH = location.pathname.replace(/[^/]*$/, "");
function apiUrl(path) {
  return NAPLAN_BASE_PATH + path.replace(/^\//, "");
}

const NaplanAuth = (function () {
  function me() {
    return fetch(apiUrl("/api/auth/me")).then((res) => (res.ok ? res.json() : null));
  }

  function logout() {
    return fetch(apiUrl("/api/auth/logout"), { method: "POST" });
  }

  function renderNav() {
    const slot = document.getElementById("auth-slot");
    if (!slot) return me();

    return me().then((user) => {
      if (user) {
        slot.innerHTML = `
          <a href="profile.html" class="auth-login-link">Hi, ${escapeHtml(user.display_name)}</a>
          <a href="#" class="btn btn-secondary btn-small" id="logout-btn">Log out</a>
        `;
        document.getElementById("logout-btn").addEventListener("click", (e) => {
          e.preventDefault();
          logout().then(() => window.location.href = "index.html");
        });
      }
      return user;
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }

  renderNav();
  return { me, logout, renderNav };
})();
