"use strict";

const DAYS_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const OFFERS_KEY = "slotex.offers";
let SLOTS = [], REG = {}, SIM_AIRPORTS = new Set();

function hashStr(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); }

// Deterministic simulated price (USD thousands / week). Peak hours + Level 3 +
// seats + operating days drive it, with a stable per-flight jitter.
function priceFor(s) {
  const seats = +s.seats || 120;
  const hour = parseInt((s.time || "12:00").slice(0, 2), 10);
  const peak = (hour >= 6 && hour <= 9) || (hour >= 17 && hour <= 20) ? 1.8
             : (hour >= 10 && hour <= 16 ? 1.2 : 0.7);
  const level = (REG[s.airport] && REG[s.airport].level === "3") ? 1.5 : 1.0;
  const daysCount = s.days ? s.days.split(",").length : 1;
  const base = 40 + seats * 1.1;
  let p = base * peak * level * (0.6 + 0.09 * daysCount);
  p *= 0.9 + (hashStr(s.airport + s.carrier + s.flight_no + s.time) % 20) / 100;
  return Math.max(5, Math.round(p / 5) * 5);
}
const fmtPrice = (k) => "$" + k.toLocaleString() + "k";

function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
const $ = (id) => document.getElementById(id);

function airportsInSlots() {
  const set = new Map();
  for (const s of SLOTS) if (!set.has(s.airport)) set.set(s.airport, (REG[s.airport] || {}).city || "");
  return [...set.entries()].sort();
}

// airports with listings, grouped by market (Brazil / US / Europe / …)
function airportsGrouped() {
  const info = new Map();
  for (const s of SLOTS) if (!info.has(s.airport))
    info.set(s.airport, { market: s.market || "Other", city: (REG[s.airport] || {}).city || "" });
  const groups = {};
  for (const [iata, i] of info) (groups[i.market] ||= []).push([iata, i.city]);
  for (const k in groups) groups[k].sort();
  return groups;
}

// Coordinator fields in the WASG data can hold several emails / newlines and long
// URLs — tidy them for display.
function cleanEmail(v) {
  if (!v) return "";
  return (v.split(/[\n;,]+/).map((x) => x.trim()).find((x) => x.includes("@"))) || "";
}
function cleanSite(v) {
  if (!v) return "";
  let u = v.trim().split(/\s+/)[0];
  if (!u) return "";
  if (!/^https?:\/\//i.test(u)) u = "https://" + u.replace(/^\/+/, "");
  try { new URL(u); return u; } catch { return ""; }
}

function currentFilters() {
  return {
    airport: $("f-airport").value,
    dir: $("f-dir").value,
    sort: $("f-sort").value,
    q: $("f-search").value.trim().toLowerCase(),
  };
}

function applyFilters() {
  const f = currentFilters();
  let rows = SLOTS.filter((s) =>
    (!f.airport || s.airport === f.airport) &&
    (!f.dir || s.direction === f.dir) &&
    (!f.q || (s.carrier + " " + s.flight_no + " " + s.orig_dest).toLowerCase().includes(f.q)));
  rows = rows.map((s) => ({ ...s, price: priceFor(s) }));
  const cmp = {
    "price-desc": (a, b) => b.price - a.price,
    "price-asc": (a, b) => a.price - b.price,
    "time-asc": (a, b) => (a.time || "").localeCompare(b.time || ""),
  }[f.sort];
  rows.sort(cmp);
  renderAirportInfo(f.airport);
  renderListings(rows);
}

function renderAirportInfo(iata) {
  const box = $("airport-info");
  const r = iata && REG[iata];
  if (!r) { box.hidden = true; return; }
  box.hidden = false;
  const lvl = r.level === "3" ? '<span class="badge l3">LEVEL 3 · coordinated</span>'
            : r.level === "2" ? '<span class="badge l2">LEVEL 2 · facilitated</span>' : "";
  const sim = SIM_AIRPORTS.has(iata) ? '<span class="badge sim">SIMULATED listings</span>' : "";
  const email = cleanEmail(r.coordinator), site = cleanSite(r.website);
  box.innerHTML =
    `<span class="big">${iata}</span> ${lvl} ${sim}
     <span>${r.city || ""}${r.country ? ", " + r.country : ""}</span>
     ${email ? `<span>Coordinator: <b>${email}</b></span>` : ""}
     ${site ? `<span><a href="${site}" target="_blank" rel="noopener">Coordinator site ↗</a></span>` : ""}`;
}

function renderListings(rows) {
  const wrap = $("listings"); wrap.innerHTML = "";
  $("count").textContent = rows.length.toLocaleString() + " listings";
  const CAP = 300;
  for (const s of rows.slice(0, CAP)) {
    const card = el("div", "card");
    const route = s.orig_dest ? (s.direction === "arr" ? "from " : "to ") + s.orig_dest : "";
    card.innerHTML =
      `<div class="top"><span class="apt">${s.airport}${s.sim ? ' <span class="sim">SIM</span>' : ""}</span><span class="dir">${s.direction}</span></div>
       <div class="time">${s.time || "--:--"}</div>
       <div class="flight">${s.carrier} ${s.flight_no} · ${route}</div>
       <div class="days">${s.days || ""}</div>
       <div class="meta"><span>${s.aircraft || "?"}</span><span>${s.seats || "?"} seats</span><span>${s.service || ""}</span></div>
       <div class="foot"><span class="price">${fmtPrice(s.price)} <small>/wk</small></span></div>`;
    const btn = el("button", "trade", "Trade");
    btn.onclick = () => openModal(s);
    card.querySelector(".foot").appendChild(btn);
    wrap.appendChild(card);
  }
  if (rows.length > CAP) wrap.appendChild(el("div", "empty", `+${rows.length - CAP} more — refine filters to see them`));
  if (!rows.length) wrap.appendChild(el("div", "empty", "No listings match your filters."));
}

function renderStats() {
  const prices = SLOTS.map(priceFor);
  const avg = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
  const l3 = new Set(SLOTS.filter((s) => (REG[s.airport] || {}).level === "3").map((s) => s.airport));
  $("stats").innerHTML =
    `<div><b>${SLOTS.length.toLocaleString()}</b> listings</div>
     <div><b>${airportsInSlots().length}</b> airports</div>
     <div><b>${l3.size}</b> Level 3</div>
     <div><b>${fmtPrice(avg)}</b> avg/wk</div>`;
}

// ---- Trade modal + offers (localStorage) ----
function openModal(s) {
  const body = $("modal-body");
  const price = priceFor(s);
  body.innerHTML =
    `<h2>${s.airport} · ${s.time}</h2>
     <div class="sub">${s.carrier} ${s.flight_no} — mock landing-slot listing</div>
     <div class="row"><span>Direction</span><span>${s.direction}</span></div>
     <div class="row"><span>Days</span><span>${s.days || "-"}</span></div>
     <div class="row"><span>Aircraft / seats</span><span>${s.aircraft || "?"} · ${s.seats || "?"}</span></div>
     <div class="row"><span>Route</span><span>${s.orig_dest || "-"}</span></div>
     <div class="row"><span>Ask price</span><span>${fmtPrice(price)} / wk</span></div>
     <label>Your offer (USD thousands / week)</label>
     <input id="offer-amt" type="number" value="${price}" min="1">
     <button class="submit" id="offer-submit">Submit offer (demo)</button>`;
  $("offer-submit").onclick = () => {
    const amt = Math.max(1, +$("offer-amt").value || price);
    addOffer({ airport: s.airport, time: s.time, carrier: s.carrier, flight_no: s.flight_no, amt });
    closeModal();
    toast(`Offer of ${fmtPrice(amt)} submitted for ${s.airport} ${s.time} (demo)`);
  };
  $("modal").hidden = false;
}
const closeModal = () => { $("modal").hidden = true; };

function getOffers() { try { return JSON.parse(localStorage.getItem(OFFERS_KEY)) || []; } catch { return []; } }
function addOffer(o) { const l = getOffers(); l.unshift(o); localStorage.setItem(OFFERS_KEY, JSON.stringify(l)); renderOffers(); }
function renderOffers() {
  const l = getOffers(), box = $("offers-list");
  box.innerHTML = "";
  if (!l.length) { box.appendChild(el("div", "empty", "No offers yet. Click Trade on a listing.")); return; }
  for (const o of l) {
    box.appendChild(el("div", "offer",
      `<div class="o-top"><span>${o.airport} · ${o.time}</span><span class="o-price">${fmtPrice(o.amt)}</span></div>
       <div class="flight">${o.carrier} ${o.flight_no}</div>`));
  }
}

let toastT;
function toast(msg) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => t.hidden = true, 2600); }

