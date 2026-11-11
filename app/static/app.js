"use strict";

// The five sample questions from the brief. `p` is the document family (colours the card), `tag` its topic.
const SAMPLES = [
  { q: "What is the recommended coolant concentration for the TX-200 CNC turning centre?", p: "MNT", tag: "Maintenance" },
  { q: "The machine is showing alarm AL-104. What does it mean and what should the operator do?", p: "MNT", tag: "Alarms" },
  { q: "Who is allowed to remove a lockout lock from a machine?", p: "SAF", tag: "Safety" },
  { q: "What is the outer diameter tolerance for the BH-220 bearing housing?", p: "QC", tag: "Quality" },
  { q: "How often should spindle runout be checked, and who does it?", p: "MNT", tag: "Maintenance" },
];

const ICON = {
  chat: '<svg viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  warn: '<svg viewBox="0 0 24 24"><path d="M12 3l10 18H2z M12 10v5 M12 18.2v.1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 11v6M12 7.5v.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  pdf: '<svg viewBox="0 0 24 24"><path d="M6 3h8l5 5v13H6z M14 3v5h5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M5 15V5a2 2 0 0 1 2-2h8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M16.5 16.5L21 21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  retry: '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  up: '<svg viewBox="0 0 24 24"><path d="M7 11v9H4v-9zM7 11l4-8c1.5 0 2.5 1 2.2 2.6L12.8 9H19a2 2 0 0 1 2 2.4l-1.3 6.5A2 2 0 0 1 17.8 20H7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  down: '<svg viewBox="0 0 24 24"><path d="M7 13V4H4v9zM7 13l4 8c1.5 0 2.5-1 2.2-2.6L12.8 15H19a2 2 0 0 0 2-2.4l-1.3-6.5A2 2 0 0 0 17.8 4H7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  spark: '<svg class="spark" viewBox="0 0 24 24"><path d="M12 2l2.2 6.8L21 11l-6.8 2.2L12 20l-2.2-6.8L3 11l6.8-2.2z" fill="currentColor"/><path d="M19 3l.8 2.2L22 6l-2.2.8L19 9l-.8-2.2L16 6l2.2-.8z" fill="currentColor"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="M19 12H5M11 6l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

const $ = (id) => document.getElementById(id);
const resultEl = $("result"), welcomeEl = $("welcome"), qEl = $("q"), askBtn = $("ask");
let timer = null, lastQuestion = "";

/* ---------- helpers ---------- */
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const prefixOf = (docNo) => String(docNo).split("-")[0];
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode: ignore */ } },
};
const STOP = new Set("a an and are as at be by can do does for from how i in is it of on or should the to what when where which who will with you your that this".split(" "));

// Same idea as the server's normaliser: "al305" -> "al-305". Used only to highlight the matching table row.
function questionTokens(q) {
  const n = q.toLowerCase().replace(/\b(al|bh|qf|sf|cnc)\s?-?\s?(\d{2,4}[a-z]?)\b/g, "$1-$2");
  const words = (n.match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) || []).filter((w) => !STOP.has(w) && w.length > 1);
  return { words, codes: words.filter((w) => /^[a-z]{1,4}-\d/.test(w)) };
}

function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); }

// Turn the model's plain text into paragraphs / numbered steps / bullets (escaped first, so it is safe).
function formatAnswer(text) {
  const lines = text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
  let html = "", list = null;
  const close = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const l of lines) {
    const num = l.match(/^\d+[.)]\s+(.*)/), bul = l.match(/^[-•*]\s+(.*)/);
    if (num) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${inline(num[1])}</li>`; }
    else if (bul) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${inline(bul[1])}</li>`; }
    else { close(); html += `<p>${inline(l)}</p>`; }
  }
  close();
  return html;
}

