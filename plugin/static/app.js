/* Receipts — dashboard logic + receipt-card generator. */

const $ = (s) => document.querySelector(s);
let DATA = null;
let currentCardData = null;
// Where shared receipt links resolve — the static GitHub Pages adoption page.
const SHARE_BASE = "https://abhitsian.github.io/receipts/";

/* ---------- formatting ---------- */
function fmtTokens(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return Math.round(n / 1e3) + "K";
  return String(n || 0);
}
function fmtMins(m) {
  if (m >= 60) {
    const h = m / 60;
    const v = h >= 10 ? Math.round(h) : (Math.round(h * 10) / 10);
    return "~" + String(v).replace(/\.0$/, "") + " hr" + (v >= 2 ? "s" : "");
  }
  return "~" + (m || 0) + " min";
}
function esc(s) {
  return (s || "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function shortTime(iso) {
  const d = new Date(iso);
  let h = d.getHours(), ap = h >= 12 ? "p" : "a";
  h = h % 12 || 12;
  return h + ":" + String(d.getMinutes()).padStart(2, "0") + ap;
}
function shortDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function displayName() {
  return ($("#nameInput").value || "").trim() || (DATA && DATA.user) || "you";
}

/* ---------- toast ---------- */
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 2600);
}

/* ---------- load + render ---------- */
async function load() {
  try {
    const r = await fetch("/api/dashboard");
    DATA = await r.json();
  } catch (e) {
    return;
  }
  if (!$("#nameInput").value) {
    $("#nameInput").value = localStorage.getItem("receipts_name") || "";
  }
  render();
}

function render() {
  const d = DATA;
  renderRunning(d.active);
  renderHero(d);
  renderHourly(d.today.hourly);
  renderTrend(d.trend);
  renderReceipts(d.receipts);

  const at = d.alltime;
  $("#footStats").textContent =
    `${at.sessions} sessions · ${fmtTokens(at.tokens)} tokens · ` +
    `${fmtMins(at.minutes_saved)} saved · ${at.days_active} active days`;
}

function renderRunning(active) {
  const strip = $("#runningStrip");
  if (!active || !active.length) { strip.classList.add("hidden"); return; }
  strip.classList.remove("hidden");
  let html = `<span class="live-dot"></span>` +
    `<span class="rs-label">${active.length} session${active.length > 1 ? "s" : ""} running now</span>`;
  active.slice(0, 3).forEach((r) => {
    html += `<span class="rs-item"><b>${esc(r.title)}</b> · ${fmtTokens(r.total_tokens)} tokens</span>`;
  });
  strip.innerHTML = html;
}

function renderHero(d) {
  const t = d.today;
  const tasks = $("#statTasks");
  tasks.querySelector(".stat-value").textContent = t.tasks;
  tasks.querySelector(".stat-sub").innerHTML = t.noncode > 0
    ? `<span class="good">${t.noncode} needed no code</span>`
    : (t.tasks ? "all code work today" : "nothing yet today");

  $("#statSaved .stat-value").textContent = fmtMins(t.minutes_saved).replace("~", "");

  const streak = $("#statStreak");
  streak.querySelector(".stat-value").textContent = (d.streak ? "🔥 " : "") + d.streak;
  streak.querySelector(".stat-sub").textContent =
    d.streak >= 2 ? "days in a row" : d.streak === 1 ? "day — keep it going" : "start one today";

  const tok = $("#statTokens");
  tok.querySelector(".stat-value").textContent = fmtTokens(t.tokens);
  tok.querySelector(".stat-sub").textContent = `across ${t.sessions} session${t.sessions === 1 ? "" : "s"}`;
}

function renderHourly(hourly) {
  const max = Math.max(...hourly, 1);
  const nowH = new Date().getHours();
  let bars = "", axis = "";
  hourly.forEach((v, h) => {
    const pct = Math.round((v / max) * 100);
    const cls = "hbar" + (v === 0 ? " empty" : "") + (h === nowH ? " now" : "");
    bars += `<div class="${cls}" style="height:${Math.max(pct, 2)}%" ` +
      `data-tip="${String(h).padStart(2, "0")}:00 — ${fmtTokens(v)}"></div>`;
    axis += `<span>${[0, 6, 12, 18].includes(h) ? h : ""}</span>`;
  });
  $("#hourlyChart").innerHTML = bars;
  let ax = $("#hourAxis");
  if (!ax) {
    ax = document.createElement("div");
    ax.id = "hourAxis";
    ax.className = "hour-axis";
    $("#hourlyChart").after(ax);
  }
  ax.innerHTML = axis;
}

