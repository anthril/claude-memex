/* memex-docsite — page-level comment threads.
   Fetches comments for the current page, renders threaded discussion,
   handles new-comment + reply submission. Storage and visibility are
   handled server-side. */

const config = window.MEMEX_COMMENTS_CONFIG || {};
const container = document.getElementById("memex-comments");
const pageSlug = config.pageSlug;
const writeEnabled = config.writeEnabled === true && config.staticMode !== true;
const authMode = config.authMode || "none";

if (container && pageSlug) {
  bootstrap();
}

async function bootstrap() {
  await render();
}

async function render() {
  container.innerHTML = "<p class='page-meta'>Loading comments…</p>";
  let records = [];
  try {
    const r = await fetch(`/api/comments/${pageSlug}`);
    if (r.ok) records = await r.json();
  } catch (err) {
    container.innerHTML = "<p class='empty'>Couldn't load comments.</p>";
    return;
  }

  container.innerHTML = "";
  const heading = document.createElement("h2");
  heading.textContent = `Comments (${records.filter((r) => r.status !== "deleted").length})`;
  container.appendChild(heading);

  const topLevel = records.filter((r) => !r.replies_to);
  if (topLevel.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No comments yet.";
    container.appendChild(empty);
  }
  for (const root of topLevel) {
    container.appendChild(renderThread(root, records));
  }

  if (writeEnabled) container.appendChild(buildNewCommentForm(null));
}

function renderThread(root, all) {
  const wrapper = document.createElement("div");
  wrapper.className = "memex-comment-thread";
  wrapper.appendChild(renderCard(root));
  const replies = all.filter((r) => r.replies_to === root.id);
  for (const reply of replies) {
    const replyEl = renderCard(reply, { isReply: true });
    wrapper.appendChild(replyEl);
  }
  if (writeEnabled) wrapper.appendChild(buildNewCommentForm(root.id));
  return wrapper;
}

function renderCard(rec, opts = {}) {
  const card = document.createElement("article");
  card.className = "memex-comment-card" + (opts.isReply ? " memex-comment-reply" : "");
  card.innerHTML = `
    <header>
      <strong>${escapeHtml(rec.author || "anonymous")}</strong>
      <time>${escapeHtml(rec.created || "")}</time>
      <span class="visibility">${escapeHtml(rec.visibility || "public")}</span>
      ${rec.status === "deleted" ? '<span class="badge badge-static">deleted</span>' : ""}
    </header>
    <p class="body">${escapeHtml(rec.body || "")}</p>
  `;
  return card;
}

function buildNewCommentForm(replyTo) {
  const form = document.createElement("form");
  form.className = replyTo ? "memex-comment-reply-form" : "memex-comment-new-form";
  const placeholder = replyTo ? "Reply…" : "Add a comment (markdown supported)";
  const visibilityRow = replyTo ? "" : `
    <label class="visibility-row">
      <span>Visibility</span>
      <select name="visibility">
        <option value="public">Public</option>
        <option value="group">Group (authenticated)</option>
        <option value="private">Private (only me)</option>
      </select>
    </label>
  `;
  form.innerHTML = `
    <textarea name="body" rows="${replyTo ? 2 : 4}" placeholder="${placeholder}" required></textarea>
    ${visibilityRow}
    <div class="form-actions">
      <button type="submit">${replyTo ? "Reply" : "Post"}</button>
    </div>
  `;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = form.querySelector("textarea").value.trim();
    if (!body) return;
    const visibility = form.querySelector("select")?.value || "public";
    const ok = await postComment({ body, visibility, replies_to: replyTo });
    if (ok) await render();
  });
  return form;
}

async function postComment(payload) {
  const headers = { "Content-Type": "application/json" };
  const token = readToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const r = await fetch(`/api/comments/${pageSlug}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      flashStatus(`Comment failed: ${err.error || r.statusText}`);
      return false;
    }
    return true;
  } catch (err) {
    flashStatus("Network error posting comment.");
    return false;
  }
}

function readToken() {
  if (authMode !== "token") return null;
  return localStorage.getItem("memex_token") || prompt("Enter your memex token:");
}

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
