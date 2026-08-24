(function () {
  const YEAR_CONTENT = {
    3: {
      format: "Reading, language conventions and numeracy are on paper or a simplified online interface with larger text and buttons. Writing stays entirely on paper, per ACARA policy.",
      domains: [
        { icon: "ti-book", color: "#854F0B", name: "Reading", time: "45 mins", questions: "approx. 32 questions",
          desc: "Shorter comprehension passages testing understanding, inference and vocabulary, in the simplest format of any year level." },
        { icon: "ti-pencil", color: "#993C1D", name: "Writing", time: "40 mins", questions: "1 writing task",
          desc: "One narrative or persuasive task, scored on structure, ideas, language and grammar — the only year level still completed on paper." },
        { icon: "ti-abc", color: "#993C1D", name: "Language conventions", time: "45 mins", questions: "approx. 40 questions",
          desc: "Spelling, grammar and punctuation across short items, using simple, first-time-test-taker-friendly wording." },
        { icon: "ti-calculator", color: "#3B6D11", name: "Numeracy", time: "45 mins", questions: "approx. 32 questions",
          desc: "Number, measurement and geometry basics. Not adaptive — every Year 3 student sees the same question set." },
      ],
    },
    5: {
      format: "Fully online for Reading, Writing, Language Conventions and Numeracy. This is the first year level where Reading and Numeracy use adaptive difficulty.",
      domains: [
        { icon: "ti-book", color: "#854F0B", name: "Reading", time: "50 mins", questions: "approx. 40 questions",
          desc: "Longer comprehension passages across more text types, testing understanding, inference and vocabulary. Adaptive: questions get easier or harder based on how your child is going." },
        { icon: "ti-pencil", color: "#993C1D", name: "Writing", time: "42 mins", questions: "1 writing task",
          desc: "One narrative or persuasive task, scored on structure, ideas, language and grammar — fully online from this year level." },
        { icon: "ti-abc", color: "#993C1D", name: "Language conventions", time: "45 mins", questions: "approx. 45 questions",
          desc: "Spelling, grammar and punctuation, with a wider difficulty range than Year 3." },
        { icon: "ti-calculator", color: "#3B6D11", name: "Numeracy", time: "50 mins", questions: "approx. 40 questions",
          desc: "Number, algebra, measurement, geometry and statistics. Adaptive in difficulty." },
      ],
    },
    7: {
      format: "Fully online across all four domains. Reading and Numeracy remain adaptive, with longer passages and more multi-step problems than Year 5.",
      domains: [
        { icon: "ti-book", color: "#854F0B", name: "Reading", time: "65 mins", questions: "approx. 42 questions",
          desc: "Longer, more complex passages including persuasive and analytical texts, with higher-level inference questions. Adaptive." },
        { icon: "ti-pencil", color: "#993C1D", name: "Writing", time: "42 mins", questions: "1 writing task",
          desc: "One narrative or persuasive task, assessed on the same criteria but expecting more developed structure and vocabulary." },
        { icon: "ti-abc", color: "#993C1D", name: "Language conventions", time: "45 mins", questions: "approx. 50 questions",
          desc: "Spelling, grammar and punctuation across more complex sentence structures." },
        { icon: "ti-calculator", color: "#3B6D11", name: "Numeracy", time: "65 mins", questions: "approx. 48 questions",
          desc: "Number, algebra, measurement, geometry, statistics and problem solving, adaptive, with more multi-step problems." },
      ],
    },
    9: {
      format: "Fully online across all four domains, using the most advanced item bank. Reading and Numeracy stay adaptive.",
      domains: [
        { icon: "ti-book", color: "#854F0B", name: "Reading", time: "65 mins", questions: "approx. 44 questions",
          desc: "The most advanced reading item bank, with dense and abstract passages across a wide range of text types. Adaptive." },
        { icon: "ti-pencil", color: "#993C1D", name: "Writing", time: "42 mins", questions: "1 writing task",
          desc: "One narrative or persuasive task, assessed on the same criteria, expecting sophisticated control of language." },
        { icon: "ti-abc", color: "#993C1D", name: "Language conventions", time: "45 mins", questions: "approx. 50 questions",
          desc: "Spelling, grammar and punctuation covering the full secondary curriculum range." },
        { icon: "ti-calculator", color: "#3B6D11", name: "Numeracy", time: "65 mins", questions: "approx. 50 questions",
          desc: "The most advanced numeracy item bank — algebra, statistics and multi-step problem solving feature heavily. Adaptive." },
      ],
    },
  };

  const tabs = Array.from(document.querySelectorAll("#year-tabs .tab"));
  const cardsEl = document.getElementById("domain-cards");
  const lede = document.querySelector(".page-section .lede");

  function render(year) {
    const data = YEAR_CONTENT[year];
    cardsEl.innerHTML = data.domains.map((d) => `
      <div class="info-card">
        <h4><i class="ti ${d.icon}" style="color:${d.color};"></i> ${d.name}</h4>
        <p>${d.desc}</p>
        <span class="meta">${d.time}</span>
        <span class="meta" style="color:${d.color};background:${d.color}1A;">${d.questions}</span>
      </div>
    `).join("");

    const formatNote = document.getElementById("format-note");
    if (formatNote) formatNote.textContent = data.format;

    if (window.NaplanFx) { NaplanFx.autoTagReveal(); NaplanFx.initReveal(); }
  }

  function wireMoreDetails() {
    document.querySelectorAll(".more-details-btn").forEach((btn) => {
      const panel = document.getElementById(btn.dataset.target);
      if (!panel) return;
      btn.addEventListener("click", () => {
        const willOpen = !panel.classList.contains("open");
        panel.classList.toggle("open", willOpen);
        btn.classList.toggle("expanded", willOpen);
        btn.setAttribute("aria-expanded", String(willOpen));
        btn.innerHTML = willOpen
          ? `Less details <i class="ti ti-chevron-down"></i>`
          : `More details <i class="ti ti-chevron-down"></i>`;
      });
    });
  }

  function wireFaq() {
    document.querySelectorAll(".faq-question").forEach((btn) => {
      const panel = document.getElementById(btn.dataset.target);
      if (!panel) return;
      btn.addEventListener("click", () => {
        const willOpen = !panel.classList.contains("open");
        panel.classList.toggle("open", willOpen);
        btn.classList.toggle("expanded", willOpen);
        btn.setAttribute("aria-expanded", String(willOpen));
      });
    });
  }

  const year = NaplanYear.wirePicker(tabs, "active", (y) => {
    render(y);
    NaplanYear.propagateToLinks(document.body);
  });
  render(year);
  NaplanYear.propagateToLinks(document.body);
  wireMoreDetails();
  wireFaq();
})();