function renderTrend(trend) {
  const max = Math.max(...trend.map((x) => x.tokens), 1);
  let total = 0;
  $("#trendChart").innerHTML = trend.map((x) => {
    total += x.tokens;
    const pct = Math.round((x.tokens / max) * 100);
    return `<div class="tcol ${x.is_today ? "today" : ""}" ` +
      `title="${x.date} · ${fmtTokens(x.tokens)} tokens · ${x.sessions} sessions">` +
      `<div class="tbar ${x.tokens > 0 ? "has" : ""}" style="height:${Math.max(pct, 3)}%"></div>` +
      `<div class="tlabel">${x.label[0]}</div></div>`;
  }).join("");
  $("#trendNote").textContent = `${fmtTokens(total)} tokens · 2 weeks`;
}

function renderReceipts(receipts) {
  const list = $("#receiptList");
  if (!receipts.length) {
    list.innerHTML = `<div class="empty-note">No sessions yet. Use Claude Code, then come back.</div>`;
    return;
  }
  list.innerHTML = receipts.map((r, i) => {
    const spark = r.category === "non-code" ? "✨ " : "";
    return `<div class="rrow" data-i="${i}">
      <div class="rrow-time">${shortTime(r.start)}</div>
      <div class="rrow-main">
        <div class="rrow-title">${spark}${esc(r.title)}</div>
        <div class="rrow-meta">${shortDate(r.start)} · ${esc(r.project)} · ${r.tool_count} tool calls · ${fmtMins(r.minutes_saved)}</div>
      </div>
      <span class="badge ${r.category === "non-code" ? "noncode" : r.category}">${r.task_type}</span>
      <div class="rrow-tok"><b>${fmtTokens(r.total_tokens)}</b><br>tokens</div>
    </div>`;
  }).join("");
  list.querySelectorAll(".rrow").forEach((row) => {
    row.onclick = () => openSessionCard(receipts[+row.dataset.i]);
  });
}

/* ---------- receipt card ---------- */
function cardDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric", year: "numeric",
  }).toUpperCase();
}
function barcodeNum(seed) {
  return (seed || "").replace(/[^a-z0-9]/gi, "").slice(0, 14).toUpperCase().padEnd(14, "0");
}

function buildCard(c) {
  const lines = c.lines.map(
    ([k, v]) => `<div class="r-line"><span>${k}</span><span>${v}</span></div>`
  ).join("");
  const built = c.built
    ? `<div class="r-built">BUILT: <b class="r-edit" contenteditable="true">${esc(c.built)}</b></div>`
    : "";
  const badge = c.badge ? `<div class="r-badge">${c.badge}</div>` : "";
  // Optional editable free-text block (e.g. today's line-up). Never the raw
  // prompt — that can leak sensitive content. Generic by default, editable,
  // rendered as plain text (pre-line) so it carries safely into a share link.
  const notes = c.notesText
    ? `<div class="r-prompt-label">— ${esc(c.notesLabel)} —</div>` +
      `<div class="r-prompt r-edit" contenteditable="true">${esc(c.notesText)}</div>` +
      `<div class="r-dash"></div>`
    : "";
  return `<div class="receipt" id="theCard">
    <div class="zig"></div>
    <div class="r-body">
      <div class="r-logo">🧾 RECEIPTS</div>
      <div class="r-sub">CLAUDE CODE · @${esc(displayName()).toUpperCase()}</div>
      <div class="r-dash"></div>
      <div class="r-date">${c.date}</div>
      <div class="r-dash"></div>
      <div class="r-item-name r-edit" contenteditable="true">${esc(c.item)}</div>
      <div style="margin-top:11px">${lines}</div>
      ${built}
      <div class="r-dash"></div>
      <div class="r-line big"><span>TIME SAVED</span><span>${c.saved}</span></div>
      <div class="r-dash"></div>
      ${badge}
      ${notes}
      <div class="r-foot">${c.foot}</div>
      <img class="r-qr" src="/static/qr.png" alt="QR code — scan to get Receipts">
      <div class="r-qr-cap">SCAN TO GET RECEIPTS · FREE</div>
    </div>
    <div class="zig bottom"></div>
  </div>`;
}

