"use strict";

const MODES = [
  { id: "wave", name: "Wave", desc: "Rainbow flowing across",
    swatch: "linear-gradient(90deg,#f00,#ff0,#0f0,#0ff,#00f,#f0f,#f00)" },
  { id: "spectrum", name: "Spectrum", desc: "Whole board cycles colors",
    swatch: "linear-gradient(90deg,#ff3d77,#7a5cff,#22d3ee,#34d399)" },
  { id: "breathing", name: "Breathing", desc: "Fades in and out",
    swatch: "radial-gradient(circle,#7a5cff 0%,#1a1440 75%)" },
  { id: "static", name: "Solid", desc: "One color everywhere",
    swatch: "#ff2a55" },
  { id: "stack", name: "Color loading", desc: "Colors fill the board",
    swatch: "linear-gradient(90deg,#f00 0 33%,#0f0 33% 66%,#00f 66%)" },
  { id: "custom", name: "Custom", desc: "Your per-key design",
    swatch: "conic-gradient(#ff3d77,#fbbf24,#34d399,#22d3ee,#7a5cff,#ff3d77)" },
];
// Wave / color loading directions as stored in the keyboard (0-3).
const DIRECTIONS = [["→", "Left to right"], ["←", "Right to left"], ["↓", "Top to bottom"], ["↑", "Bottom to top"]];
const SWATCHES = ["#ff0000", "#ff6a00", "#ffd400", "#00ff4c", "#00e5ff", "#0040ff", "#7a00ff", "#ff00c8", "#ffffff", "#000000"];

let S, L, PATTERNS, LIMITS;
let dirty = false;
let tool = "brush";
let keyEls = [];
const $ = (sel) => document.querySelector(sel);

const profile = () => S.profiles[S.active];
const fx = () => profile().effects;

// ---------- helpers ----------
function hexToRgb(h) { h = h.replace("#", ""); return [0, 2, 4].map((i) => parseInt(h.substr(i, 2), 16)); }
function rgbToHex([r, g, b]) { return "#" + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join(""); }
function hsv(h, s = 1, v = 1) {
  h = ((h % 1) + 1) % 1; const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  const [r, g, b] = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6];
  return [r * 255, g * 255, b * 255];
}
function scale(c, k) { return c.map((v) => v * k); }
function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  children.forEach((c) => e.append(c));
  return e;
}
let toastTimer;
function toast(msg, kind = "") {
  const t = $("#toast"); t.textContent = msg; t.className = `toast show ${kind}`;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.className = "toast"), 3200);
}

// ---------- persistence ----------
let saveTimer;
function changed({ markDirty = true } = {}) {
  if (markDirty) setDirty(true);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => window.pywebview.api.save_settings(S), 400);
  renderProfiles();
}
function setDirty(v) { dirty = v; $("#dirty").hidden = !v; }

async function applyToKeyboard() {
  const btn = $("#btn-apply"); btn.disabled = true; btn.textContent = "Applying…";
  clearTimeout(saveTimer);
  try {
    const r = await window.pywebview.api.apply(S);
    if (r.ok) { setDirty(false); toast("Saved to the keyboard", "ok"); } else toast(r.message, "err");
  } catch (e) { toast(String(e), "err"); }
  btn.disabled = false; btn.textContent = "Apply to keyboard";
  refreshDevice();
}

async function refreshDevice() {
  const d = await window.pywebview.api.device_status();
  $("#device").classList.toggle("on", d.connected);
  $("#device-text").textContent = d.connected ? `Keyboard connected · FW ${d.firmware}` : "Keyboard not found";
}

// ---------- keyboard preview ----------
function buildKeyboard() {
  const kb = $("#keyboard"); kb.innerHTML = ""; keyEls = [];
  L.keys.forEach((k, i) => {
    const glow = el("div", { class: "glow" }), cap = el("div", { class: "cap" });
    const node = el("div", { class: "key", "data-i": i }, cap, glow, el("span", { class: "lbl", text: k.label }));
    kb.append(node); keyEls.push({ node, cap, glow, k });
  });
  layoutKeyboard();
}
function layoutKeyboard() {
  if (!L) return;
  const kb = $("#keyboard"); const u = kb.clientWidth / L.width; const gap = Math.max(2, u * 0.06);
  kb.style.height = `${L.height * u}px`;
  keyEls.forEach(({ node, k }) => {
    Object.assign(node.style, { left: `${k.x * u}px`, top: `${k.y * u}px`,
      width: `${k.w * u - gap}px`, height: `${k.h * u - gap}px` });
  });
}
window.addEventListener("resize", layoutKeyboard);

