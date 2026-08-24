(function () {
  const root = document.getElementById("quiz-root");
  const params = new URLSearchParams(window.location.search);
  const testId = params.get("test_id");

  if (!testId) {
    root.innerHTML = "<p class=\"lede\">No test selected. Go back to <a href=\"practice.html\">Practice</a>.</p>";
    return;
  }

  const redirectTarget = encodeURIComponent(`quiz.html?test_id=${testId}`);

  NaplanAuth.me().then((user) => {
    if (!user) {
      root.innerHTML = `
        <div class="diagnostic-banner">
          <div>
            <h3><i class="ti ti-lock"></i> Log in to take this quiz</h3>
            <p>Logging in lets us mark your answers instantly and save the result to your history.</p>
          </div>
          <a class="btn btn-primary" href="login.html?redirect=${redirectTarget}">Log in</a>
        </div>
        <p class="lede">New here? <a href="signup.html?redirect=${redirectTarget}">Create an account</a> — it only takes a minute.</p>
      `;
      return;
    }
    loadQuiz();
  });

  function loadQuiz() {
    fetch(`/api/tests/${testId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Test not found");
        return res.json();
      })
      .then(renderQuiz)
      .catch(() => {
        root.innerHTML = "<p class=\"lede\">Couldn't load that test. Go back to <a href=\"practice.html\">Practice</a>.</p>";
      });
  }

  function renderQuiz(test) {
    const questionsHtml = test.questions.map((q, i) => renderQuestion(q, i)).join("");

    const editionLabel = test.content_year ? `${test.content_year} edition · ` : "Classic · ";
    root.innerHTML = `
      <h1>${escapeHtml(test.title)}</h1>
      <p class="lede">${editionLabel}${test.domain_name ? escapeHtml(test.domain_name) + " · " : ""}${test.questions.length} questions · about ${test.time_limit_mins} mins</p>
      <form id="quiz-form">
        ${questionsHtml}
        <button type="submit" class="btn btn-primary">Submit answers</button>
      </form>
    `;

    document.getElementById("quiz-form").addEventListener("submit", (e) => {
      e.preventDefault();
      submitQuiz(test);
    });

    root.querySelectorAll(".check-btn").forEach((btn) => {
      btn.addEventListener("click", () => checkAnswer(btn.dataset.questionId));
    });

    root.querySelectorAll(".option-list").forEach((list) => {
      list.addEventListener("change", (e) => {
        if (e.target.type !== "radio") return;
        list.querySelectorAll(".option-row").forEach((row) => row.classList.remove("option-row--selected"));
        e.target.closest(".option-row").classList.add("option-row--selected");
      });
    });

    if (window.NaplanFx) { NaplanFx.autoTagReveal(); NaplanFx.initReveal(); }
  }

  function renderQuestion(q, index) {
    let inputHtml;
    if (q.options && q.options.length) {
      inputHtml = q.options.map((opt) => `
        <label class="option-row">
          <input type="radio" name="q_${q.question_id}" value="${escapeHtml(opt.text)}">
          <span>${opt.key}. ${escapeHtml(opt.text)}</span>
        </label>
      `).join("");
    } else {
      inputHtml = `<textarea name="q_${q.question_id}" rows="4" placeholder="Write your answer here…"></textarea>`;
    }

    const isNumeracy = q.domain_name === "Numeracy";
    const checkRow = isNumeracy ? `
      <div style="margin-top:12px;">
        <button type="button" class="btn btn-secondary btn-small check-btn" data-question-id="${q.question_id}">Check answer</button>
        <div id="check-feedback-${q.question_id}" style="margin-top:10px;"></div>
      </div>
    ` : "";

    const diagramHtml = q.media_url
      ? `<div class="question-diagram"><img src="${escapeHtml(q.media_url)}" alt="Diagram for question ${index + 1}" loading="lazy"></div>`
      : "";

    return `
      <div class="info-card question-card">
        <h4>Question ${index + 1}${q.domain_name ? ` · ${escapeHtml(q.domain_name)}` : ""}</h4>
        ${diagramHtml}
        <p>${escapeHtml(q.prompt)}</p>
        <div class="option-list">${inputHtml}</div>
        ${checkRow}
      </div>
    `;
  }

  function checkAnswer(questionId) {
    const form = document.getElementById("quiz-form");
    const field = form.elements[`q_${questionId}`];
    const feedbackEl = document.getElementById(`check-feedback-${questionId}`);
    const selected = field instanceof RadioNodeList
      ? Array.from(field).find((el) => el.checked)
      : field;

    if (!selected || !selected.value) {
      feedbackEl.innerHTML = `<p class="meta" style="display:block;background:none;padding:0;color:#993C1D;">Pick an answer first, then check.</p>`;
      return;
    }

    feedbackEl.innerHTML = `<p class="meta">Checking…</p>`;
    fetch(`/api/questions/${questionId}/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: selected.value }),
    })
      .then((res) => res.json())
      .then((result) => {
        const style = result.is_correct
          ? "color:#3B6D11;background:#EAF3DE;"
          : "color:#993C1D;background:#FAECE7;";
        feedbackEl.innerHTML = `
          <span class="meta" style="${style}">${result.is_correct ? "Correct!" : "Not quite — try again"}</span>
          ${!result.is_correct ? `<p class="meta" style="display:block;background:none;padding:6px 0 0;color:#8A7A67;">${escapeHtml(result.explanation || "")}</p>` : ""}
        `;
      });
  }

  function submitQuiz(test) {
    const form = document.getElementById("quiz-form");
    const answers = {};
    test.questions.forEach((q) => {
      const field = form.elements[`q_${q.question_id}`];
      if (!field) return;
      if (field instanceof RadioNodeList) {
        const checked = Array.from(field).find((el) => el.checked);
        answers[q.question_id] = checked ? checked.value : null;
      } else {
        answers[q.question_id] = field.value || null;
      }
    });

    fetch(`/api/tests/${test.test_id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    })
      .then(async (res) => {
        if (res.status === 401) {
          window.location.href = `login.html?redirect=${redirectTarget}`;
          return null;
        }
        return res.json();
      })
      .then((result) => {
        if (result) renderResults(test, result);
      });
  }

  function renderResults(test, result) {
    const rowsHtml = result.results.map((r, i) => {
      const q = test.questions.find((q) => q.question_id === r.question_id);

      if (r.writing_assessment) {
        return renderWritingResult(i, q, r);
      }

      const status = r.is_correct === null
        ? "<span class=\"meta\">Not auto-marked</span>"
        : r.is_correct
          ? "<span class=\"meta\" style=\"color:#3B6D11;background:#EAF3DE;\">Correct</span>"
          : "<span class=\"meta\" style=\"color:#993C1D;background:#FAECE7;\">Incorrect</span>";

      return `
        <div class="info-card question-card">
          <h4>Question ${i + 1} ${status}</h4>
          <p>${escapeHtml(q ? q.prompt : "")}</p>
          <p><strong>Your answer:</strong> ${escapeHtml(r.student_answer || "(no answer)")}</p>
          ${r.is_correct === false ? `<p><strong>Correct answer:</strong> ${escapeHtml(r.correct_answer)}</p>` : ""}
          ${r.explanation ? `<p class="meta" style="display:block;background:none;padding:0;color:#8A7A67;">${escapeHtml(r.explanation)}</p>` : ""}
        </div>
      `;
    }).join("");

    const feedback = result.feedback || { comments: [], domain_accuracy: [], suggestions: [] };
    const commentsHtml = feedback.comments.map((c) => `<p>${escapeHtml(c)}</p>`).join("");
    const domainHtml = feedback.domain_accuracy.map((d) =>
      `<span class="meta" style="margin-right:8px;">${escapeHtml(d.domain_name)}: ${d.accuracy}%</span>`
    ).join("");
    const suggestionLinks = feedback.suggestions.map((s) =>
      `<a class="btn btn-secondary btn-small" style="margin-top:10px;" href="quiz.html?test_id=${s.test_id}">Try: ${escapeHtml(s.title)}</a>`
    ).join(" ");

    root.innerHTML = `
      <div class="diagnostic-banner">
        <div>
          <h3><i class="ti ti-gauge"></i> ${result.score_percent !== null ? result.score_percent + "% correct" : "Submitted"}</h3>
          <p>${escapeHtml(result.band_estimate)}</p>
        </div>
        <a class="btn btn-primary" href="practice.html">Back to practice</a>
      </div>
      ${(commentsHtml || domainHtml) ? `
        <div class="feedback-box">
          ${commentsHtml}
          <div style="margin-top:8px;">${domainHtml}</div>
          ${suggestionLinks}
        </div>
      ` : ""}
      ${rowsHtml}
    `;

    if (window.NaplanFx) { NaplanFx.autoTagReveal(); NaplanFx.initReveal(); }
  }

  function renderWritingResult(index, q, r) {
    const wa = r.writing_assessment;
    const criteriaHtml = wa.criteria.map((c) =>
      `<span class="meta" style="margin-right:8px;">${escapeHtml(c.name)}: ${c.score}/${c.max}</span>`
    ).join("");
    const commentsHtml = wa.comments.map((c) => `<p>${escapeHtml(c)}</p>`).join("");

    return `
      <div class="info-card question-card">
        <h4>Question ${index + 1} <span class="meta" style="color:#854F0B;background:#FAEEDA;">Writing score: ${wa.score_percent}/100</span></h4>
        <p>${escapeHtml(q ? q.prompt : "")}</p>
        <p><strong>Your response:</strong></p>
        <p style="white-space:pre-wrap;background:var(--cream-2);border-radius:10px;padding:10px 12px;">${escapeHtml(r.student_answer || "(no answer)")}</p>
        <div style="margin:10px 0;">${criteriaHtml}</div>
        <div class="feedback-box" style="margin:0;">${commentsHtml}</div>
      </div>
    `;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }
})();
