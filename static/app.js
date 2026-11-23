/* Namma Mitra client: renders the WhatsApp phone, the Flow sheet, the payment sheet,
 * the service rail and the "behind the chat" pipeline. All logic lives on the server. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };
  const newSid = () => "s-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  let SID = store.get("nm_session", null) || newSid();
  store.set("nm_session", SID);
  let LANG = "kn", UI = {}, P = null, SERVICES = [];
  let showQueue = Promise.resolve(), lastSide = null;
  const stream = $("#stream"), msgBox = $("#messages"), input = $("#input"), sendBtn = $("#send");

  // ---------------------------------------------------------------- icons
  const ICON = {
    list: '<svg viewBox="0 0 24 24"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>',
    pay: '<svg viewBox="0 0 24 24"><path d="M20 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/></svg>',
    dl: '<svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>',
    form: '<svg viewBox="0 0 24 24"><path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-9 14H7v-2h3v2zm0-4H7v-2h3v2zm0-4H7V7h3v2zm7 8h-5v-2h5v2zm0-4h-5v-2h5v2zm0-4h-5V7h5v2z"/></svg>',
    search: '<svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>',
  };
  // Monochrome line icons per service (stroke-based, see .tile svg in CSS)
  const SVC_ICON = {
    certificate: '<svg viewBox="0 0 24 24"><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 12h6M9 16h6"/></svg>',
    energy: '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h6l-1 8 9-12h-6z"/></svg>',
    education: '<svg viewBox="0 0 24 24"><path d="m2 9 10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/><path d="M22 9v6"/></svg>',
    land: '<svg viewBox="0 0 24 24"><path d="M3 20h18"/><path d="M4 20c2-8 5-12 8-12s6 4 8 12"/><path d="M9 14h6"/></svg>',
    ration: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/><path d="M7 14h4"/></svg>',
    bus: '<svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="15" rx="3"/><path d="M4 10h16"/><path d="M8 21v-3M16 21v-3"/><path d="M8 14h.01M16 14h.01"/></svg>',
    vehicle: '<svg viewBox="0 0 24 24"><path d="M5 16 6.5 9h11L19 16"/><rect x="3" y="12" width="18" height="6" rx="2"/><path d="M7 21v-3M17 21v-3"/><path d="M7 15h.01M17 15h.01"/></svg>',
    grievance: '<svg viewBox="0 0 24 24"><path d="M4 4h16v11H8l-4 4z"/><path d="M12 7v4M12 13h.01"/></svg>',
    gruhalakshmi: '<svg viewBox="0 0 24 24"><path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M12 13a1.6 1.6 0 0 1 3 .6c0 1.5-3 3.4-3 3.4s-3-1.9-3-3.4a1.6 1.6 0 0 1 3-.6z"/></svg>',
    yuvanidhi: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-3.5 3-6 7-6s7 2.5 7 6"/><path d="M15 4h5M17.5 1.5v5"/></svg>',
  };
  const TICK = '<svg viewBox="0 0 16 11"><path d="M11.07.65 10.4 0 4.98 5.42 2.7 3.14 2.02 3.8l2.96 2.97zm3.35 0L8.98 6.08l-.75-.75-.67.67 1.42 1.42L15.1 1.3zM.4 6.15l2.95 2.96.67-.66L1.07 5.49z"/></svg>';

  // ---------------------------------------------------------------- api
  async function api(path, body = {}) {
    body.session_id = SID;
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    if (j.lang) { LANG = j.lang; document.documentElement.lang = LANG; }
    if (j.services && j.services.length) SERVICES = j.services;
    if (j.ui) applyUI(j.ui);
    if (j.trace_id) showTrace(j.trace_id);
    return j;
  }
  function applyUI(ui) {
    UI = ui;
    input.placeholder = UI.type_message;
    $("#dateChip").textContent = UI.today;
    $("#noticeEnc").textContent = UI.encrypted;
    $("#noticeMeta").textContent = UI.secure_notice;
    $("#headSub").textContent = UI.online;
    document.querySelectorAll("#langs button").forEach(b => b.classList.toggle("on", b.dataset.lang === LANG));
    renderServiceRail();
  }

  // ---------------------------------------------------------------- formatting
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function inline(s) {
    return s
      .replace(/```([^`]+)```/g, "<code>$1</code>")
      .replace(/(^|[\s(“"'>•])\*(?!\s)([^*\n]+?)\*(?=$|[\s).,!?:;”"'<])/g, "$1<b>$2</b>")
      .replace(/(^|[\s(“"'>•])_(?!\s)([^_\n]+?)_(?=$|[\s).,!?:;”"'<])/g, "$1<i>$2</i>")
      .replace(/(^|[\s(])~(?!\s)([^~\n]+?)~(?=$|[\s).,!?:;])/g, "$1<s>$2</s>");
  }
  function fmt(text) {
    return esc(text).split("\n").map(line =>
      line.startsWith("&gt; ") ? `<div class="q">${inline(line.slice(5))}</div>` : inline(line)
    ).join("<br>").replace(/<\/div><br>/g, "</div>");
  }
  function clock(ts) {
    const d = ts ? new Date(ts * 1000) : new Date();
    let h = d.getHours(); const m = String(d.getMinutes()).padStart(2, "0");
    const ap = h >= 12 ? "pm" : "am"; h = h % 12 || 12;
    return `${h}:${m} ${ap}`;
  }
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const scrollDown = () => requestAnimationFrame(() => { msgBox.scrollTop = msgBox.scrollHeight; });

  // ---------------------------------------------------------------- chat rendering
  function render(m, live = true) {
    const side = m.dir === "in" ? "out" : "in";       // server "in" = from the citizen -> right side
    const row = document.createElement("div");
    row.className = `row ${side}` + (lastSide === side ? " cont" : "");
    lastSide = side;
    const b = document.createElement("div");
    b.className = "bubble" + (m.type === "image" ? " has-img" : "") + (m.type === "system" ? " system" : "");
    let html = "";
    if (m.type === "image") html += `<img class="photo" src="${esc(m.image)}" alt="">`;
    if (m.type === "document") {
      html += `<div class="doc" data-doc="${esc(m.doc.id)}"><div class="pdf">PDF</div><div class="dn"><b>${esc(m.doc.name)}</b><span>${esc(UI.pdf_meta || "PDF")}</span></div><div class="dl">${ICON.dl}</div></div>`;
    }
    if (m.type === "flow_response") {
      html += `<div class="flowresp"><div class="fi">${ICON.form}</div><div><b>${esc(m.text)}</b><small>${esc(m.sub || "")}</small></div></div>`;
      if (m.answers && m.answers.length) html += `<button class="cta view-resp">${esc(UI.view_response || "View response")}</button>`;
    } else if (m.text) {
      html += `<div class="txt">${fmt(m.text)}</div>`;
    }
    if (m.footer) html += `<div class="footer">${fmt(m.footer)}</div>`;
    const trace = m.trace_id ? `<span class="trace" data-trace="${m.trace_id}" title="Trace number: quote it when reporting an issue">#${m.trace_id}</span>` : "";
    const tick = side === "out" ? `<span class="tick ${live ? "" : "read"}">${TICK}</span>` : "";
    html += `<span class="meta">${trace}<span>${clock(m.ts)}</span>${tick}</span>`;
    if (m.cta) html += `<button class="cta">${ICON[m.cta.icon] || ""}<span>${esc(m.cta.label)}</span></button>`;
    b.innerHTML = html;
    row.appendChild(b);
    if (m.cta) $(".cta", b).onclick = e => handleCta(m.cta.action, e.currentTarget);
    const vr = $(".view-resp", b);
    if (vr) vr.onclick = () => showResponse(m);
    const doc = $(".doc", b);
    if (doc) doc.onclick = () => window.open("/doc/" + doc.dataset.doc + ".pdf", "_blank");
    const tr = $(".trace", b);
    if (tr) tr.onclick = () => window.open("/logs?trace=" + tr.dataset.trace, "_blank");
    if (m.buttons && m.buttons.length) {
      const wrap = document.createElement("div");
      wrap.className = "btns";
      m.buttons.forEach(bt => {
        const btn = document.createElement("button");
        btn.textContent = bt.label;
        btn.onclick = () => sendPayload(bt.label, bt.payload);
        wrap.appendChild(btn);
      });
      row.appendChild(wrap);
    }
    stream.appendChild(row);
    scrollDown();
    return row;
  }
  function showBot(msgs) {
    msgs = msgs || [];
    showQueue = showQueue.then(async () => {
      for (const m of msgs) {
        $("#typing").hidden = false; $("#headSub").textContent = UI.typing || "typing…";
        scrollDown();
        await sleep(Math.min(1000, 350 + (m.text || "").length * 1.1));
        $("#typing").hidden = true; $("#headSub").textContent = UI.online || "online";
        render(m);
      }
    });
    return showQueue;
  }
  function markRead() { document.querySelectorAll(".tick:not(.read)").forEach(t => t.classList.add("read")); }
  function toast(text, onClick, ms = 4000) {
    const t = $("#toast"); t.textContent = text; t.hidden = false;
    t.onclick = () => { t.hidden = true; onClick && onClick(); };
    clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, ms);
  }

  async function sendText(text) {
    text = text.trim();
    if (!text) return;
    $("#sayHi").hidden = true;
    render({ dir: "in", type: "text", text, ts: Date.now() / 1000 });
    try {
      const res = await api("/api/message", { text });
      markRead();
      await showBot(res.messages);
    } catch (e) { toast(UI.network_error || "Connection problem. Tap to retry.", () => sendText(text)); }
  }
  async function sendPayload(label, payload) {
    render({ dir: "in", type: "text", text: label, ts: Date.now() / 1000 });
    try {
      const res = await api("/api/message", { text: label, label, payload });
      markRead();
      await showBot(res.messages);
    } catch (e) { toast(UI.network_error || "Connection problem. Tap to retry.", () => sendPayload(label, payload)); }
  }
  function handleCta(action, btn) {
    if (!action) return;
    if (action.kind === "panel") return openPanel(action.service, action.prefill);
    if (action.kind === "pay") return openPay(action.payment_id, btn);
  }

  // ---------------------------------------------------------------- field logic (mirror of flowkit.py)
  function visible(f, values, byId) {
    if (!f.show_if) return true;
    return Object.entries(f.show_if).every(([ref, exp]) => {
      const parent = byId[ref];
      if (parent && !visible(parent, values, byId)) return false;
      return (Array.isArray(exp) ? exp : [exp]).includes(values[ref]);
    });
  }
  function visibleFields() {
    const byId = Object.fromEntries(P.fields.map(f => [f.id, f]));
    return P.fields.filter(f => visible(f, P.values, byId));
  }
  function transform(f, v) {
    let s = String(v ?? "").trim();
    if (f.transform === "upper") s = s.toUpperCase();
    if (f.transform === "upper_nospace") s = s.toUpperCase().replace(/[\s-]/g, "");
    if (f.transform === "digits") s = s.replace(/[\s-]/g, "");
    return s;
  }
  function fieldError(f) {
    const v = P.values[f.id];
    const empty = v === undefined || v === null || String(v).trim() === "";
    if (f.type === "info") return null;
    if (empty) return f.required === false ? null : (["radio", "dropdown"].includes(f.type) ? UI.select_option : UI.required);
    if (f.type === "number") {
      const n = Number(String(v).replace(/,/g, ""));
      if (!Number.isFinite(n)) return UI.invalid_format;
      if ((f.min != null && n < f.min) || (f.max != null && n > f.max))
        return (f.error || UI.number_range || "{min} - {max}").split("{min}").join(f.min).split("{max}").join(f.max);
      return null;
    }
    if (f.type === "date") {
      const dmy = x => String(x || "").split("-").reverse().join("-");
      if ((f.min_date && v < f.min_date) || (f.max_date && v > f.max_date))
        return (f.error || UI.date_range || "{a} - {b}").split("{a}").join(dmy(f.min_date)).split("{b}").join(dmy(f.max_date));
      return null;
    }
    if (["text", "textarea"].includes(f.type)) {
      const s = transform(f, v);
      if (f.min_len && s.length < f.min_len) return UI.invalid_format;
      if (f.pattern && !(new RegExp(f.pattern, "u")).test(s)) return f.error || UI.invalid_format;
    }
    return null;
  }
  const formValid = () => P && P.service && visibleFields().every(f => !fieldError(f));

  // ---------------------------------------------------------------- Flow sheet
  async function openPanel(service, prefill) {
    try {
      const res = await api("/api/panel/open", { service, prefill });
      P = Object.assign({ values: {}, errors: {}, touched: {}, stack: [], list: null }, res.panel);
      P.values = Object.assign({}, res.panel.values || {});
      SERVICES = res.panel.services || SERVICES;
      $("#payModal").hidden = true;
      $("#confirm").parentElement.hidden = false;
      $("#panel").hidden = false;
      renderPanel();
    } catch (e) { toast(UI.network_error || "Connection problem"); }
  }
  function closePanel() { P = null; $("#panel").hidden = true; $("#confirm").parentElement.hidden = false; input.focus(); }
  // Read-only "View response" sheet for a submitted form (as in WhatsApp Flows)
  function showResponse(m) {
    P = null;
    $("#payModal").hidden = true;
    $("#panelTitle").textContent = UI.your_response || "Your response";
    $("#panelBack").classList.remove("show");
    $("#panelBody").innerHTML = `<p class="heading">${esc(m.text)}</p><p class="req-note">${esc(UI.response_note || "")}</p>` +
      m.answers.map(a => `<div class="field"><div class="flabel">${esc(a.label)}</div><div class="resp-val">${esc(a.value)}</div></div>`).join("");
    $("#confirm").parentElement.hidden = true;
    $("#panel").hidden = false;
    $("#panelBody").scrollTop = 0;
  }
  async function selectService(key) {
    P.list = null;
    if (key === P.service) return renderPanel();
    try {
      const res = await api("/api/panel/service", { service: key });
      Object.assign(P, { service: key, fields: res.fields, values: {}, errors: {}, touched: {} });
      renderPanel(); $("#panelBody").scrollTop = 0;
    } catch (e) { toast(UI.network_error || "Connection problem"); }
  }
  function renderPanel() {
    const body = $("#panelBody");
    $("#panelBack").classList.toggle("show", !!(P.list || P.stack.length));
    if (P.list) return renderList(body);
    $("#panelTitle").textContent = P.screen === "main" ? UI.panel_title : P.title;
    let html = "";
    if (P.screen === "main") {
      html += `<div class="banner"><img src="/static/img/gok_logo.jpg" alt=""><div class="bt"><b>ನಮ್ಮ ಮಿತ್ರ · Namma Mitra</b><span>${LANG === "kn" ? "ಕರ್ನಾಟಕ ಸರ್ಕಾರ · ನಾಗರಿಕ ಸೇವೆಗಳು" : "Government of Karnataka · Citizen Services"}</span></div></div>`;
      html += `<p class="heading">${esc(UI.panel_heading)}</p><p class="req-note">${esc(UI.required_note)}</p>`;
      const svc = SERVICES.find(s => s.key === P.service);
      html += `<div class="field"><div class="outlined" data-pick="service"><span class="float">${esc(UI.select_label)}</span>
        <span class="val">${esc(svc ? svc.title : UI.select_placeholder)}</span>
        ${svc ? '<span class="clear" data-clear="1">✕</span>' : '<span class="caret"></span>'}</div></div>`;
    } else {
      html += `<p class="req-note">${esc(UI.required_note)}</p>`;
    }
    if (P.errors._) html += `<div class="gen-error">${esc(P.errors._)}</div>`;
    if (P.service) visibleFields().forEach(f => { html += fieldHTML(f); });
    body.innerHTML = html;
    bindPanel(body);
    updateConfirm();
  }
  function errFor(f) {
    if (P.errors[f.id]) return P.errors[f.id];
    if (["radio", "dropdown"].includes(f.type) && f.required !== false && !P.values[f.id] && P.screen === "main") return UI.select_option;
    return P.touched[f.id] ? fieldError(f) : null;
  }
  function fieldHTML(f) {
    const err = errFor(f);
    const opt = f.required === false ? ` <small>(${esc(UI.optional)})</small>` : "";
    const label = f.label ? `<div class="flabel">${esc(f.label)}${opt}</div>` : "";
    const v = P.values[f.id] ?? "";
    let inner = "";
    switch (f.type) {
      case "info":
        return `<div class="info-card">${fmt(f.text)}</div>`;
      case "radio":
        inner = (err && !P.values[f.id] ? `<div class="ferr">${esc(err)}</div>` : "") +
          f.options.map(o => `<div class="opt ${v === o.id ? "sel" : ""}" data-radio="${esc(f.id)}" data-val="${esc(o.id)}">
            <div class="ot">${esc(o.title)}${o.description ? `<small>${esc(o.description)}</small>` : ""}</div><span class="radio"></span></div>`).join("");
        if (err && P.values[f.id]) inner += `<div class="ferr below">${esc(err)}</div>`;
        return `<div class="field ${err && P.values[f.id] ? "invalid" : ""}" data-field="${esc(f.id)}">${label}${inner}</div>`;
      case "dropdown": {
        const sel = f.options.find(o => o.id === v);
        inner = `<div class="outlined" data-pick="${esc(f.id)}"><span class="val">${esc(sel ? sel.title : UI.choose)}</span><span class="caret"></span></div>`;
        break;
      }
      case "textarea":
        inner = `<textarea class="inp" data-input="${esc(f.id)}" placeholder="${esc(f.placeholder || "")}" maxlength="${f.max_len || 500}">${esc(v)}</textarea>`;
        break;
      case "date":
        inner = `<input class="inp" type="date" data-input="${esc(f.id)}" value="${esc(v)}" min="${esc(f.min_date || "")}" max="${esc(f.max_date || "")}">`;
        break;
      case "number":
        inner = `<input class="inp" type="text" inputmode="numeric" data-input="${esc(f.id)}" value="${esc(v)}" placeholder="${esc(f.placeholder || "")}">`;
        break;
      default:
        inner = `<input class="inp" type="text" ${f.input_mode ? `inputmode="${esc(f.input_mode)}"` : ""} data-input="${esc(f.id)}" value="${esc(v)}" placeholder="${esc(f.placeholder || f.label)}" autocomplete="off">`;
    }
    const help = f.helper ? `<div class="fhelp">${esc(f.helper)}</div>` : "";
    return `<div class="field ${err ? "invalid" : ""}" data-field="${esc(f.id)}">${label}${inner}${err ? `<div class="ferr below">${esc(err)}</div>` : help}</div>`;
  }
  function bindPanel(body) {
    body.querySelectorAll("[data-radio]").forEach(el => el.onclick = () => {
      P.values[el.dataset.radio] = el.dataset.val;
      delete P.errors[el.dataset.radio]; delete P.errors._;
      renderPanel();
    });
    body.querySelectorAll("[data-pick]").forEach(el => el.onclick = e => {
      if (e.target.dataset.clear) { Object.assign(P, { service: null, fields: [], values: {}, errors: {}, touched: {} }); return renderPanel(); }
      P.list = { kind: el.dataset.pick === "service" ? "service" : "field", id: el.dataset.pick, q: "" };
      renderPanel();
    });
    body.querySelectorAll("[data-input]").forEach(el => {
      const id = el.dataset.input;
      el.oninput = () => { P.values[id] = el.value; delete P.errors[id]; updateConfirm(); };
      el.onchange = el.oninput;
      el.onblur = () => {
        P.touched[id] = true;
        const f = P.fields.find(x => x.id === id);
        const wrap = el.closest(".field");
        const err = P.errors[id] || fieldError(f);
        wrap.classList.toggle("invalid", !!err);
        let e = $(".ferr", wrap), h = $(".fhelp", wrap);
        if (err) { if (!e) { e = document.createElement("div"); e.className = "ferr below"; wrap.appendChild(e); } e.textContent = err; if (h) h.hidden = true; }
        else { if (e) e.remove(); if (h) h.hidden = false; }
      };
    });
  }
  function updateConfirm() {
    const c = $("#confirm");
    c.textContent = P.submit || UI.confirm;
    c.disabled = !formValid();
  }
  function renderList(body) {
    const isSvc = P.list.kind === "service";
    const field = isSvc ? null : P.fields.find(f => f.id === P.list.id);
    $("#panelTitle").textContent = isSvc ? UI.select_label : field.label;
    const items = isSvc
      ? SERVICES.map(s => ({ id: s.key, title: s.title, sub: s.subtitle, icon: s.icon }))
      : field.options.map(o => ({ id: o.id, title: o.title, sub: o.description }));
    const current = isSvc ? P.service : P.values[field.id];
    const q = (P.list.q || "").toLowerCase();
    const shown = items.filter(i => !q || (i.title + " " + (i.sub || "")).toLowerCase().includes(q));
    let html = `<div class="list-search">${ICON.search}<input id="listQ" placeholder="${esc(UI.search)}" value="${esc(P.list.q || "")}"></div>`;
    if (isSvc) html += `<div class="li ${current ? "" : "sel"}" data-li=""><div class="tile ph">${ICON.list}</div><div class="lt"><b>${esc(UI.select_placeholder)}</b></div>${current ? "" : '<span class="tickmark">✓</span>'}</div>`;
    html += shown.map(i => `<div class="li ${i.id === current ? "sel" : ""}" data-li="${esc(i.id)}">
      ${isSvc ? `<div class="tile">${SVC_ICON[i.icon] || ICON.list}</div>` : ""}<div class="lt"><b>${esc(i.title)}</b>${i.sub ? `<small>${esc(i.sub)}</small>` : ""}</div>
      ${i.id === current ? '<span class="tickmark">✓</span>' : ""}</div>`).join("");
    body.innerHTML = html;
    $("#confirm").disabled = true;
    const qi = $("#listQ");
    qi.oninput = () => { P.list.q = qi.value; renderList(body); const n = $("#listQ"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); };
    body.querySelectorAll("[data-li]").forEach(el => el.onclick = () => {
      const id = el.dataset.li;
      if (isSvc) { if (!id) { Object.assign(P, { service: null, fields: [], values: {}, errors: {}, list: null }); return renderPanel(); } return selectService(id); }
      P.values[field.id] = id; delete P.errors[field.id]; P.list = null; renderPanel();
    });
  }
  async function submitPanel() {
    if (!P || !P.service) return;
    const vis = visibleFields();
    vis.forEach(f => { P.touched[f.id] = true; });
    if (!formValid()) { renderPanel(); return; }
    const values = {};
    vis.forEach(f => { if (f.type !== "info" && P.values[f.id] !== undefined) values[f.id] = P.values[f.id]; });
    const c = $("#confirm"); c.classList.add("busy"); c.disabled = true;
    try {
      const res = await api("/api/panel/submit", { service: P.service, screen: P.screen, values });
      c.classList.remove("busy");
      if (res.errors) {
        P.errors = res.errors; renderPanel();
        const first = $(".field.invalid, .gen-error, .ferr", $("#panelBody"));
        if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      if (res.panel) {
        const snapshot = JSON.parse(JSON.stringify(Object.assign({}, P, { stack: [] })));
        P = Object.assign({ values: {}, errors: {}, touched: {}, list: null }, res.panel, { stack: P.stack.concat([snapshot]) });
        renderPanel(); $("#panelBody").scrollTop = 0;
        return;
      }
      closePanel();
      if (res.inbound) render(res.inbound, false);
      markRead();
      await showBot(res.messages);
    } catch (e) {
      c.classList.remove("busy"); updateConfirm();
      toast(UI.network_error || "Connection problem. Tap to retry.", submitPanel);
    }
  }

  // ---------------------------------------------------------------- payment sheet
  const METHODS = [
    ["UPI - PhonePe", "Pe", "#5f259f"], ["UPI - Google Pay", "G", "#1a73e8"], ["UPI - BHIM", "B", "#e65100"],
    ["Debit / Credit Card", "C", "#455a64"], ["Net Banking", "NB", "#2e7d32"],
  ];
  async function openPay(pid, btn) {
    let info;
    try { info = (await api("/api/payment/info", { payment_id: pid })).payment; } catch (e) { return toast(UI.network_error); }
    if (!info || info.status === "paid") return doPay(pid, "UPI", btn, true);
    let method = METHODS[0][0];
    const body = $("#payBody");
    const amt = "₹" + Number(info.amount).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    body.innerHTML = `<div class="pay-amt"><small>${esc(UI.pay_title)}</small><b>${amt}</b><span>${esc(info.purpose)}</span></div>
      <div class="pay-label">${esc(UI.pay_choose)}</div>
      ${METHODS.map((m, i) => `<div class="pm ${i === 0 ? "sel" : ""}" data-m="${esc(m[0])}"><span class="logo" style="background:${m[2]}">${m[1]}</span><span class="nm">${esc(m[0])}</span><span class="radio"></span></div>`).join("")}
      <button class="pay-btn" id="payGo">${esc(UI.pay_now)} ${amt}</button>
      <div class="secure">Secured by Karnataka One · Demonstration, no money is charged</div>`;
    body.querySelectorAll(".pm").forEach(el => el.onclick = () => {
      body.querySelectorAll(".pm").forEach(x => x.classList.remove("sel")); el.classList.add("sel"); method = el.dataset.m;
    });
    $("#payGo").onclick = () => doPay(pid, method, btn, false, amt);
    $("#panel").hidden = true;
    $("#payModal").hidden = false;
  }
  async function doPay(pid, method, btn, silent, amt) {
    const body = $("#payBody");
    if (!silent) body.innerHTML = `<div class="pay-state"><div class="spinner"></div><b>${esc(UI.pay_processing)}</b><span>${esc(method)}</span></div>`;
    try {
      const [res] = await Promise.all([api("/api/payment/pay", { payment_id: pid, method }), sleep(silent ? 0 : 1400)]);
      if (!silent) {
        body.innerHTML = `<div class="pay-state"><div class="ok">✓</div><b>${esc(UI.pay_success)}</b><span>${esc(amt || "")}</span></div>`;
        await sleep(900);
        $("#payModal").hidden = true;
      }
      if (btn) { btn.classList.add("done"); btn.querySelector("span").textContent = UI.pay_success || "Paid"; }
      await showBot(res.messages);
    } catch (e) {
      body.innerHTML = `<div class="pay-state"><b>${esc(UI.network_error)}</b><button class="pay-btn" id="payRetry">Retry</button></div>`;
      $("#payRetry").onclick = () => doPay(pid, method, btn, false, amt);
    }
  }

  // ---------------------------------------------------------------- service rail
  function renderServiceRail() {
    const el = $("#svcList");
    if (!el || !SERVICES.length) return;
    el.innerHTML = SERVICES.map(s => `<div class="svc" data-svc="${esc(s.key)}"><div class="tile">${SVC_ICON[s.icon] || ICON.list}</div><div><b>${esc(s.title)}</b><small>${esc(s.subtitle)}</small><small class="dept">${esc(s.dept || "")}</small></div></div>`).join("");
    el.querySelectorAll(".svc").forEach(d => d.onclick = () => openPanel(d.dataset.svc));
  }

  // ---------------------------------------------------------------- behind the chat
  const STEPS = [
    ["Message received", "WhatsApp Business API webhook"],
    ["Language and intent", "command / keyword routing"],
    ["Form validation", "field rules, formats, date windows"],
    ["Department service", "service logic"],
    ["Records and payment", "state saved, payment intent"],
    ["Document issued", "PDF generated"],
    ["Reply delivered", "messages sent back"],
  ];
  function renderPipeline(state) {
    const ol = $("#pipeline");
    ol.innerHTML = STEPS.map((s, i) => {
      const st = state[i] || {};
      return `<li class="${st.cls || ""}"><span class="n">${st.cls === "done" ? "✓" : i + 1}</span><div><b>${esc(s[0])}</b><small>${esc(st.detail || s[1])}</small></div></li>`;
    }).join("");
  }
  renderPipeline([]);
  async function showTrace(id) {
    $("#traceId").textContent = "#" + id;
    $("#traceLink").href = "/logs?trace=" + id;
    try {
      const r = await fetch("/api/logs?trace=" + id);
      const { trace, calls, messages } = await r.json();
      if (!trace) return;
      const has = re => calls.filter(c => re.test(c.module + "." + c.func));
      const fnOf = cs => cs.length ? cs[0].module + "." + cs[0].func + " · " + (cs[0].duration_ms || 0).toFixed(1) + " ms" : "";
      const nlu = has(/^nlu\./), val = has(/validate_all|flowkit/), svc = has(/^services\.(?!base)/), rec = has(/rec_put|payments\./), doc = has(/docs\.create/);
      const out = messages.filter(m => m.dir === "out").length;
      const state = [
        { cls: "done", detail: trace.kind + " · " + (trace.duration_ms || 0).toFixed(1) + " ms" },
        nlu.length ? { cls: "done", detail: fnOf(nlu) } : (trace.kind.startsWith("panel") ? { cls: "done", detail: "selected from the service menu" } : { cls: "skip" }),
        val.length ? { cls: "done", detail: fnOf(val) }
          : (/panel\/(open|service)/.test(trace.kind) ? { cls: "active", detail: "waiting for the citizen to fill the form" } : { cls: "skip" }),
        svc.length ? { cls: "done", detail: fnOf(svc) } : { cls: "skip" },
        rec.length ? { cls: "done", detail: fnOf(rec) } : { cls: "skip" },
        doc.length ? { cls: "done", detail: fnOf(doc) } : { cls: "skip" },
        out ? { cls: "done", detail: out + (out === 1 ? " message" : " messages") + " · trace #" + id } : { cls: "active", detail: "awaiting form input" },
      ];
      renderPipeline(state);
    } catch (e) { /* log panel is informational */ }
  }

  // ---------------------------------------------------------------- wiring
  input.addEventListener("input", () => sendBtn.classList.toggle("ready", !!input.value.trim()));
  input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); const t = input.value; input.value = ""; sendBtn.classList.remove("ready"); sendText(t); } });
  sendBtn.onclick = () => { const t = input.value; input.value = ""; sendBtn.classList.remove("ready"); sendText(t); input.focus(); };
  $("#sayHi button").onclick = () => sendText("Hi");
  $("#confirm").onclick = submitPanel;
  $("#panelClose").onclick = closePanel;
  $("#panelBack").onclick = () => {
    if (!P) return;
    if (P.list) { P.list = null; return renderPanel(); }
    if (P.stack.length) { const stack = P.stack.slice(0, -1); P = Object.assign(P.stack[P.stack.length - 1], { stack }); renderPanel(); }
  };
  $("#payClose").onclick = () => { $("#payModal").hidden = true; };
  $("#langs").onclick = e => { const b = e.target.closest("button"); if (b && b.dataset.lang !== LANG) sendText(b.dataset.lang.toUpperCase()); };
  $("#resetBtn").onclick = () => { SID = newSid(); store.set("nm_session", SID); stream.innerHTML = ""; lastSide = null; closePanel(); $("#payModal").hidden = true; renderPipeline([]); $("#traceId").textContent = "—"; boot(); };
  document.body.classList.toggle("hide-trace", new URLSearchParams(location.search).get("trace") === "0");

  const splashStart = Date.now();
  function hideSplash() {
    const s = $("#splash");
    if (!s || s.classList.contains("done")) return;
    setTimeout(() => s.classList.add("done"), Math.max(0, 1600 - (Date.now() - splashStart)));
  }
  setTimeout(hideSplash, 6000);   // never block the demo, even if the server is slow

  async function boot() {
    try {
      const res = await api("/api/session", {});
      const open = await api("/api/panel/open", {});
      SERVICES = open.panel.services || [];
      renderServiceRail();
      stream.innerHTML = ""; lastSide = null;
      (res.history || []).forEach(m => render(m, false));
      $("#sayHi").hidden = (res.history || []).length > 0;
      scrollDown();
    } catch (e) { toast("Server not reachable. Start it with: python run.py", boot, 8000); }
    hideSplash();
    input.focus();
  }
  boot();
})();
