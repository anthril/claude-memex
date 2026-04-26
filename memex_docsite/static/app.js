/* memex-docsite global UI bootstrap.
   Phase 1: theme toggle + system-theme detection. Future phases will
   import their modules from /static/<feature>.js (search, graph, annotations). */

const root = document.documentElement;
const STORAGE_KEY = "memex-docsite-theme";

function applyTheme(theme) {
  root.dataset.theme = theme;
  if (theme === "auto") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.themeApplied = prefersDark ? "dark" : "light";
  } else {
    root.dataset.themeApplied = theme;
  }
}

const stored = localStorage.getItem(STORAGE_KEY);
applyTheme(stored || root.dataset.theme || "auto");

const button = document.getElementById("theme-toggle");
if (button) {
  button.addEventListener("click", () => {
    const order = ["auto", "light", "dark"];
    const current = localStorage.getItem(STORAGE_KEY) || root.dataset.theme || "auto";
    const next = order[(order.indexOf(current) + 1) % order.length];
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
    button.title = `Theme: ${next}`;
  });
}

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if ((localStorage.getItem(STORAGE_KEY) || "auto") === "auto") applyTheme("auto");
});

// Mobile sidebar toggle.
const shell = document.querySelector(".site-shell");
const sidebarToggle = document.getElementById("sidebar-toggle");
if (shell && sidebarToggle) {
  sidebarToggle.addEventListener("click", () => {
    const open = shell.classList.toggle("sidebar-open");
    sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });
  // Tap outside the sidebar to close.
  document.addEventListener("click", (e) => {
    if (!shell.classList.contains("sidebar-open")) return;
    const inside = e.target.closest(".sidebar, #sidebar-toggle");
    if (!inside) {
      shell.classList.remove("sidebar-open");
      sidebarToggle.setAttribute("aria-expanded", "false");
    }
  });
}

// TOC scroll-spy: highlight the heading currently in view.
const tocLinks = document.querySelectorAll(".toc a[href^='#']");
if (tocLinks.length > 0 && "IntersectionObserver" in window) {
  const linksByHash = new Map();
  for (const a of tocLinks) {
    linksByHash.set(decodeURIComponent(a.getAttribute("href")).slice(1), a);
  }
  const headings = Array.from(linksByHash.keys())
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  let activeId = null;
  function setActive(id) {
    if (id === activeId) return;
    if (activeId) linksByHash.get(activeId)?.classList.remove("active");
    activeId = id;
    if (activeId) linksByHash.get(activeId)?.classList.add("active");
  }

  // Track the most-recently entered heading. The fallback below the IO
  // handles edge cases where no heading is currently intersecting (e.g.,
  // the user scrolled past the last heading).
  const visibility = new Map();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        visibility.set(entry.target.id, entry.intersectionRatio);
      }
      // Pick the topmost heading with non-zero intersection. If none is
      // visible, fall back to the last heading whose top is above the
      // viewport — i.e., the section the user is currently reading.
      let chosen = null;
      let bestTop = -Infinity;
      for (const h of headings) {
        const rect = h.getBoundingClientRect();
        if (rect.top <= 100 && rect.top > bestTop) {
          bestTop = rect.top;
          chosen = h.id;
        }
      }
      if (!chosen) {
        for (const h of headings) {
          if ((visibility.get(h.id) || 0) > 0) { chosen = h.id; break; }
        }
      }
      if (chosen) setActive(chosen);
    },
    { rootMargin: "-72px 0px -60% 0px", threshold: [0, 0.25, 0.5, 1] },
  );
  for (const h of headings) observer.observe(h);
}

// `/` focuses the search input. Skip if the user is already typing somewhere.
document.addEventListener("keydown", (e) => {
  if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
  const t = e.target;
  if (
    t instanceof HTMLInputElement ||
    t instanceof HTMLTextAreaElement ||
    (t instanceof HTMLElement && t.isContentEditable)
  ) return;
  const search = document.getElementById("site-search-input");
  if (search) {
    e.preventDefault();
    search.focus();
    search.select();
  }
});