async function init() {
  [REG, SLOTS] = await Promise.all([
    fetch("data/registry.json").then((r) => r.json()).then((a) => Object.fromEntries(a.map((x) => [x.iata, x]))),
    fetch("data/slots.json").then((r) => r.json()),
  ]);
  for (const k in REG) REG[k].level = String(REG[k].level ?? "");   // gspread may hand back numbers
  SIM_AIRPORTS = new Set(SLOTS.filter((s) => s.sim).map((s) => s.airport));
  const sel = $("f-airport");
  sel.appendChild(new Option("All airports", ""));
  const groups = airportsGrouped();
  const order = ["Europe", "US", "Brazil"];
  for (const mk of [...order, ...Object.keys(groups).filter((k) => !order.includes(k))]) {
    if (!groups[mk]) continue;
    const og = document.createElement("optgroup");
    og.label = mk + (mk === "Brazil" ? " (real data)" : " (simulated)");
    for (const [iata, city] of groups[mk]) og.appendChild(new Option(`${iata} — ${city}`, iata));
    sel.appendChild(og);
  }
  sel.value = REG.LHR ? "LHR" : airportsInSlots()[0][0];   // default to a familiar hub
  for (const id of ["f-airport", "f-dir", "f-sort", "f-search"]) $(id).addEventListener("input", applyFilters);
  $("modal-close").onclick = closeModal;
  $("modal").addEventListener("click", (e) => { if (e.target === $("modal")) closeModal(); });
  $("clear-offers").onclick = () => { localStorage.removeItem(OFFERS_KEY); renderOffers(); };
  if (localStorage.getItem("slotex.banner") === "off") $("demo-banner").hidden = true;
  $("banner-x").onclick = () => { $("demo-banner").hidden = true; localStorage.setItem("slotex.banner", "off"); };
  $("asof").textContent = "sampled snapshot · " + SLOTS.length + " listings";
  renderStats(); renderOffers(); applyFilters();
}
init();
