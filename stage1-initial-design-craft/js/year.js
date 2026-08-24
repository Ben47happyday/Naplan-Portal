// Shared year-level selection, persisted across pages via localStorage + URL.
const NaplanYear = (function () {
  const STORAGE_KEY = "naplanYear";
  const VALID_YEARS = [3, 5, 7, 9];

  function get() {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = parseInt(params.get("year"), 10);
    if (VALID_YEARS.includes(fromUrl)) return fromUrl;

    const fromStorage = parseInt(localStorage.getItem(STORAGE_KEY), 10);
    if (VALID_YEARS.includes(fromStorage)) return fromStorage;

    return 5;
  }

  function set(year) {
    if (!VALID_YEARS.includes(year)) return;
    localStorage.setItem(STORAGE_KEY, String(year));
  }

  // Wires up a set of elements with [data-year] attributes as a picker:
  // clicking one selects it (adds `selectedClass`), persists the choice,
  // and calls onChange(year) if provided.
  function wirePicker(elements, selectedClass, onChange) {
    const current = get();
    elements.forEach((el) => {
      const y = parseInt(el.dataset.year, 10);
      el.classList.toggle(selectedClass, y === current);
      el.addEventListener("click", () => {
        set(y);
        elements.forEach((e) => e.classList.remove(selectedClass));
        el.classList.add(selectedClass);
        if (onChange) onChange(y);
      });
    });
    return current;
  }

  // Appends ?year=<selected> to same-site links inside `container` so the
  // choice carries through when navigating to another page.
  function propagateToLinks(container) {
    const year = get();
    container.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("http")) return;
      const url = new URL(href, window.location.href);
      url.searchParams.set("year", year);
      a.setAttribute("href", url.pathname + url.search);
    });
  }

  return { get, set, wirePicker, propagateToLinks, VALID_YEARS };
})();