// Approximate animation of each built-in effect, for the on-screen preview.
function frameColors(t) {
  const p = profile(), f = p.effects, n = keyEls.length;
  const W = L.width, H = L.height;
  const pos = (k) => [(k.x + k.w / 2) / W, (k.y + k.h / 2) / H];
  const out = new Array(n);
  const period = (s) => 9 / Math.max(1, s.speed);
  switch (p.mode) {
    case "static": {
      const c = scale(hexToRgb(f.static.color), f.static.brightness / 5); out.fill(c); break;
    }
    case "spectrum": {
      const c = scale(hsv(t / period(f.spectrum)), f.spectrum.brightness / 5); out.fill(c); break;
    }
    case "breathing": {
      const per = period(f.breathing), cycle = Math.floor(t / per), ph = (t / per) % 1;
      const col = f.breathing.loop ? f.breathing.colors[cycle % 5] : f.breathing.colors[0];
      const k = (0.5 - 0.5 * Math.cos(ph * 2 * Math.PI)) * f.breathing.brightness / 5;
      out.fill(scale(hexToRgb(col), k)); break;
    }
    case "wave": {
      const w = f.wave, d = w.direction, b = w.brightness / 5;
      keyEls.forEach(({ k }, i) => {
        const [x, y] = pos(k); const s = [x, 1 - x, y, 1 - y][d] ?? x;
        out[i] = scale(hsv(s * 0.9 - t / period(w)), b);
      });
      break;
    }
    case "stack": {
      const st = f.stack, per = period(st) * 0.8, cycle = Math.floor(t / per), ph = (t / per) % 1;
      const cur = hexToRgb(st.colors[st.loop ? cycle % 5 : 0]);
      const prev = st.loop ? hexToRgb(st.colors[(cycle + 4) % 5]) : [0, 0, 0];
      keyEls.forEach(({ k }, i) => {
        const [x, y] = pos(k); const s = [x, 1 - x, y, 1 - y][st.direction] ?? x;
        out[i] = scale(s <= ph ? cur : prev, st.brightness / 5);
      });
      break;
    }
    default: {
      const c = f.custom, b = c.brightness / 5;
      keyEls.forEach(({ k }, i) => { out[i] = scale(hexToRgb(c.keys[k.led] || "#000000"), b); });
    }
  }
  return out;
}
let lastPaint = 0;
function animate(ts) {
  if (ts - lastPaint > 33) {
    lastPaint = ts;
    const colors = frameColors(ts / 1000);
    keyEls.forEach(({ cap, glow, node }, i) => {
      const [r, g, b] = colors[i].map(Math.round), lum = (r + g + b) / 765;
      cap.style.background = `radial-gradient(circle at 50% 55%, rgb(${r},${g},${b}) 0%, rgba(${r},${g},${b},.55) 80%), #1b1f29`;
      glow.style.background = `rgba(${r},${g},${b},${0.15 * lum})`;
      node.style.boxShadow = lum > 0.02 ? `0 0 ${6 + 10 * lum}px rgba(${r},${g},${b},${0.35 + 0.3 * lum}), inset 0 -3px 0 rgba(0,0,0,.45)` : "";
    });
  }
  requestAnimationFrame(animate);
}

// ---------- profiles sidebar ----------
function chipStyle(p) {
  const m = MODES.find((x) => x.id === p.mode);
  if (p.mode === "static") return p.effects.static.color;
  if (p.mode === "breathing" || p.mode === "stack") return `linear-gradient(135deg,${p.effects[p.mode].colors.join(",")})`;
  return m.swatch;
}
function renderProfiles() {
  const ul = $("#profiles"); ul.innerHTML = "";
  S.profiles.forEach((p, i) => {
    const chip = el("span", { class: "chip" }); chip.style.background = chipStyle(p);
    const li = el("li", { class: i === S.active ? "active" : "", onclick: () => selectProfile(i) },
      chip, el("span", { class: "pname", text: p.name }));
    ul.append(li);
  });
}
async function selectProfile(i) {
  if (i === S.active) return;
  S.active = i; renderAll(); changed();
  await applyToKeyboard();
}

