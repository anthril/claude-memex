/* Render the wiki link graph using the locally vendored Mermaid bundle.
   Mermaid is loaded via a <script> tag in graph.html, so it lives on
   window.mermaid by the time this module runs. No CDN, no network. */

const summaryEl = document.getElementById("graph-summary");
const statsEl = document.getElementById("graph-stats");
const canvas = document.getElementById("graph");
const hideOrphansEl = document.getElementById("hide-orphans");
const refreshEl = document.getElementById("refresh-graph");
const exportEl = document.getElementById("export-mermaid");

let mermaidReady = false;
function ensureMermaid() {
  if (mermaidReady || !window.mermaid) return mermaidReady;
  window.mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
  mermaidReady = true;
  return true;
}

function safeId(slug) {
  return slug.replace(/[^a-zA-Z0-9]/g, "_") || "n";
}

function buildMermaid(graph, { hideOrphans }) {
  const lines = ["graph LR"];
  const orphans = new Set(graph.summary.orphans);
  const visible = new Set();
  for (const n of graph.nodes) {
    if (hideOrphans && orphans.has(n.slug)) continue;
    visible.add(n.slug);
    const label = (n.title || n.slug).replace(/"/g, "'");
    lines.push(`  ${safeId(n.slug)}["${label}"]`);
  }
  for (const e of graph.edges) {
    if (!visible.has(e.source) || !visible.has(e.target)) continue;
    lines.push(`  ${safeId(e.source)} --> ${safeId(e.target)}`);
  }
  return lines.join("\n");
}

function renderStats(graph) {
  const sect = (title, items) => {
    if (!items.length) return "";
    return `<h3>${title} (${items.length})</h3><ul>${items
      .map((s) => `<li><a href="/${s === "index" ? "" : s}">${s}</a></li>`)
      .join("")}</ul>`;
  };
  statsEl.innerHTML =
    sect("Orphans (no inbound links)", graph.summary.orphans) +
    sect("Hubs (≥5 inbound)", graph.summary.hubs) +
    sect("Dead ends (no outbound links)", graph.summary.dead_ends);
}

async function render() {
  summaryEl.textContent = "Fetching graph…";
  const graph = await fetch("/api/graph").then((r) => r.json());
  summaryEl.textContent = `${graph.summary.node_count} pages, ${graph.summary.edge_count} edges.`;
  renderStats(graph);

  const text = buildMermaid(graph, { hideOrphans: hideOrphansEl.checked });
  if (graph.summary.node_count === 0) {
    canvas.textContent = "No pages found.";
    return;
  }

  const blob = new Blob([text], { type: "text/plain" });
  exportEl.href = URL.createObjectURL(blob);

  if (!ensureMermaid()) {
    canvas.innerHTML = `<pre class="graph-fallback">${text}</pre>`;
    return;
  }
  try {
    const id = "memex-graph-" + Date.now();
    const { svg } = await window.mermaid.render(id, text);
    canvas.innerHTML = svg;
  } catch (err) {
    canvas.innerHTML = `<pre class="graph-fallback">${text}</pre>`;
    console.error("Mermaid render failed", err);
  }
}

hideOrphansEl.addEventListener("change", render);
refreshEl.addEventListener("click", render);
render();
