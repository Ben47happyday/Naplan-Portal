// Shared micro-interactions: soft page transitions + scroll-triggered reveals.
// Include on every page, after the DOM content it should animate.
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Smooth outgoing transition before internal navigations.
  if (!reduceMotion) {
    document.addEventListener("click", (e) => {
      const link = e.target.closest("a[href]");
      if (!link) return;
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("http") || href.startsWith("mailto:")) return;
      if (link.target === "_blank" || e.metaKey || e.ctrlKey || e.shiftKey) return;

      e.preventDefault();
      document.body.classList.add("page-leaving");
      setTimeout(() => { window.location.href = href; }, 160);
    });
  }

  // Scroll-triggered reveal: any element with .reveal fades/rises into view.
  function initReveal() {
    const targets = document.querySelectorAll(".reveal");
    if (!targets.length) return;

    if (reduceMotion || !("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("in-view"));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });

    targets.forEach((el) => observer.observe(el));
  }

  // Auto-tag common repeating content blocks so every page gets reveal
  // animation without needing to hand-edit markup everywhere.
  function autoTagReveal() {
    const selectors = [
      ".pillar-card", ".info-card", ".year-card", ".question-card",
      ".diagnostic-banner", ".page-section > h1", ".page-section > .lede",
    ];
    document.querySelectorAll(selectors.join(",")).forEach((el, i) => {
      if (el.classList.contains("reveal")) return;
      el.classList.add("reveal");
      el.style.transitionDelay = `${Math.min(i % 6, 5) * 60}ms`;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ready);
  } else {
    ready();
  }

  function ready() {
    autoTagReveal();
    initReveal();
  }

  // Re-run for content injected later by page-specific scripts (fetch results).
  window.NaplanFx = { initReveal, autoTagReveal };
})();
