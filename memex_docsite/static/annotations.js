/* memex-docsite — first-party inline annotations.
   Implements W3C TextQuoteSelector + TextPositionSelector anchoring in
   ~250 lines of vanilla JS. No external libs, no bundler.
   Backed by /api/annotations/<page-slug>. */

const config = window.MEMEX_ANNOTATIONS_CONFIG || {};
const root = document.querySelector("[data-annotation-root]");
const sidebarEl = document.getElementById("annotation-sidebar");
const sidebarBody = document.getElementById("annotation-sidebar-body");
const sidebarClose = document.getElementById("annotation-sidebar-close");
const newButton = document.getElementById("annotation-new-button");
const pageSlug = config.pageSlug;
const writeEnabled = config.writeEnabled === true && config.staticMode !== true;
const authMode = config.authMode || "none";
const PREFIX_WIDTH = 32;

if (root && pageSlug) {
  bootstrap();
}

async function bootstrap() {
  injectFloatingButton();
  hookSelectionListener();
  if (sidebarClose) sidebarClose.addEventListener("click", closeSidebar);
  if (newButton) newButton.addEventListener("click", () => beginAnnotation(captureSelection() || null));
  await renderAllAnnotations();
}

// ─── DOM ↔ text-offset helpers ──────────────────────────────────────────────

function plainText(node) {
  // Walk text nodes, return the plain string. Mirrors window.getSelection's view.
  return node.textContent || "";
}

function textOffsetOf(rootNode, target, targetOffset) {
  /* Convert a (textNode, offsetWithinNode) pair into a character offset
     into rootNode.textContent. Returns -1 if `target` isn't a descendant. */
  const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_TEXT);
  let chars = 0;
  let node = walker.nextNode();
  while (node) {
    if (node === target) return chars + targetOffset;
    chars += node.nodeValue.length;
    node = walker.nextNode();
  }
  return -1;
}

function rangeFromOffsets(rootNode, start, end) {
  const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_TEXT);
  let chars = 0;
  let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
  let node = walker.nextNode();
  while (node) {
    const len = node.nodeValue.length;
    if (!startNode && chars + len >= start) {
      startNode = node;
      startOffset = start - chars;
    }
    if (chars + len >= end) {
      endNode = node;
      endOffset = end - chars;
      break;
    }
    chars += len;
    node = walker.nextNode();
  }
  if (!startNode || !endNode) return null;
  const range = document.createRange();
  range.setStart(startNode, startOffset);
  range.setEnd(endNode, endOffset);
  return range;
}

// ─── selectors (serialise / deserialise) ────────────────────────────────────

function selectorFromRange(range) {
  const text = plainText(root);
  const start = textOffsetOf(root, range.startContainer, range.startOffset);
  const end = textOffsetOf(root, range.endContainer, range.endOffset);
  if (start < 0 || end < start) return null;
  const exact = text.slice(start, end);
  if (!exact.trim()) return null;
  const prefix = text.slice(Math.max(0, start - PREFIX_WIDTH), start);
  const suffix = text.slice(end, Math.min(text.length, end + PREFIX_WIDTH));
  return {
    selector: { type: "TextQuoteSelector", exact, prefix, suffix },
    position: { type: "TextPositionSelector", start, end },
  };
}

function rangeFromSelectors(selector, position) {
  const text = plainText(root);
  // 1. Try the position selector first — exact and cheap.
  if (position && Number.isInteger(position.start) && Number.isInteger(position.end)) {
    const candidate = text.slice(position.start, position.end);
    if (candidate === selector.exact) {
      return rangeFromOffsets(root, position.start, position.end);
    }
  }
  // 2. Fall back to the quote+prefix+suffix scan.
  const matches = findAllOccurrences(text, selector.exact);
  if (matches.length === 0) return null;
  let bestStart = matches[0];
  if (matches.length > 1) {
    let bestScore = -1;
    for (const candidate of matches) {
      const score = scoreContext(text, candidate, selector);
      if (score > bestScore) {
        bestScore = score;
        bestStart = candidate;
      }
    }
  }
  return rangeFromOffsets(root, bestStart, bestStart + selector.exact.length);
}

function findAllOccurrences(haystack, needle) {
  if (!needle) return [];
  const out = [];
  let from = 0;
  while (true) {
    const idx = haystack.indexOf(needle, from);
    if (idx === -1) break;
    out.push(idx);
    from = idx + 1;
  }
  return out;
}

