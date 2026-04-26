/* memex-docsite — interactive 3D link graph (Obsidian-style).
 *
 * Renders the wiki link graph using `3d-force-graph` (UMD bundle, MIT,
 * by Vasco Asturiano). Three.js is bundled inside the 3d-force-graph
 * UMD so we don't need a separate script tag for it. A 2D toggle hands
 * off to `force-graph` (canvas-based, MIT, same author) for users who
 * want a flat layout or whose machine doesn't have WebGL.
 *
 * Both libraries are vendored under `static/vendor/` so the docsite
 * stays offline-friendly. See vendor/*.LICENSE for the full text.
 */

const summaryEl = document.getElementById("graph-summary");
const statsEl = document.getElementById("graph-stats");
const canvas = document.getElementById("graph");
const hideOrphansEl = document.getElementById("hide-orphans");
const refreshEl = document.getElementById("refresh-graph");
const exportEl = document.getElementById("export-graph-json");
const use2DEl = document.getElementById("use-2d");

const NODE_SIZE = 6;
const LINK_DISTANCE = 60;
const showLabelsEl = document.getElementById("show-labels");
const statsToggleBtn = document.getElementById("graph-stats-toggle");
const statsCloseBtn = document.getElementById("graph-stats-close");
const statsSheet = document.getElementById("graph-stats-sheet");
const statsBackdrop = document.getElementById("graph-stats-backdrop");

let currentGraph = null;
let instance = null;
let mode = "3d"; // "3d" | "2d"
let alwaysShowLabels = false;

function readCssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function clearCanvas() {
  if (instance && typeof instance._destructor === "function") {
    try { instance._destructor(); } catch (_e) { /* ignore */ }
  }
  canvas.innerHTML = "";
  instance = null;
}

// 3d-force-graph and force-graph both read parent size at init and don't
// auto-resize. We use a ResizeObserver to push width/height updates to the
// instance whenever the container's box changes (window resize, sidebar
// toggle, devtools open, etc.). One observer is enough — re-attached per
// instance because clearCanvas() destroys the old one.
let canvasResizeObserver = null;
function observeCanvasResize() {
  if (canvasResizeObserver) {
    canvasResizeObserver.disconnect();
    canvasResizeObserver = null;
  }
  if (!instance || typeof ResizeObserver !== "function") return;
  canvasResizeObserver = new ResizeObserver(() => {
    if (!instance) return;
    if (typeof instance.width === "function") instance.width(canvas.clientWidth);
    if (typeof instance.height === "function") instance.height(canvas.clientHeight);
  });
  canvasResizeObserver.observe(canvas);
}

function applyTheme() {
  if (!instance) return;
  const bg = readCssVar("--bg", "#fafafa");
  if (typeof instance.backgroundColor === "function") {
    instance.backgroundColor(bg);
  }
}

function shapeData(graph, { hideOrphans }) {
  const orphans = new Set(graph.summary?.orphans || []);
  const visible = new Set();
  const nodes = [];
  for (const n of graph.nodes) {
    if (hideOrphans && orphans.has(n.slug)) continue;
    visible.add(n.slug);
    nodes.push({ id: n.slug, name: n.title || n.slug, group: n.type || "untyped" });
  }
  const links = [];
  for (const e of graph.edges) {
    if (!visible.has(e.source) || !visible.has(e.target)) continue;
    links.push({ source: e.source, target: e.target });
  }
  return { nodes, links };
}

function navigateToNode(node) {
  if (!node || !node.id) return;
  const slug = node.id;
  window.location.href = "/" + (slug === "index" ? "" : slug);
}

function build3D(data) {
  if (typeof window.ForceGraph3D !== "function") {
    canvas.innerHTML = `<p class="empty">3D graph library failed to load. Try the 2D fallback or check the browser console.</p>`;
    return;
  }
  instance = window.ForceGraph3D()(canvas)
    .width(canvas.clientWidth)
    .height(canvas.clientHeight)
    .graphData(data)
    .nodeLabel((n) => n.name)
    .nodeAutoColorBy("group")
    .nodeRelSize(NODE_SIZE)
    .linkOpacity(0.4)
    .linkDirectionalArrowLength(2)
    .linkDirectionalArrowRelPos(0.85)
    .onNodeClick(navigateToNode)
    .enableNodeDrag(true)
    .cooldownTicks(120);
  if (instance.d3Force) {
    const linkF = instance.d3Force("link");
    if (linkF && typeof linkF.distance === "function") {
      linkF.distance(LINK_DISTANCE);
    }
  }
  if (typeof instance.onEngineStop === "function") {
    instance.onEngineStop(() => {
      if (instance && typeof instance.zoomToFit === "function") {
        instance.zoomToFit(400);
      }
    });
  }
  observeCanvasResize();
  applyNodeLabelMode();
  applyTheme();
}