// Chunk text (plain lines + Markdown tables) -> safe HTML, with the best-matching table row highlighted.
function renderExcerpt(text, tok) {
  const lines = text.split("\n");
  let html = "", i = 0;
  while (i < lines.length) {
    if (lines[i].startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const body = rows.slice(2).map(cells);
      const score = body.map((r) => {
        const t = r.join(" ").toLowerCase();
        return tok.codes.some((c) => t.includes(c)) ? 99 : tok.words.filter((w) => t.includes(w)).length;
      });
      const best = Math.max(0, ...score);
      html += "<table><thead><tr>" + cells(rows[0]).map((c) => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody>";
      body.forEach((r, k) => {
        html += `<tr${best >= 2 && score[k] === best ? ' class="hl"' : ""}>` + r.map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>";
      });
      html += "</tbody></table>";
    } else { html += `<p>${esc(lines[i])}</p>`; i++; }
  }
  return html;
}

// Search-only mode (no LLM): still put the single best-matching table row or line right in the answer card.
function bestMatch(s, tok) {
  const lines = s.text.split("\n");
  const tableLines = lines.filter((l) => l.startsWith("|"));
  const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  if (tableLines.length > 2) {
    const head = cells(tableLines[0]);
    let best = null, bestScore = 0;
    tableLines.slice(2).forEach((r) => {
      const c = cells(r), t = c.join(" ").toLowerCase();
      const sc = tok.codes.some((x) => t.includes(x)) ? 99 : tok.words.filter((w) => t.includes(w)).length;
      if (sc > bestScore) { best = c; bestScore = sc; }
    });
    if (best && bestScore >= 2) return head.map((h, i) => [h, best[i] || ""]);
  }
  // Prose (procedures, rules) is never cut down to one line: that could drop an exception or a safety step.
  return [];
}

/* ---------- render ---------- */
function sourceCard(s, tok, open) {
  const sup = s.status === "superseded";
  const pages = s.page_range[0] === s.page_range[1] ? `p.${s.page_range[0]}` : `p.${s.page_range[0]}–${s.page_range[1]}`;
  return `
  <article class="card src ${sup ? "superseded" : ""}" id="src-${s.n}" data-p="${esc(prefixOf(s.doc_no))}">
    <div class="src-top">
      <span class="src-doc">${esc(s.doc_no)} · Rev ${esc(s.revision)}</span>
      <span class="badge ${sup ? "superseded" : "current"}">${sup ? "Superseded" : "Current"}</span>
      ${s.cited ? '<span class="badge used">Used in answer</span>' : ""}
    </div>
    <div class="src-ref">${esc(s.title)}<br>Section ${esc(s.section)} · ${pages} · effective ${esc(s.effective_date)}</div>
    ${sup ? `<div class="banner superseded">${ICON.warn}<div>Superseded revision. Do not use it for current work.</div></div>` : ""}
    <details class="excerpt-wrap" ${open ? "open" : ""}>
      <summary>Exact text from the document</summary>
      <div class="excerpt">${renderExcerpt(s.text, tok)}</div>
    </details>
    <div class="actions"><a class="btn ghost" href="${esc(s.pdf_url)}" target="_blank" rel="noopener">${ICON.pdf}Open PDF at page ${s.page}</a></div>
  </article>`;
}

function questionHeader(q) {
  return `<div class="card-head"><h2>Your question</h2><button class="btn ghost" type="button" id="back">${ICON.back}New question</button></div>
          <p class="question">${esc(q)}</p>`;
}

// Two columns on wide screens (answer | evidence); they stack on phones.
const grid = (left, right = "") =>
  `<div class="result-grid ${right ? "" : "single"}"><div class="col-main">${left}</div>${right ? `<div class="col-src">${right}</div>` : ""}</div>`;

function render(r) {
  const tok = questionTokens(r.question);
  let html = `<div class="card">${questionHeader(r.question)}</div>`;

  if (r.mode === "not_found") {
    html += `<div class="card notfound"><div class="nf-icon">${ICON.search}</div>
      <h3>Not found in the plant documents</h3>
      <p>I couldn't find this in the SOPs and manuals I have, so I won't guess.</p>
      ${r.notice ? `<p><strong>${esc(r.notice)}</strong></p>` : ""}`;
    if (r.closest.length) {
      html += `<p class="meta">Closest documents (they may not answer this):</p><div class="actions">` +
        r.closest.map((c) => `<a class="btn ghost" href="${esc(c.pdf_url)}" target="_blank" rel="noopener">${ICON.pdf}${esc(c.doc_no)} Rev ${esc(c.revision)}</a>`).join("") + "</div>";
    }
    html += `<p class="meta">${r.latency_ms} ms</p></div>`;
    return grid(html);
  }

  html += `<div class="card"><div class="card-head"><h2>Answer</h2></div>`;
  if (r.safety_flag) html += `<div class="banner safety">${ICON.warn}<div>Safety-critical. Confirm against the SOP page below before you act.</div></div>`;
  if (r.mode === "retrieval_only") {
    const top = r.sources.find((s) => s.cited) || r.sources[0];
    const pairs = top ? bestMatch(top, tok) : [];
    if (pairs.length) {
      html += `<div class="match"><div class="match-label">Best match · ${esc(top.doc_no)} Rev ${esc(top.revision)}, section ${esc(top.section.split(".")[0])}, p.${top.page}</div><dl>` +
        pairs.map(([k, v]) => (k ? `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>` : `<dd class="wide">${esc(v)}</dd>`)).join("") + "</dl></div>";
    }
    html += `<div class="banner info">${ICON.info}<div>${esc(r.notice)}</div></div>`;
  } else html += `<div class="answer" id="answer-text">${formatAnswer(r.answer)}</div>`;
  (r.revision_notes || []).forEach((n) => { html += `<div class="banner info">${ICON.info}<div>${esc(n)}</div></div>`; });

  const cited = r.sources.filter((s) => s.cited);
  if (cited.length) {
    html += `<div class="cites"><span class="lbl">Sources</span>` + cited.map((s) =>
      `<a class="cite ${s.status === "superseded" ? "sup" : ""}" href="#src-${s.n}" data-src="${s.n}"><i></i>${esc(s.doc_no)} Rev ${esc(s.revision)} · §${esc(s.section.split(".")[0])} · p.${s.page}</a>`).join("") + "</div>";
  }
  html += `<div class="ans-actions" data-trace="${esc(r.trace_id)}">
      ${r.mode === "llm" ? `<button class="act" type="button" id="copy">${ICON.copy}<span>Copy</span></button>` : ""}
      <button class="act" type="button" data-fb="1" aria-label="This answer was helpful">${ICON.up}<span>Helpful</span></button>
      <button class="act" type="button" data-fb="0" aria-label="This answer was not helpful">${ICON.down}<span>Not helpful</span></button>
      <span class="thanks" id="thanks"></span><span class="ms">${r.latency_ms} ms</span></div></div>`;

  const used = r.sources.filter((s) => s.cited), other = r.sources.filter((s) => !s.cited);
  let evidence = `<h3 class="sec-title">Source</h3>` + used.map((s, i) => sourceCard(s, tok, i === 0)).join("");
  if (other.length) {
    evidence += `<details class="others"><summary>Other matching sections (${other.length})</summary>${other.map((s) => sourceCard(s, tok, false)).join("")}</details>`;
  }
  return grid(html, evidence);
}

function show(html) {
  welcomeEl.hidden = true;
  resultEl.innerHTML = html;
  window.scrollTo({ top: 0, behavior: "smooth" });
  const back = $("back"); if (back) back.onclick = reset;
  const copy = $("copy");
  if (copy) copy.onclick = async () => {
    const text = $("answer-text").innerText;
    try { await navigator.clipboard.writeText(text); }
    catch { const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand("copy"); } catch { /* ignore */ } t.remove(); }
    copy.lastChild.textContent = "Copied";
    setTimeout(() => (copy.lastChild.textContent = "Copy"), 1500);
  };
  // Source chips jump to (and open) the matching source card.
  document.querySelectorAll(".cite").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    const card = $("src-" + a.dataset.src);
    if (!card) return;
    const d = card.querySelector("details"); if (d) d.open = true;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
  }));
  // Thumbs up / down: stored in logs/feedback.jsonl for review.
  document.querySelectorAll("[data-fb]").forEach((b) => b.addEventListener("click", async () => {
    const row = b.closest(".ans-actions");
    row.querySelectorAll("[data-fb]").forEach((x) => (x.disabled = true));
    b.classList.add("on");
    try {
      const res = await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: row.dataset.trace, helpful: b.dataset.fb === "1" }) });
      $("thanks").textContent = res.ok ? "Thanks. Saved for review." : "Could not save feedback.";
    } catch { $("thanks").textContent = "Could not save feedback."; }
  }));
  const retry = $("retry"); if (retry) retry.onclick = () => ask(lastQuestion);
}