function openSessionCard(r) {
  // Headline pre-fills from the title — a one-liner, not the raw prompt —
  // and is editable on the card so anything sensitive can be scrubbed.
  showCard({
    date: cardDate(r.start),
    item: r.title,
    lines: [
      ["TASK TYPE", r.task_type],
      ["TOOL CALLS", r.tool_count],
      ["TOKENS", fmtTokens(r.total_tokens)],
      ["MODEL", r.model],
    ],
    built: r.files_created.length ? r.files_created.join(", ") : "",
    saved: fmtMins(r.minutes_saved).replace("~", "").toUpperCase(),
    badge: r.category === "non-code" ? "✨ NO CODE NEEDED ✨" : "",
    notesLabel: "",
    notesText: "",
    foot: "you can do this too →",
    barcode: barcodeNum(r.id),
  });
}

function openTodayCard() {
  const t = DATA.today;
  if (!t.tasks) { toast("Nothing logged today yet — go use Claude Code"); return; }
  const todayStr = new Date().toISOString().slice(0, 10);
  const todays = DATA.receipts.filter((r) => r.start.slice(0, 10) === todayStr);
  const lineup = todays.slice(0, 6)
    .map((r) => `• ${r.title}`).join("\n") || "—";
  showCard({
    date: cardDate(new Date().toISOString()),
    item: `${t.tasks} thing${t.tasks === 1 ? "" : "s"} done today`,
    lines: [
      ["NEEDED NO CODE", `${t.noncode} of ${t.tasks}`],
      ["SESSIONS", t.sessions],
      ["TOKENS BURNED", fmtTokens(t.tokens)],
    ],
    built: "",
    saved: fmtMins(t.minutes_saved).replace("~", "").toUpperCase(),
    badge: t.noncode > 0 ? `✨ ${t.noncode} DONE WITHOUT CODE ✨` : "",
    notesLabel: "WHAT I DID",
    notesText: lineup,
    foot: "your turn →",
    barcode: barcodeNum(todayStr + displayName()),
  });
}

function showCard(card) {
  currentCardData = card;
  $("#cardHost").innerHTML = buildCard(card);
  $("#modal").classList.remove("hidden");
}

/* ---------- copy / download ---------- */
async function copyImage() {
  const card = $("#theCard");
  if (!card) return;
  try {
    const canvas = await html2canvas(card, { scale: 2, backgroundColor: null, logging: false });
    canvas.toBlob(async (blob) => {
      try {
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        toast("Receipt copied — paste it in Slack or Teams");
      } catch (e) {
        toast("Clipboard blocked — use Download PNG instead");
      }
    }, "image/png");
  } catch (e) {
    toast("Couldn't render — try Download PNG");
  }
}

async function downloadImage() {
  const card = $("#theCard");
  if (!card) return;
  const canvas = await html2canvas(card, { scale: 2, backgroundColor: null, logging: false });
  const a = document.createElement("a");
  a.download = "receipt.png";
  a.href = canvas.toDataURL("image/png");
  a.click();
}

function copyText() {
  const card = $("#theCard");
  if (!card) return;
  const lines = [];
  lines.push("🧾 RECEIPTS — CLAUDE CODE");
  card.querySelectorAll(".r-item-name, .r-line, .r-built, .r-badge, .r-prompt, .r-foot")
    .forEach((el) => {
      if (el.classList.contains("r-line")) {
        const s = el.querySelectorAll("span");
        lines.push(`${s[0].textContent}: ${s[1].textContent}`);
      } else {
        lines.push(el.innerText.trim());
      }
    });
  lines.push("claude.com/code");
  navigator.clipboard.writeText(lines.join("\n"))
    .then(() => toast("Receipt text copied"))
    .catch(() => toast("Copy failed"));
}