// Always-show-labels: 3d-force-graph defaults to hover-only. We attach text
// to each node via the native CanvasObject API. For 2D mode we set the node
// canvas paint; for 3D, the helper falls back to nothing (a sprite renderer
// would need three-spritetext, which isn't vendored).
function applyNodeLabelMode() {
  if (!instance) return;
  if (mode === "2d" && typeof instance.nodeCanvasObject === "function") {
    if (alwaysShowLabels) {
      instance.nodeCanvasObject((node, ctx, globalScale) => {
        const fontSize = 12 / Math.max(globalScale, 0.5);
        const r = NODE_SIZE;
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
        ctx.fillStyle = node.color || "#888";
        ctx.fill();
        if (globalScale > 0.6) {
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillStyle = readCssVar("--fg", "#222");
          ctx.fillText(" " + node.name, node.x + r, node.y);
        }
      });
      instance.nodePointerAreaPaint((node, color, ctx) => {
        ctx.fillStyle = color;
        const r = NODE_SIZE + 4;
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
        ctx.fill();
      });
    } else {
      instance.nodeCanvasObject(null);
      instance.nodePointerAreaPaint(null);
    }
  }
  // 3D always-labels needs three-spritetext (not vendored). Hover label
  // remains the working affordance in 3D mode; the toggle is a no-op there.
}

function build2D(data) {
  if (typeof window.ForceGraph !== "function") {
    canvas.innerHTML = `<p class="empty">2D graph library failed to load.</p>`;
    return;
  }
  instance = window.ForceGraph()(canvas)
    .width(canvas.clientWidth)
    .height(canvas.clientHeight)
    .graphData(data)
    .nodeLabel((n) => n.name)
    .nodeAutoColorBy("group")
    .nodeRelSize(NODE_SIZE)
    .linkColor(() => readCssVar("--border", "#cbd5e1"))
    .linkDirectionalArrowLength(3)
    .linkDirectionalArrowRelPos(0.85)
    .enableNodeDrag(true)
    .enableZoomInteraction(true)
    .enablePanInteraction(true)
    .onNodeClick(navigateToNode);
  if (instance.d3Force) {
    const linkF = instance.d3Force("link");
    if (linkF && typeof linkF.distance === "function") {
      linkF.distance(LINK_DISTANCE);
    }
  }
  observeCanvasResize();
  applyNodeLabelMode();
}


function renderStats(graph) {
  const sect = (title, items) => {
    if (!items || !items.length) return "";
    return `<h3>${title} (${items.length})</h3><ul>${items
      .map((s) => `<li><a href="/${s === "index" ? "" : s}">${s}</a></li>`)
      .join("")}</ul>`;
  };
  if (!statsEl) return;
  statsEl.innerHTML =
    sect("Orphans (no inbound links)", graph.summary?.orphans || []) +
    sect("Hubs (≥5 inbound)", graph.summary?.hubs || []) +
    sect("Dead ends (no outbound links)", graph.summary?.dead_ends || []);
}

async function render() {
  if (summaryEl) summaryEl.textContent = "Fetching graph…";
  let graph;
  try {
    graph = await fetch("/api/graph").then((r) => r.json());
  } catch (err) {
    if (summaryEl) summaryEl.textContent = "Failed to fetch graph.";
    console.error(err);
    return;
  }
  currentGraph = graph;
  if (summaryEl) {
    summaryEl.textContent =
      `${graph.summary.node_count} pages, ${graph.summary.edge_count} edges` +
      (mode === "3d" ? " · 3D view (drag to rotate, scroll to zoom)." : " · 2D view.");
  }
  renderStats(graph);

  if (graph.summary.node_count === 0) {
    canvas.textContent = "No pages found.";
    return;
  }

  if (exportEl) {
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: "application/json" });
    exportEl.href = URL.createObjectURL(blob);
  }

  const data = shapeData(graph, { hideOrphans: hideOrphansEl?.checked });
  clearCanvas();
  if (mode === "2d") {
    build2D(data);
  } else {
    build3D(data);
  }
}

if (hideOrphansEl) hideOrphansEl.addEventListener("change", render);
if (refreshEl) refreshEl.addEventListener("click", render);
if (use2DEl) {
  use2DEl.addEventListener("change", () => {
    mode = use2DEl.checked ? "2d" : "3d";
    render();
  });
}
if (showLabelsEl) {
  showLabelsEl.addEventListener("change", () => {
    alwaysShowLabels = showLabelsEl.checked;
    applyNodeLabelMode();
    if (instance && typeof instance.refresh === "function") instance.refresh();
  });
}
// ─── Stats sheet toggle ────────────────────────────────────────────────────

function setStatsOpen(open) {
  if (!statsSheet || !statsBackdrop) return;
  statsSheet.classList.toggle("is-open", open);
  statsBackdrop.classList.toggle("is-open", open);
  statsSheet.setAttribute("aria-hidden", open ? "false" : "true");
  statsBackdrop.setAttribute("aria-hidden", open ? "false" : "true");
  if (statsToggleBtn) {
    statsToggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
    statsToggleBtn.classList.toggle("is-active", open);
  }
}

if (statsToggleBtn) {
  statsToggleBtn.addEventListener("click", () => {
    setStatsOpen(!statsSheet?.classList.contains("is-open"));
  });
}
if (statsCloseBtn) statsCloseBtn.addEventListener("click", () => setStatsOpen(false));
if (statsBackdrop) statsBackdrop.addEventListener("click", () => setStatsOpen(false));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && statsSheet?.classList.contains("is-open")) {
    setStatsOpen(false);
  }
});
// Re-apply theme background when the user toggles light/dark via base.css.
const themeObserver = new MutationObserver(applyTheme);
themeObserver.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["data-theme"],
});

render();