// ---------- effects tab ----------
function renderModes() {
  const box = $("#modes"); box.innerHTML = "";
  MODES.forEach((m) => {
    const sw = el("div", { class: "swatch" }); sw.style.background = m.swatch;
    box.append(el("button", { class: `mode ${profile().mode === m.id ? "on" : ""}`,
      onclick: () => { profile().mode = m.id; changed(); renderModes(); renderSettings(); } },
      sw, el("b", { text: m.name }), el("small", { text: m.desc })));
  });
}
function slider(label, obj, key, min, max) {
  const val = el("b", { text: obj[key] });
  const input = el("input", { type: "range", min, max, step: 1 });
  input.value = obj[key];
  input.addEventListener("input", () => { obj[key] = +input.value; val.textContent = input.value; changed(); });
  const lab = el("label", { class: "field-label" }); lab.append(label, val);
  return el("div", { class: "group" }, lab, input);
}
function colorPicker(obj, key, idx) {
  const input = el("input", { type: "color" });
  input.value = idx === undefined ? obj[key] : obj[key][idx];
  input.addEventListener("input", () => {
    if (idx === undefined) obj[key] = input.value; else obj[key][idx] = input.value;
    changed();
  });
  return input;
}
function directionPicker(obj) {
  const seg = el("div", { class: "seg" });
  DIRECTIONS.forEach(([arrow, title], d) => {
    seg.append(el("button", { class: obj.direction === d ? "on" : "", title, text: arrow,
      onclick: () => { obj.direction = d; changed(); renderSettings(); } }));
  });
  return el("div", { class: "group" }, el("label", { class: "field-label", text: "Direction" }), seg);
}
function loopToggle(obj) {
  const cb = el("input", { type: "checkbox" }); cb.checked = !!obj.loop;
  cb.addEventListener("change", () => { obj.loop = cb.checked; changed(); });
  const lab = el("label", { class: "toggle inline-toggle" }, cb, el("span", { class: "switch" }),
    el("span", { text: "Cycle through all 5 colors" }));
  return el("div", { class: "group" }, el("label", { class: "field-label", text: "Colors" }), lab);
}
function renderSettings() {
  const box = $("#mode-settings"); box.innerHTML = "";
  const p = profile(), f = p.effects, [smin, smax] = LIMITS.speed, bmax = LIMITS.brightness;
  const colorsGroup = (obj) => {
    const row = el("div", { class: "colors" });
    obj.colors.forEach((_, i) => row.append(colorPicker(obj, "colors", i)));
    return el("div", { class: "group" }, el("label", { class: "field-label", text: "Palette" }), row);
  };
  switch (p.mode) {
    case "static":
      box.append(el("div", { class: "group" }, el("label", { class: "field-label", text: "Color" }), colorPicker(f.static, "color")),
        slider("Brightness", f.static, "brightness", 0, bmax));
      break;
    case "breathing":
      box.append(colorsGroup(f.breathing), loopToggle(f.breathing),
        slider("Speed", f.breathing, "speed", smin, smax), slider("Brightness", f.breathing, "brightness", 0, bmax));
      break;
    case "spectrum":
      box.append(slider("Speed", f.spectrum, "speed", smin, smax), slider("Brightness", f.spectrum, "brightness", 0, bmax));
      break;
    case "wave":
      box.append(directionPicker(f.wave), slider("Speed", f.wave, "speed", smin, smax),
        slider("Brightness", f.wave, "brightness", 0, bmax));
      break;
    case "stack":
      box.append(colorsGroup(f.stack), loopToggle(f.stack), directionPicker(f.stack),
        slider("Speed", f.stack, "speed", smin, smax), slider("Brightness", f.stack, "brightness", 0, bmax));
      break;
    default:
      box.append(el("p", { class: "hint", text: "Custom shows your own per-key colors. Paint them in the Paint keys tab or start from a design in Patterns." }),
        slider("Brightness", f.custom, "brightness", 0, bmax));
  }
}