/* ---------- share link ---------- */
function createShareLink() {
  const card = $("#theCard");
  if (!card || !currentCardData) return;
  // Snapshot the card *as edited* — the user may have scrubbed the headline,
  // file list, or notes. Only this sanitized content goes into the link; it is
  // encoded into the URL itself, so nothing is uploaded or stored anywhere.
  const data = Object.assign({}, currentCardData, { name: displayName() });
  const itemEl = card.querySelector(".r-item-name");
  if (itemEl) data.item = itemEl.innerText.trim();
  const builtEl = card.querySelector(".r-built b");
  if (builtEl) data.built = builtEl.innerText.trim();
  const notesEl = card.querySelector(".r-prompt");
  if (notesEl) data.notesText = notesEl.innerText.trim();
  try {
    const url = SHARE_BASE + "#" + btoa(encodeURIComponent(JSON.stringify(data)));
    navigator.clipboard.writeText(url)
      .then(() => toast("Share link copied — it opens your card + how to get Receipts"))
      .catch(() => toast("Clipboard blocked — couldn't copy the link"));
  } catch (e) {
    toast("Couldn't build the link");
  }
}

/* ---------- wiring ---------- */
$("#todayReceiptBtn").onclick = openTodayCard;
$("#shareLinkBtn").onclick = createShareLink;
$("#copyImgBtn").onclick = copyImage;
$("#copyTxtBtn").onclick = copyText;
$("#dlBtn").onclick = downloadImage;
$("#closeBtn").onclick = () => $("#modal").classList.add("hidden");
$("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); };
$("#nameInput").oninput = (e) => localStorage.setItem("receipts_name", e.target.value.trim());

load();
setInterval(load, 7000);

/* ============ Insights view ============ */
let currentDays = 30;
const PALETTE = ["#ff9a3c", "#9aa6e8", "#5fd6a4", "#e87fae", "#7fd0e8", "#d8c45f"];

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.onclick = () => {
      document.querySelectorAll(".tab")
        .forEach((x) => x.classList.toggle("active", x === tab));
      const view = tab.dataset.view;
      $("#viewDashboard").classList.toggle("hidden", view !== "dashboard");
      $("#viewInsights").classList.toggle("hidden", view !== "insights");
      if (view === "insights") loadInsights(currentDays);
    };
  });
}

function setupPeriod() {
  $("#periodPicker").querySelectorAll("button").forEach((b) => {
    b.onclick = () => {
      $("#periodPicker").querySelectorAll("button")
        .forEach((x) => x.classList.toggle("active", x === b));
      loadInsights(+b.dataset.days);
    };
  });
}

async function loadInsights(days) {
  currentDays = days;
  let ins;
  try {
    ins = await (await fetch("/api/insights?days=" + days)).json();
  } catch (e) {
    return;
  }
  renderInsights(ins);
}

function renderInsights(ins) {
  $("#insSummary").innerHTML = [
    ["is-val amber", fmtTokens(ins.total_tokens), "tokens burned"],
    ["is-val", ins.total_sessions, "sessions"],
    ["is-val", fmtMins(ins.total_saved).replace("~", ""), "time saved"],
    ["is-val", ins.active_days, "active days"],
  ].map(([c, v, l]) =>
    `<div class="is-item"><div class="${c}">${v}</div>` +
    `<div class="is-label">${l}</div></div>`).join("");

  renderInsDaily(ins.daily);
  renderHbars("#insByTask", ins.by_task);
  renderHbars("#insByProject", ins.by_project);
  renderHeatmap(ins.heatmap);

  const c = ins.by_category;
  renderSplitBar("#insCategory", [
    { label: "Code", tokens: c.code, color: "#9aa6e8" },
    { label: "Mixed", tokens: c.mixed, color: "#f0b878" },
    { label: "No code", tokens: c["non-code"], color: "#5fd6a4" },
  ]);
  renderSplitBar("#insModel", ins.by_model.map((m, i) =>
    ({ label: m.name, tokens: m.tokens, color: PALETTE[i % PALETTE.length] })));
}