function scoreContext(text, position, selector) {
  /* Reward overlap between the live page's prefix/suffix and the
     selector's stored prefix/suffix. Crude but effective for survival
     across small edits. */
  const prefix = selector.prefix || "";
  const suffix = selector.suffix || "";
  const livePrefix = text.slice(Math.max(0, position - prefix.length), position);
  const liveSuffix = text.slice(position + selector.exact.length, position + selector.exact.length + suffix.length);
  return commonSuffixLen(prefix, livePrefix) + commonPrefixLen(suffix, liveSuffix);
}

function commonSuffixLen(a, b) {
  let n = 0;
  while (n < a.length && n < b.length && a[a.length - 1 - n] === b[b.length - 1 - n]) n++;
  return n;
}
function commonPrefixLen(a, b) {
  let n = 0;
  while (n < a.length && n < b.length && a[n] === b[n]) n++;
  return n;
}

// ─── highlight rendering ────────────────────────────────────────────────────

function paintHighlight(range, ann) {
  if (range.collapsed) return;
  // surroundContents fails on partial-element ranges; split into rects ourselves.
  const mark = document.createElement("mark");
  mark.className = "memex-annotation";
  mark.dataset.annotationId = ann.id;
  mark.title = (ann.body || "").split("\n", 1)[0].slice(0, 200);
  try {
    range.surroundContents(mark);
  } catch (err) {
    // Range crosses element boundaries — wrap each text node in the range.
    wrapRange(range, ann);
    return;
  }
  mark.addEventListener("click", (e) => { e.stopPropagation(); openSidebar(ann); });
}

function wrapRange(range, ann) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  const startContainer = range.startContainer;
  const endContainer = range.endContainer;
  let inside = false;
  while (node) {
    const next = walker.nextNode();  // fetch next before mutating
    if (node === startContainer) {
      inside = true;
      const start = node.splitText(range.startOffset);
      const tail = node === endContainer ? start.splitText(range.endOffset - range.startOffset) : null;
      wrapTextNode(start, ann);
      if (node === endContainer) inside = false;
    } else if (node === endContainer) {
      const tail = node.splitText(range.endOffset);
      wrapTextNode(node, ann);
      inside = false;
    } else if (inside && node.nodeValue.trim()) {
      wrapTextNode(node, ann);
    }
    node = next;
    if (!inside) break;
  }
}

function wrapTextNode(textNode, ann) {
  const mark = document.createElement("mark");
  mark.className = "memex-annotation";
  mark.dataset.annotationId = ann.id;
  textNode.parentNode.insertBefore(mark, textNode);
  mark.appendChild(textNode);
  mark.addEventListener("click", (e) => { e.stopPropagation(); openSidebar(ann); });
}

// ─── sidebar / form ─────────────────────────────────────────────────────────

let pendingSelection = null;
let annotationsCache = [];

function openSidebar(ann) {
  if (!sidebarEl || !sidebarBody) return;
  sidebarEl.classList.add("open");
  sidebarBody.innerHTML = "";
  const repliesTo = ann.id;
  appendAnnotationCard(sidebarBody, ann);
  const replies = annotationsCache.filter((a) => a.replies_to === ann.id);
  for (const reply of replies) appendAnnotationCard(sidebarBody, reply, { isReply: true });
  if (writeEnabled) appendReplyForm(sidebarBody, repliesTo);
}

function closeSidebar() {
  if (sidebarEl) sidebarEl.classList.remove("open");
  pendingSelection = null;
  hideFloatingButton();
}

function appendAnnotationCard(parent, ann, opts = {}) {
  const card = document.createElement("article");
  card.className = "memex-annotation-card" + (opts.isReply ? " memex-reply" : "");
  card.innerHTML = `
    <header>
      <strong>${escapeHtml(ann.author || "anonymous")}</strong>
      <time>${ann.created || ""}</time>
      <span class="visibility">${escapeHtml(ann.visibility || "public")}</span>
    </header>
    <blockquote>${escapeHtml((ann.selector || {}).exact || "")}</blockquote>
    <p class="body">${escapeHtml(ann.body || "")}</p>
  `;
  parent.appendChild(card);
}

function appendReplyForm(parent, replies_to) {
  const form = document.createElement("form");
  form.className = "memex-annotation-reply-form";
  form.innerHTML = `
    <textarea name="body" rows="3" placeholder="Reply…"></textarea>
    <div class="form-actions"><button type="submit">Reply</button></div>
  `;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = form.querySelector("textarea").value.trim();
    if (!body) return;
    const parentAnn = annotationsCache.find((a) => a.id === replies_to);
    if (!parentAnn) return;
    await postAnnotation({
      body,
      selector: parentAnn.selector,
      position: parentAnn.position,
      replies_to,
      visibility: parentAnn.visibility,
    });
  });
  parent.appendChild(form);
}