// ---------- paint tab ----------
function paintKey(i) {
  const led = keyEls[i].k.led, c = fx().custom;
  if (tool === "pick") {
    const color = c.keys[led] || "#000000";
    $("#paint-color").value = color; setTool("brush"); toast(`Picked ${color}`); return;
  }
  if (profile().mode !== "custom") { profile().mode = "custom"; renderModes(); renderSettings(); }
  if (tool === "erase") delete c.keys[led]; else c.keys[led] = $("#paint-color").value;
  changed();
}
function setTool(t) {
  tool = t;
  document.querySelectorAll("#paint-tool button").forEach((b) => b.classList.toggle("on", b.dataset.tool === t));
  $("#keyboard").classList.toggle("picking", t === "pick");
}
function setupPaint() {
  const kb = $("#keyboard"); let down = false, last = -1;
  const hit = (e) => { const k = e.target.closest(".key"); return k ? +k.dataset.i : -1; };
  kb.addEventListener("pointerdown", (e) => {
    if (currentTab !== "paint") return;
    down = true; last = hit(e); if (last >= 0) paintKey(last);
  });
  kb.addEventListener("pointermove", (e) => {
    if (!down || tool === "pick") return;
    const el2 = document.elementFromPoint(e.clientX, e.clientY)?.closest(".key");
    const i = el2 ? +el2.dataset.i : -1;
    if (i >= 0 && i !== last) { last = i; paintKey(i); }
  });
  window.addEventListener("pointerup", () => (down = false));
  document.querySelectorAll("#paint-tool button").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
  SWATCHES.forEach((c) => {
    const b = el("button", { title: c, onclick: () => ($("#paint-color").value = c) }); b.style.background = c;
    $("#swatches").append(b);
  });
  $("#paint-fill").addEventListener("click", () => {
    const c = fx().custom, color = $("#paint-color").value;
    L.keys.forEach((k) => (c.keys[k.led] = color)); profile().mode = "custom"; changed(); renderModes(); renderSettings();
  });
  $("#paint-clear").addEventListener("click", () => { fx().custom.keys = {}; changed(); });
  const cb = $("#custom-bright");
  cb.addEventListener("input", () => { fx().custom.brightness = +cb.value; $("#custom-bright-val").textContent = cb.value; changed(); });
  $("#design-save").addEventListener("click", () => {
    const name = $("#design-name").value.trim();
    if (!name) { toast("Give the design a name first", "err"); return; }
    S.designs[name] = { ...fx().custom.keys }; $("#design-name").value = ""; changed({ markDirty: false });
    renderDesigns(); toast(`Saved "${name}"`, "ok");
  });
}
function renderDesigns() {
  const box = $("#design-list"); box.innerHTML = "";
  const names = Object.keys(S.designs);
  if (!names.length) { box.append(el("span", { class: "hint", text: "Saved designs will show up here." })); return; }
  names.forEach((name) => {
    box.append(el("span", { class: "design" }, el("span", { text: name }),
      el("button", { title: "Load", text: "Load", onclick: () => loadKeys(S.designs[name]) }),
      el("button", { title: "Delete", text: "✕", onclick: () => { delete S.designs[name]; changed({ markDirty: false }); renderDesigns(); } })));
  });
}
function loadKeys(keys) {
  fx().custom.keys = { ...keys }; profile().mode = "custom"; changed(); renderModes(); renderSettings();
}

// ---------- patterns tab ----------
function renderPatterns() {
  const grid = $("#pattern-grid"); grid.innerHTML = "";
  for (const [name, keys] of Object.entries(PATTERNS)) {
    const cv = el("canvas", { width: 450, height: 125 });
    const ctx = cv.getContext("2d"), u = 450 / L.width;
    L.keys.forEach((k) => {
      ctx.fillStyle = keys[k.led] || "#000"; ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = 6;
      ctx.beginPath(); ctx.roundRect(k.x * u + 1, k.y * u + 1, k.w * u - 3, k.h * u - 3, 3); ctx.fill();
    });
    grid.append(el("button", { class: "pattern", onclick: () => { loadKeys(keys); toast(`${name} loaded. Click Apply to keyboard to save it.`); } },
      cv, el("b", { text: name })));
  }
}

// ---------- gaming tab ----------
function renderGaming() {
  const g = profile().gaming;
  [["#g-win", "win"], ["#g-alttab", "alt_tab"], ["#g-altf4", "alt_f4"]].forEach(([sel, key]) => {
    const cb = $(sel); cb.checked = !!g[key];
    cb.onchange = () => { g[key] = cb.checked; changed({ markDirty: false }); };
  });
}

// ---------- tabs ----------
let currentTab = "effects";
function setupTabs() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
    currentTab = t.dataset.tab;
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== `tab-${currentTab}`));
    $("#keyboard").classList.toggle("painting", currentTab === "paint");
  }));
}

function renderAll() {
  $("#profile-name").value = profile().name;
  const cb = $("#custom-bright"); cb.max = LIMITS.brightness; cb.value = fx().custom.brightness;
  $("#custom-bright-val").textContent = cb.value;
  renderProfiles(); renderModes(); renderSettings(); renderGaming(); renderDesigns();
}

async function init() {
  const data = await window.pywebview.api.get_init();
  S = data.settings; L = data.layout; PATTERNS = data.patterns; LIMITS = data.limits;
  buildKeyboard(); setupTabs(); setupPaint(); renderPatterns(); renderAll();
  $("#profile-name").addEventListener("input", (e) => { profile().name = e.target.value || `Profile ${S.active + 1}`; changed({ markDirty: false }); });
  $("#btn-apply").addEventListener("click", applyToKeyboard);
  $("#btn-off").addEventListener("click", async () => {
    const r = await window.pywebview.api.lights_off();
    toast(r.ok ? "Lights off. Apply a profile to turn them back on." : r.message, r.ok ? "ok" : "err");
    if (r.ok) setDirty(true);
  });
  requestAnimationFrame(animate);
  refreshDevice(); setInterval(refreshDevice, 5000);
}
window.addEventListener("pywebviewready", init);
