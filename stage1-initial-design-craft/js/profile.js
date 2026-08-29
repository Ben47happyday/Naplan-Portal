(function () {
  const root = document.getElementById("profile-root");
  const YEAR_LABELS = { 3: "Year 3", 5: "Year 5", 7: "Year 7", 9: "Year 9" };

  NaplanAuth.me().then((user) => {
    if (!user) {
      window.location.href = "login.html?redirect=profile.html";
      return;
    }
    renderProfile(user);
    loadHistory();
  });

  function renderProfile(user) {
    root.innerHTML = `
      <h1>Hi, ${escapeHtml(user.display_name)}</h1>
      <p class="lede">${escapeHtml(user.email)} · ${YEAR_LABELS[user.year_level_id] || ""}</p>

      <div class="card-grid" style="margin-bottom:28px;">
        <div class="info-card">
          <h4>Your quiz history</h4>
          <p>Every practice test and level check you've completed, most recent first.</p>
        </div>
      </div>

      <div id="history-container"><p class="lede">Loading history…</p></div>
    `;

    if (window.NaplanFx) { NaplanFx.autoTagReveal(); NaplanFx.initReveal(); }
  }

  function loadHistory() {
    fetch("/api/me/attempts")
      .then((res) => res.json())
      .then(renderHistory)
      .catch(() => {
        document.getElementById("history-container").innerHTML =
          "<p class=\"lede\">Couldn't load your history right now.</p>";
      });
  }

  function renderHistory(attempts) {
    const container = document.getElementById("history-container");
    if (!attempts.length) {
      container.innerHTML = "<p class=\"lede\">No attempts yet — head to <a href=\"practice.html\">Practice</a> to get started.</p>";
      return;
    }

    const rows = attempts.map((a) => {
      const date = a.completed_at ? new Date(a.completed_at).toLocaleDateString() : "—";
      const score = a.score_percent !== null ? `${a.score_percent}%` : "Not auto-scored";
      return `
        <tr>
          <td>${date}</td>
          <td>${escapeHtml(a.test_title)}</td>
          <td>${escapeHtml(a.domain_name || "Mixed")}</td>
          <td>${score}</td>
          <td>${escapeHtml(a.band_estimate || "")}</td>
          <td><span class="view-link" data-attempt-id="${a.attempt_id}">View</span></td>
        </tr>
        <tr class="detail-row" id="detail-${a.attempt_id}" style="display:none;">
          <td colspan="6"></td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <div class="table-scroll">
        <table class="history-table">
          <thead>
            <tr><th>Date</th><th>Test</th><th>Domain</th><th>Score</th><th>Result</th><th></th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;

    container.querySelectorAll(".view-link").forEach((link) => {
      link.addEventListener("click", () => toggleDetail(link.dataset.attemptId));
    });
  }

  function toggleDetail(attemptId) {
    const row = document.getElementById(`detail-${attemptId}`);
    const cell = row.querySelector("td");

    if (row.style.display !== "none") {
      row.style.display = "none";
      return;
    }
    row.style.display = "table-row";
    if (cell.dataset.loaded) return;

    cell.innerHTML = "Loading…";
    fetch(`/api/attempts/${attemptId}`)
      .then((res) => res.json())
      .then((data) => {
        cell.dataset.loaded = "true";
        cell.innerHTML = renderFeedback(data);
      });
  }

  function renderFeedback(data) {
    const comments = (data.feedback.comments || []).map((c) => `<p>${escapeHtml(c)}</p>`).join("");
    const domainRows = (data.feedback.domain_accuracy || []).map((d) =>
      `<span class="meta" style="margin-right:8px;">${escapeHtml(d.domain_name)}: ${d.accuracy}%</span>`
    ).join("");

    const questionRows = data.results.map((r) => {
      if (r.writing_assessment) {
        const wa = r.writing_assessment;
        const criteriaHtml = wa.criteria.map((c) =>
          `<span class="meta" style="margin-right:8px;">${escapeHtml(c.name)}: ${c.score}/${c.max}</span>`
        ).join("");
        const waComments = wa.comments.map((c) => `<p>${escapeHtml(c)}</p>`).join("");
        return `
          <div class="info-card question-card">
            <p>${escapeHtml(r.prompt)} <span class="meta" style="color:#854F0B;background:#FAEEDA;">Writing score: ${wa.score_percent}/100</span></p>
            <p style="white-space:pre-wrap;background:var(--cream-2);border-radius:10px;padding:10px 12px;">${escapeHtml(r.student_answer || "(no answer)")}</p>
            <div style="margin:10px 0;">${criteriaHtml}</div>
            <div class="feedback-box" style="margin:0;">${waComments}</div>
          </div>
        `;
      }
      return `
      <div class="info-card question-card">
        <p>${escapeHtml(r.prompt)}</p>
        <p><strong>Your answer:</strong> ${escapeHtml(r.student_answer || "(no answer)")}</p>
        ${r.is_correct === false ? `<p><strong>Correct answer:</strong> ${escapeHtml(r.correct_answer)}</p>` : ""}
      </div>
    `;
    }).join("");

    return `
      <div class="feedback-box">
        ${comments}
        <div style="margin-top:8px;">${domainRows}</div>
      </div>
      ${questionRows}
    `;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }
})();