function reset() {
  clearInterval(timer);
  resultEl.innerHTML = ""; welcomeEl.hidden = false; qEl.value = ""; autosize(); qEl.focus();
  window.scrollTo({ top: 0 });
}

// Drawn once; only the status word and the seconds counter change, so the animations do not restart.
const STAGES = ["Searching the documents", "Reading the matching sections", "Checking document revisions", "Writing the answer"];
function showLoading(q) {
  const start = Date.now();
  show(grid(`<div class="card">${questionHeader(q)}</div>
    <div class="card loading" aria-busy="true">
      <div class="think">${ICON.spark}<span class="think-word" id="tw">${STAGES[0]}</span></div>
      <div class="line w1"></div><div class="line w2"></div><div class="line w3"></div>
      <p class="msg" id="elapsed">Working… 0s</p></div>`));
  timer = setInterval(() => {
    const s = Math.floor((Date.now() - start) / 1000);
    const tw = $("tw"), el = $("elapsed");
    if (!tw || !el) return;
    const next = STAGES[Math.floor(s / 2) % STAGES.length];
    if (tw.textContent !== next) { tw.textContent = next; tw.classList.remove("swap"); void tw.offsetWidth; tw.classList.add("swap"); }
    el.textContent = `Working… ${s}s` + (s >= 6 ? " The local AI can take up to 20 seconds, especially on the first question." : "");
  }, 500);
}