function renderInsDaily(daily) {
  const el = $("#insDaily");
  const max = Math.max(...daily.map((d) => d.tokens), 1);
  const cols = `repeat(${daily.length}, 1fr)`;
  el.style.gridTemplateColumns = cols;
  el.innerHTML = daily.map((d) => {
    const pct = Math.round((d.tokens / max) * 100);
    const wk = d.dow === "Sat" || d.dow === "Sun";
    const cls = "dbar" + (d.tokens === 0 ? " empty" : wk ? " weekend" : "");
    return `<div class="${cls}" style="height:${Math.max(pct, 2)}%" ` +
      `title="${d.label} (${d.dow}) — ${fmtTokens(d.tokens)} tokens"></div>`;
  }).join("");

  // Date axis — label ~7 evenly spaced bars (plus the last) so 30/90-day
  // views stay readable.
  const last = daily.length - 1;
  const step = Math.max(1, Math.round(daily.length / 7));
  let ax = $("#insDailyAxis");
  if (!ax) {
    ax = document.createElement("div");
    ax.id = "insDailyAxis";
    ax.className = "daily-axis";
    el.after(ax);
  }
  ax.style.gridTemplateColumns = cols;
  ax.innerHTML = daily.map((d, i) => {
    const show = i % step === 0 || i === last;
    return `<span>${show ? d.label : ""}</span>`;
  }).join("");

  const tot = daily.reduce((s, d) => s + d.tokens, 0);
  $("#insDailyNote").textContent = `${fmtTokens(tot)} across ${daily.length} days`;
}

function renderHbars(sel, items) {
  const el = $(sel);
  if (!items.length) {
    el.innerHTML = `<div class="empty-note">No data in this period.</div>`;
    return;
  }
  const max = Math.max(...items.map((i) => i.tokens), 1);
  el.innerHTML = items.map((i) =>
    `<div class="hbar-row">
      <div class="hbar-label" title="${esc(i.name)}">${esc(i.name)}</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:${Math.round(i.tokens / max * 100)}%"></div></div>
      <div class="hbar-val"><b>${fmtTokens(i.tokens)}</b> · ${i.pct}%</div>
    </div>`).join("");
}

function renderHeatmap(heat) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  let max = 1;
  heat.forEach((row) => row.forEach((v) => { if (v > max) max = v; }));
  let html = "";
  heat.forEach((row, di) => {
    html += `<div class="hm-row"><div class="hm-day">${days[di]}</div>`;
    row.forEach((v, h) => {
      const a = v === 0 ? 0 : (0.12 + 0.88 * (v / max));
      html += `<div class="hm-cell" style="background:rgba(255,154,60,${a.toFixed(3)})" ` +
        `title="${days[di]} ${String(h).padStart(2, "0")}:00 — ${fmtTokens(v)} tokens"></div>`;
    });
    html += "</div>";
  });
  let ax = `<div class="hm-axis"><span></span>`;
  for (let h = 0; h < 24; h++) ax += `<span>${[0, 6, 12, 18].includes(h) ? h : ""}</span>`;
  $("#insHeatmap").innerHTML = html + ax + "</div>";
}

function renderSplitBar(sel, segs) {
  const total = segs.reduce((s, x) => s + x.tokens, 0) || 1;
  const track = segs.filter((s) => s.tokens > 0).map((s) =>
    `<div class="sb-seg" style="width:${(s.tokens / total * 100).toFixed(1)}%;` +
    `background:${s.color}" title="${esc(s.label)}: ${fmtTokens(s.tokens)}"></div>`).join("");
  const legend = segs.map((s) =>
    `<div class="sb-key"><span class="sb-dot" style="background:${s.color}"></span>` +
    `${esc(s.label)} · ${fmtTokens(s.tokens)} (${Math.round(s.tokens / total * 100)}%)</div>`).join("");
  $(sel).innerHTML = `<div class="sb-track">${track}</div><div class="sb-legend">${legend}</div>`;
}

setupTabs();
setupPeriod();
