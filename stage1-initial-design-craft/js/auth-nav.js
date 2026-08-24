// Shared auth-aware header: swaps the Log in/Sign up links for a
// profile/logout link when a session is active. Include on every page.
const NaplanAuth = (function () {
  function me() {
    return fetch("/api/auth/me").then((res) => (res.ok ? res.json() : null));
  }

  function logout() {
    return fetch("/api/auth/logout", { method: "POST" });
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