/* ---------- ask ---------- */
function remember(q) {
  const list = [q, ...store.get("recent", []).filter((x) => x !== q)].slice(0, 5);
  store.set("recent", list); drawRecent();
}

async function ask(question) {
  question = question.trim();
  if (question.length < 2) return;
  lastQuestion = question; qEl.value = ""; autosize(); qEl.blur();
  askBtn.disabled = true;
  showLoading(question);
  try {
    const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
    clearInterval(timer);
    if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Server error (${res.status})`); }
    const data = await res.json();
    remember(question);
    show(render(data));
  } catch (e) {
    clearInterval(timer);
    const offline = e instanceof TypeError;
    show(grid(`<div class="card">${questionHeader(question)}</div>
      <div class="card error"><h3>${offline ? "Can't reach the copilot" : "Something went wrong"}</h3>
      <p>${offline ? "Check that you are on the plant Wi-Fi, then try again." : esc(e.message)}</p>
      <div class="actions"><button class="btn" type="button" id="retry">${ICON.retry}Try again</button></div></div>`));
  } finally { askBtn.disabled = false; }
}

/* ---------- welcome screen ---------- */
// A sample-question card: topic tag + the question, coloured by document family.
function sampleCard(s, target) {
  const b = document.createElement("button");
  b.type = "button"; b.className = "chip"; b.dataset.p = s.p;
  b.innerHTML = '<span class="tag"></span><span class="q"></span>';
  b.querySelector(".tag").textContent = s.tag; b.querySelector(".q").textContent = s.q;
  b.onclick = () => ask(s.q); target.appendChild(b);
}
// A "recent question" pill (phone / tablet) and a list row (desktop sidebar).
function drawRecent() {
  const list = store.get("recent", []);
  $("recent-wrap").hidden = !list.length;
  $("side-recent-wrap").hidden = !list.length;
  $("recent").innerHTML = ""; $("side-recent").innerHTML = "";
  list.forEach((q) => {
    const pill = document.createElement("button");
    pill.type = "button"; pill.className = "chip"; pill.textContent = q.length > 44 ? q.slice(0, 42) + "…" : q;
    pill.onclick = () => ask(q); $("recent").appendChild(pill);
    const row = document.createElement("button");
    row.type = "button"; row.className = "side-item"; row.textContent = q; row.title = q;
    row.onclick = () => ask(q); $("side-recent").appendChild(row);
  });
}

async function loadStatus() {
  const pills = document.querySelectorAll(".status");
  const set = (text, cls, title = "") => pills.forEach((el) => { el.textContent = text; el.className = "pill status " + cls; el.title = title; });
  try {
    const h = await (await fetch("/api/health")).json();
    if (!h.index_loaded) set("index missing", "bad");
    else if (h.llm.reachable && h.llm.model_ready) set("Ready", "ok");
    else set("Search only", "warn", "The AI model is not running, so answers show the matching document sections.");
    const d = await (await fetch("/api/documents")).json();
    const by = {};
    d.documents.forEach((x) => (by[x.doc_no] = by[x.doc_no] || []).push(x));
    const html = Object.values(by).map((revs) => {
      revs.sort((a, b) => b.revision - a.revision);
      const t = revs[0];
      const line = revs.map((r) => `Rev ${esc(r.revision)} ${r.status === "current" ? "(current)" : "(superseded)"}`).join(" · ");
      return `<li data-p="${esc(prefixOf(t.doc_no))}"><div class="t">${esc(t.title)}</div><div class="m">${esc(t.doc_no)} · ${line}</div></li>`;
    }).join("");
    $("docs").innerHTML = html; $("side-docs").innerHTML = html;
  } catch { set("offline", "bad"); }
}

/* ---------- composer + theme ---------- */
function autosize() {
  qEl.style.height = "auto";
  qEl.style.height = Math.min(qEl.scrollHeight, 140) + "px";
  qEl.style.overflowY = qEl.scrollHeight > 140 ? "auto" : "hidden";
}
qEl.addEventListener("input", autosize);
qEl.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(qEl.value); } });
$("form").addEventListener("submit", (e) => { e.preventDefault(); ask(qEl.value); });
document.querySelectorAll(".brand").forEach((b) => {
  b.addEventListener("click", reset);
  b.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); reset(); } });
});
$("new-q").addEventListener("click", reset);

document.querySelectorAll(".theme-toggle").forEach((btn) => btn.addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch { /* ignore */ }
}));

SAMPLES.forEach((s) => sampleCard(s, $("chips")));
drawRecent();
loadStatus();
