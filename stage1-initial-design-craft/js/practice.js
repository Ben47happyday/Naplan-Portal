(function () {
  const list = document.getElementById("test-list");
  const tabs = document.querySelectorAll("#domain-tabs .tab");
  const yearTabs = document.querySelectorAll("#year-tabs .tab");
  const editionSelect = document.getElementById("edition-select");
  let YEAR = NaplanYear.get();
  NaplanYear.propagateToLinks(document.body);

  const lede = document.querySelector(".page-section .lede");
  function updateLede() {
    if (lede) lede.textContent = `Real style Year ${YEAR} questions, marked instantly with a worked explanation for every answer.`;
  }
  updateLede();

  const ICONS = {
    R: { image: "images/icon-book-cartoon.svg", color: "#854F0B" },
    W: { image: "images/icon-pencil-cartoon.svg", color: "#993C1D" },
    LC: { image: "images/icon-abc-cartoon.svg", color: "#993C1D" },
    N: { image: "images/icon-calculator-cartoon.svg", color: "#3B6D11" },
  };
  const DEFAULT_ICON = { image: "images/icon-book-cartoon.svg", color: "#854F0B" };

  const DOMAIN_DESCRIPTIONS = {
    "": "Browse every practice set for this year level, or filter by domain using the tabs above.",
    R: "Comprehension passages testing understanding, inference and vocabulary across different text types.",
    W: "One narrative or persuasive writing task, scored on structure, ideas, language and grammar.",
    LC: "Spelling, grammar and punctuation, tested through short, focused items.",
    N: "Number, algebra, measurement, geometry, statistics and problem solving.",
  };

  function updateDescription(domainCode) {
    const el = document.getElementById("domain-description");
    if (el) el.textContent = DOMAIN_DESCRIPTIONS[domainCode || ""];
  }

  const skillSection = document.getElementById("skill-practice-section");
  const strandChips = document.getElementById("strand-chips");
  let strandsLoaded = false;

  function toggleSkillSection(domainCode) {
    if (domainCode !== "N") {
      skillSection.style.display = "none";
      return;
    }
    skillSection.style.display = "block";
    if (!strandsLoaded) loadStrands();
  }

  function loadStrands() {
    strandsLoaded = true;
    fetch(apiUrl(`/api/numeracy-strands?year=${YEAR}`))
      .then((res) => res.json())
      .then((strands) => {
        strandChips.innerHTML = strands.map((s) =>
          `<span class="tab" data-strand="${escapeHtml(s.strand)}">${escapeHtml(s.strand)} <span class="meta" style="margin-left:4px;">${s.question_count}</span></span>`
        ).join("");
        strandChips.querySelectorAll(".tab").forEach((chip) => {
          chip.addEventListener("click", () => startSkillPractice(chip.dataset.strand, chip));
        });
      });
  }

  function startSkillPractice(strand, chipEl) {
    NaplanAuth.me().then((user) => {
      if (!user) {
        window.location.href = `login.html?redirect=${encodeURIComponent("practice.html?year=" + YEAR)}`;
        return;
      }
      const originalText = chipEl.textContent;
      chipEl.textContent = "Loading…";
      fetch(apiUrl("/api/numeracy/practice-set"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year_level: YEAR, strand, limit: 8 }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.test_id) {
            window.location.href = `quiz.html?test_id=${data.test_id}`;
          } else {
            chipEl.textContent = originalText;
          }
        });
    });
  }

  function loadEditions() {
    fetch(apiUrl(`/api/editions?year=${YEAR}`))
      .then((res) => res.json())
      .then((editions) => {
        editionSelect.innerHTML = editions.map((e) => {
          const label = e.is_legacy ? "Classic (always available)" : `${e.content_year} edition${e.is_current ? " (latest)" : ""}`;
          const value = e.is_legacy ? "legacy" : e.content_year;
          return `<option value="${value}">${label}</option>`;
        }).join("") + `<option value="all">All editions</option>`;
        // Default: whichever edition is flagged current, falling back to the first option.
        const current = editions.find((e) => e.is_current);
        if (current) editionSelect.value = current.content_year;
      });
  }

  function currentDomain() {
    const active = document.querySelector("#domain-tabs .tab.active");
    return active ? active.dataset.domain : "";
  }

  function loadTests() {
    list.innerHTML = "<p class=\"lede\">Loading practice tests…</p>";
    const url = new URL(apiUrl("/api/tests"), window.location.origin);
    url.searchParams.set("year", YEAR);
    url.searchParams.set("type", "practice");
    const domainCode = currentDomain();
    if (domainCode) url.searchParams.set("domain", domainCode);
    if (editionSelect.value) url.searchParams.set("content_year", editionSelect.value);

    fetch(url)
      .then((res) => res.json())
      .then(renderTests)
      .catch(() => {
        list.innerHTML = "<p class=\"lede\">Couldn't load practice tests. Is the backend running?</p>";
      });
  }

  const DOMAIN_ORDER = ["R", "W", "LC", "N"];

  function groupByDomain(tests) {
    const groups = {};
    tests.forEach((t) => {
      const key = t.domain_code || "";
      if (!groups[key]) groups[key] = { domain_code: key, domain_name: t.domain_name || "Mixed", tests: [] };
      groups[key].tests.push(t);
    });
    return Object.values(groups).sort((a, b) => {
      const ai = DOMAIN_ORDER.indexOf(a.domain_code);
      const bi = DOMAIN_ORDER.indexOf(b.domain_code);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });
  }

  function renderTests(tests) {
    if (!tests.length) {
      list.innerHTML = "<p class=\"lede\">No practice tests found for this filter yet.</p>";
      return;
    }

    const groups = groupByDomain(tests);

    list.innerHTML = groups.map((group, gi) => {
      const icon = ICONS[group.domain_code] || DEFAULT_ICON;
      const desc = DOMAIN_DESCRIPTIONS[group.domain_code] || DOMAIN_DESCRIPTIONS[""];

      const rowsHtml = group.tests.map((t) => {
        const editionLabel = t.content_year ? `${t.content_year} edition` : "Classic edition";
        return `
          <a class="quiz-row" href="quiz.html?test_id=${t.test_id}">
            <span class="icon-circle" style="background:${icon.color}1A;"><img src="${icon.image}" alt="" width="20" height="20"></span>
            <span class="quiz-copy">
              <h4>${escapeHtml(t.title)}</h4>
              <p>${desc}</p>
            </span>
            <span class="quiz-meta">
              <span class="meta">${editionLabel}</span>
              <span class="meta" style="color:${icon.color};background:${icon.color}1A;">${t.question_count} q · ${t.time_limit_mins} min</span>
            </span>
            <i class="ti ti-chevron-right go-arrow"></i>
          </a>
        `;
      }).join("");

      return `
        <details class="quiz-category reveal"${gi === 0 ? " open" : ""}>
          <summary class="quiz-category-header">
            <span class="icon-circle" style="background:${icon.color}1A;"><img src="${icon.image}" alt="" width="24" height="24"></span>
            <span class="category-copy">
              <h3>${escapeHtml(group.domain_name)}</h3>
              <p>${desc}</p>
            </span>
            <span class="category-count">${group.tests.length} set${group.tests.length === 1 ? "" : "s"}</span>
            <i class="ti ti-chevron-down chevron"></i>
          </summary>
          <div class="quiz-category-body">${rowsHtml}</div>
        </details>
      `;
    }).join("");

    if (window.NaplanFx) { NaplanFx.autoTagReveal(); NaplanFx.initReveal(); }
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      updateDescription(tab.dataset.domain);
      toggleSkillSection(tab.dataset.domain);
      loadTests();
    });
  });

  editionSelect.addEventListener("change", loadTests);

  NaplanYear.wirePicker(yearTabs, "active", (y) => {
    YEAR = y;
    strandsLoaded = false;
    updateLede();
    NaplanYear.propagateToLinks(document.body);
    toggleSkillSection(currentDomain());
    loadEditions();
    loadTests();
  });

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }

  updateDescription("");
  loadEditions();
  loadTests();
})();