function appendNewForm(parent, captured) {
  const form = document.createElement("form");
  form.className = "memex-annotation-new-form";
  form.innerHTML = `
    <header>
      <strong>New annotation</strong>
      <blockquote>${escapeHtml((captured.selector || {}).exact || "")}</blockquote>
    </header>
    <textarea name="body" rows="4" placeholder="Your note (markdown supported)…" required></textarea>
    <label class="visibility-row">
      <span>Visibility</span>
      <select name="visibility">
        <option value="public">Public</option>
        <option value="group">Group (authenticated only)</option>
        <option value="private">Private (only me)</option>
      </select>
    </label>
    <div class="form-actions">
      <button type="submit">Post</button>
      <button type="button" class="cancel">Cancel</button>
    </div>
  `;
  form.querySelector(".cancel").addEventListener("click", closeSidebar);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = form.querySelector("textarea").value.trim();
    if (!body) return;
    await postAnnotation({
      body,
      selector: captured.selector,
      position: captured.position,
      visibility: form.querySelector("select").value,
    });
  });
  parent.appendChild(form);
}

function beginAnnotation(captured) {
  if (!captured) {
    flashStatus("Select some text on the page first.");
    return;
  }
  if (!sidebarEl) return;
  sidebarEl.classList.add("open");
  sidebarBody.innerHTML = "";
  appendNewForm(sidebarBody, captured);
}

// ─── selection toolbar ─────────────────────────────────────────────────────

let floatingButton = null;
function injectFloatingButton() {
  if (!writeEnabled) return;
  floatingButton = document.createElement("button");
  floatingButton.id = "memex-annotate-button";
  floatingButton.type = "button";
  floatingButton.textContent = "📝 Annotate";
  floatingButton.style.display = "none";
  document.body.appendChild(floatingButton);
  floatingButton.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const captured = captureSelection();
    if (captured) beginAnnotation(captured);
    hideFloatingButton();
  });
}

function captureSelection() {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return null;
  const range = sel.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return null;
  return selectorFromRange(range);
}

function hookSelectionListener() {
  if (!writeEnabled) return;
  document.addEventListener("mouseup", (e) => {
    setTimeout(showButtonIfSelection, 0);
  });
  document.addEventListener("selectionchange", () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) hideFloatingButton();
  });
}

function showButtonIfSelection() {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) {
    hideFloatingButton();
    return;
  }
  const range = sel.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) {
    hideFloatingButton();
    return;
  }
  const rect = range.getBoundingClientRect();
  if (!floatingButton) return;
  floatingButton.style.display = "inline-block";
  floatingButton.style.top = `${window.scrollY + rect.top - 36}px`;
  floatingButton.style.left = `${window.scrollX + rect.right - 90}px`;
}

function hideFloatingButton() {
  if (floatingButton) floatingButton.style.display = "none";
}

// ─── network ───────────────────────────────────────────────────────────────

async function fetchAnnotations() {
  const r = await fetch(`/api/annotations/${pageSlug}`);
  if (!r.ok) return [];
  return r.json();
}

async function postAnnotation(payload) {
  const headers = { "Content-Type": "application/json" };
  const token = readToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(`/api/annotations/${pageSlug}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    flashStatus(`Failed: ${err.error || r.statusText}`);
    return;
  }
  await renderAllAnnotations();
  closeSidebar();
}

function readToken() {
  if (authMode !== "token") return null;
  return localStorage.getItem("memex_token") || prompt("Enter your memex token:");
}

// ─── orchestration ─────────────────────────────────────────────────────────

async function renderAllAnnotations() {
  // Wipe any existing highlights, then re-render.
  for (const mark of root.querySelectorAll("mark.memex-annotation")) {
    mark.replaceWith(...mark.childNodes);
  }
  root.normalize();
  annotationsCache = await fetchAnnotations();
  const topLevel = annotationsCache.filter((a) => !a.replies_to && a.status !== "deleted");
  for (const ann of topLevel) {
    if (!ann.selector) continue;
    const range = rangeFromSelectors(ann.selector, ann.position);
    if (range) paintHighlight(range, ann);
  }
}

// ─── utils ─────────────────────────────────────────────────────────────────

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

let statusEl = null;
function flashStatus(msg) {
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.className = "memex-annotation-status";
    document.body.appendChild(statusEl);
  }
  statusEl.textContent = msg;
  statusEl.style.opacity = "1";
  clearTimeout(statusEl._fade);
  statusEl._fade = setTimeout(() => { statusEl.style.opacity = "0"; }, 2400);
}
