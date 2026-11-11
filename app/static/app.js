"use strict";

const SAMPLES = [
  "What is the recommended coolant concentration for the TX-200 CNC turning centre?",
  "The machine is showing alarm AL-104. What does it mean and what should the operator do?",
  "Who is allowed to remove a lockout lock from a machine?",
  "What is the outer diameter tolerance for the BH-220 bearing housing?",
  "How often should spindle runout be checked, and who does it?",
  "AL-305",
];

const $ = (id) => document.getElementById(id);
const resultEl = $("result");
let timer = null;

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Turn the chunk text (plain lines + markdown tables) into safe HTML.
function renderExcerpt(text) {
  const lines = text.split("\n");
  let html = "", i = 0;
  while (i < lines.length) {
    if (lines[i].startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].startsWith("|")) { rows.push(lines[i]); i++; }
      const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      html += "<table><thead><tr>" + cells(rows[0]).map((c) => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody>";
      rows.slice(2).forEach((r) => { html += "<tr>" + cells(r).map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>"; });
      html += "</tbody></table>";
    } else {
      html += `<p>${esc(lines[i])}</p>`; i++;
    }
  }
  return html;
}

function sourceCard(s) {
  const sup = s.status === "superseded";
  const pageTxt = s.page_range[0] === s.page_range[1] ? `p.${s.page_range[0]}` : `p.${s.page_range[0]}–${s.page_range[1]}`;
  return `
  <div class="card src ${sup ? "superseded" : ""}">
    <div><span class="src-title">${esc(s.doc_no)}</span> Rev ${esc(s.revision)}
      <span class="badge ${sup ? "superseded" : "current"}">${sup ? "SUPERSEDED" : "CURRENT"}</span>
      ${s.cited ? '<span class="badge used">used in answer</span>' : ""}</div>
    <div class="ref">${esc(s.title)}<br>Section ${esc(s.section)} · ${pageTxt} · effective ${esc(s.effective_date)}</div>
    ${sup ? '<div class="banner superseded">Superseded revision. Do not use it for current work.</div>' : ""}
    <details><summary>Show the exact text</summary><div class="excerpt">${renderExcerpt(s.text)}</div></details>
    <div class="actions"><a class="btn" href="${esc(s.pdf_url)}" target="_blank" rel="noopener">Open PDF at page ${s.page}</a></div>
  </div>`;
}

function render(r) {
  let html = "";
  if (r.mode === "not_found") {
    html += `<div class="card notfound"><h2>Not found in the plant documents</h2>
      <p>I couldn't find this in the SOPs and manuals I have, so I won't guess.</p>
      ${r.notice ? `<p><strong>${esc(r.notice)}</strong></p>` : ""}`;
    if (r.closest.length) {
      html += "<p class='meta'>Closest documents (they may not answer this):</p>" +
        r.closest.map((c) => `<div class="actions"><a class="btn alt" href="${esc(c.pdf_url)}" target="_blank" rel="noopener">${esc(c.doc_no)} Rev ${esc(c.revision)}: ${esc(c.title)}</a></div>`).join("");
    }
    html += `<p class="meta">${r.latency_ms} ms</p></div>`;
    resultEl.innerHTML = html;
    return;
  }

  html += `<div class="card"><h2>Answer</h2>`;
  if (r.safety_flag) html += `<div class="banner safety">⚠ Safety-critical. Confirm against the SOP page below before you act.</div>`;
  if (r.mode === "retrieval_only") {
    html += `<div class="banner info">${esc(r.notice)}</div>`;
  } else {
    html += `<div class="answer" style="margin-top:12px">${esc(r.answer)}</div>`;
  }
  (r.revision_notes || []).forEach((n) => { html += `<div class="banner info">${esc(n)}</div>`; });
  html += `<p class="meta">${r.latency_ms} ms</p></div>`;

  const used = r.sources.filter((s) => s.cited), other = r.sources.filter((s) => !s.cited);
  html += "<h3>Source</h3>" + used.map(sourceCard).join("");
  if (other.length) {
    html += `<details style="margin-top:10px"><summary>Other matching sections (${other.length})</summary>${other.map(sourceCard).join("")}</details>`;
  }
  resultEl.innerHTML = html;
}

function showLoading() {
  const start = Date.now();
  const paint = () => {
    const s = Math.floor((Date.now() - start) / 1000);
    const extra = s >= 6 ? " The local AI can take up to 20 seconds on the first question." : "";
    resultEl.innerHTML = `<div class="card loading"><div class="spin"></div><div>Searching the documents… ${s}s${extra}</div></div>`;
  };
  paint();
  timer = setInterval(paint, 1000);
}

async function ask(question) {
  question = question.trim();
  if (question.length < 2) return;
  $("ask").disabled = true;
  showLoading();
  try {
    const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
    clearInterval(timer);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }
    render(await res.json());
  } catch (e) {
    clearInterval(timer);
    const offline = e instanceof TypeError;
    resultEl.innerHTML = `<div class="card error"><h2>${offline ? "Can't reach the copilot" : "Something went wrong"}</h2>
      <p>${offline ? "Check that you are on the plant Wi-Fi and try again." : esc(e.message)}</p></div>`;
  } finally {
    $("ask").disabled = false;
  }
}

async function loadStatus() {
  const el = $("status");
  try {
    const h = await (await fetch("/api/health")).json();
    if (!h.index_loaded) { el.textContent = "index missing"; el.className = "status bad"; return; }
    if (h.llm.reachable && h.llm.model_ready) { el.textContent = "ready"; el.className = "status ok"; }
    else { el.textContent = "AI offline: search only"; el.className = "status warn"; }
    const d = await (await fetch("/api/documents")).json();
    $("docs").textContent = d.documents.filter((x) => x.status === "current").length + " current documents indexed";
  } catch { el.textContent = "offline"; el.className = "status bad"; }
}

$("form").addEventListener("submit", (e) => { e.preventDefault(); ask($("q").value); });
$("q").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask($("q").value); } });
SAMPLES.forEach((s) => {
  const b = document.createElement("button");
  b.type = "button"; b.className = "chip"; b.textContent = s; b.title = s;
  b.addEventListener("click", () => { $("q").value = s; ask(s); });
  $("chips").appendChild(b);
});
loadStatus();
