"use strict";
const $ = (id) => document.getElementById(id);
const canvas = $("room"), ctx = canvas.getContext("2d");

const state = {
  world: null, frames: [], summary: null,
  idx: 0, progress: 1, playing: false, last: 0,
  removedAt: new Map(), batteryMax: 70, agents: [],
};
let cell = 48;

const STATUS = {
  clean: "✅ Room is clean!",
  battery_dead: "🔋 Battery died before the room was clean",
  max_steps: "⏱ Step limit reached",
  stuck: "🤷 Agent gave up (nothing it can do)",
};

/* ---------------- API ---------------- */
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const seedValue = () => { const v = $("seed").value.trim(); return v === "" ? null : parseInt(v, 10); };
const simBody = () => ({
  world: state.world, battery: +$("battery").value, max_steps: +$("maxsteps").value, seed: seedValue(),
});

async function newRoom() {
  const q = new URLSearchParams({
    size: $("size").value, dirt: $("dirt").value / 100, obstacles: $("obst").value / 100,
  });
  if (seedValue() !== null) q.set("seed", seedValue());
  state.world = await api("/api/world?" + q);
  resetRun();
}

async function runSimulation() {
  const res = await post("/api/simulate", { ...simBody(), agent: $("agent").value });
  state.frames = res.frames;
  state.summary = res.summary;
  state.idx = 0;
  state.progress = 1;
  state.batteryMax = res.frames[0].battery;
  state.removedAt = new Map();
  res.frames.forEach((f, i) => f.removed && state.removedAt.set(f.removed.join(","), i));
}

/* ---------------- controls ---------------- */
function resetRun() {
  state.frames = []; state.summary = null; state.idx = 0; state.progress = 1; state.playing = false;
  state.batteryMax = +$("battery").value;
  state.removedAt = new Map();
  $("status").textContent = ""; $("compareBox").hidden = true;
  fitCanvas(); showStats(); renderLog();
}

async function play() {
  if (!state.frames.length || state.idx >= state.frames.length - 1) {
    await runSimulation(); $("status").textContent = "";
  }
  state.playing = true;
  advance();
}

async function stepOnce() {
  state.playing = false;
  if (!state.frames.length || state.idx >= state.frames.length - 1) {
    if (state.frames.length) return;
    await runSimulation();
  }
  advance(true);
}

function advance(instant = false) {
  if (state.idx >= state.frames.length - 1) return finish();
  state.idx++; state.progress = instant ? 1 : 0;
  showStats(); renderLog();
  if (state.idx >= state.frames.length - 1 && instant) finish();
}

function finish() {
  state.playing = false; state.progress = 1;
  const s = state.summary;
  $("status").textContent = `${STATUS[s.status]}  ·  cleaned ${s.cleaned}/${s.total_dirt} squares in ${s.steps} steps, score ${s.score}`;
}

/* ---------------- animation loop ---------------- */
const interval = () => 1000 / Math.pow(1.45, +$("speed").value - 1) * 0.9 + 25; // ms per step
function tick(ts) {
  const dt = Math.min(ts - (state.last || ts), 100); state.last = ts;
  if (state.playing) {
    state.progress += dt / interval();
    if (state.progress >= 1) {
      if (state.idx >= state.frames.length - 1) finish();
      else { state.progress -= 1; advance(); }
    }
  }
  draw();
  requestAnimationFrame(tick);
}

/* ---------------- drawing ---------------- */
function fitCanvas() {
  const w = state.world; if (!w) return;
  const avail = Math.min(document.querySelector(".canvas-wrap").clientWidth, 720);
  cell = Math.max(24, Math.floor(avail / w.cols));
  const dpr = window.devicePixelRatio || 1;
  canvas.style.width = cell * w.cols + "px"; canvas.style.height = cell * w.rows + "px";
  canvas.width = cell * w.cols * dpr; canvas.height = cell * w.rows * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function currentPos() {
  const f = state.frames;
  if (!f.length) return state.world.start;
  const a = f[Math.max(state.idx - 1, 0)].pos, b = f[state.idx].pos;
  const t = state.idx === 0 ? 1 : Math.min(state.progress, 1);
  const e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // ease in-out
  return [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e];
}

function dirtVisible(r, c) {
  const k = r + "," + c;
  if (!state.removedAt.has(k)) return true;
  const at = state.removedAt.get(k);
  return at > state.idx || (at === state.idx && state.progress < 0.6);
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

function draw() {
  const w = state.world; if (!w) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // floor
  for (let r = 0; r < w.rows; r++) for (let c = 0; c < w.cols; c++) {
    ctx.fillStyle = (r + c) % 2 ? "#f3ead8" : "#efe4cd";
    ctx.fillRect(c * cell, r * cell, cell, cell);
  }
  // charger
  const [sr, sc] = w.start;
  ctx.fillStyle = "#86efac"; ctx.fillRect(sc * cell, sr * cell, cell, cell);
  ctx.fillStyle = "#166534"; ctx.font = `${cell * .5}px sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText("⚡", sc * cell + cell / 2, sr * cell + cell / 2 + 1);

  // obstacles
  ctx.fillStyle = "#334155";
  w.obstacles.forEach(([r, c]) => { roundRect(c * cell + 3, r * cell + 3, cell - 6, cell - 6, 8); ctx.fill(); });

  // dirt
  const spots = [[.3, .35], [.62, .3], [.5, .68]];
  w.dirt.forEach(({ r, c, amount }) => {
    if (!dirtVisible(r, c)) return;
    ctx.fillStyle = "#92400e";
    for (let i = 0; i < amount; i++) {
      ctx.beginPath();
      ctx.arc(c * cell + spots[i][0] * cell, r * cell + spots[i][1] * cell, cell * .11, 0, 7); ctx.fill();
    }
  });

  // trail
  if (state.frames.length && state.idx > 0) {
    ctx.strokeStyle = "rgba(59,108,246,.35)"; ctx.lineWidth = Math.max(2, cell * .08); ctx.lineJoin = "round";
    ctx.beginPath();
    for (let i = 0; i < state.idx; i++) {
      const [r, c] = state.frames[i].pos;
      const x = (c + .5) * cell, y = (r + .5) * cell;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    const [pr, pc] = currentPos(); ctx.lineTo((pc + .5) * cell, (pr + .5) * cell);
    ctx.stroke();
  }

  drawRobot();
}

function drawRobot() {
  const [r, c] = currentPos();
  const cx = (c + .5) * cell, cy = (r + .5) * cell, rad = cell * .36;
  const f = state.frames[state.idx];
  const sucking = f && f.action === "SUCK" && state.progress < 1 && state.playing;
  const low = f && f.battery / state.batteryMax < .2;

  if (sucking) { // suction pulse
    ctx.strokeStyle = "rgba(146,64,14,.55)"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(cx, cy, rad + 4 + state.progress * 10, 0, 7); ctx.stroke();
  }
  ctx.fillStyle = low ? "#ef4444" : "#3b6cf6";
  ctx.beginPath(); ctx.arc(cx, cy, rad, 0, 7); ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.9)";
  ctx.beginPath(); ctx.arc(cx - rad * .35, cy - rad * .15, rad * .2, 0, 7); ctx.arc(cx + rad * .35, cy - rad * .15, rad * .2, 0, 7); ctx.fill();
  ctx.fillStyle = "#1e293b";
  ctx.beginPath(); ctx.arc(cx - rad * .35, cy - rad * .15, rad * .09, 0, 7); ctx.arc(cx + rad * .35, cy - rad * .15, rad * .09, 0, 7); ctx.fill();
  ctx.strokeStyle = "#fff"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(cx, cy + rad * .15, rad * .35, .15 * Math.PI, .85 * Math.PI); ctx.stroke();
}

/* ---------------- UI updates ---------------- */
function showStats() {
  const f = state.frames[state.idx];
  const total = state.world ? state.world.dirt.length : 0;
  const bat = f ? f.battery : +$("battery").value;
  $("sStep").textContent = f ? f.step : 0;
  $("sScore").textContent = f ? f.score : 0;
  $("sClean").textContent = `${f ? f.cleaned : 0}/${total}`;
  $("sAction").textContent = f && f.step ? f.action : "–";
  const pct = Math.max(0, bat / state.batteryMax * 100);
  $("batBar").style.width = pct + "%";
  $("batBar").style.background = pct < 20 ? "var(--bad)" : "var(--ok)";
  $("batText").textContent = `Battery ${Math.max(bat, 0)}/${state.batteryMax}`;
}

function renderLog() {
  const items = state.frames.slice(Math.max(1, state.idx - 11), state.idx + 1).filter((f) => f.step > 0).reverse();
  $("log").innerHTML = items.map((f) => `<li><b>#${f.step} ${f.action}</b> – ${f.reason}${f.bump ? " 💥 bump" : ""}</li>`).join("");
}

async function compareAll() {
  const rows = await post("/api/compare", simBody());
  $("compareTable").innerHTML =
    "<tr><th>Agent</th><th>Result</th><th>Cleaned</th><th>Steps</th><th>Score</th><th>Battery left</th><th>Recharges</th></tr>" +
    rows.map((r) => `<tr><td><b>${r.name}</b></td><td>${STATUS[r.status]}</td><td>${r.cleaned}/${r.total_dirt}</td>
      <td>${r.steps}</td><td>${r.score}</td><td>${Math.max(r.battery_left, 0)}</td><td>${r.recharges}</td></tr>`).join("");
  $("compareBox").hidden = false;
  $("compareBox").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ---------------- room editing (click a square) ---------------- */
canvas.addEventListener("click", (e) => {
  if (!state.world || state.playing) return;
  const rect = canvas.getBoundingClientRect();
  const c = Math.floor((e.clientX - rect.left) / cell), r = Math.floor((e.clientY - rect.top) / cell);
  const w = state.world;
  if (r < 0 || c < 0 || r >= w.rows || c >= w.cols || (r === w.start[0] && c === w.start[1])) return;
  const oi = w.obstacles.findIndex(([a, b]) => a === r && b === c);
  const di = w.dirt.findIndex((d) => d.r === r && d.c === c);
  if (oi >= 0) w.obstacles.splice(oi, 1);                       // obstacle -> empty
  else if (di < 0) w.dirt.push({ r, c, amount: 1 });             // empty -> dirt 1
  else if (w.dirt[di].amount < 3) w.dirt[di].amount++;           // dirt 1 -> 2 -> 3
  else { w.dirt.splice(di, 1); w.obstacles.push([r, c]); }       // dirt 3 -> obstacle
  resetRun();
});

/* ---------------- wiring ---------------- */
function bindSlider(id, label, fmt = (v) => v) {
  const el = $(id), out = $(label);
  const upd = () => (out.textContent = fmt(el.value)); el.addEventListener("input", upd); upd();
}
bindSlider("size", "sizeV", (v) => `${v}×${v}`); bindSlider("dirt", "dirtV"); bindSlider("obst", "obstV");
bindSlider("battery", "batV"); bindSlider("maxsteps", "maxV"); bindSlider("speed", "spdV");

$("run").onclick = play;
$("pause").onclick = () => (state.playing = false);
$("step").onclick = stepOnce;
$("reset").onclick = resetRun;
$("newRoom").onclick = newRoom;
$("compare").onclick = compareAll;
$("battery").addEventListener("change", resetRun);
$("agent").addEventListener("change", () => {
  $("agentDesc").textContent = state.agents.find((a) => a.id === $("agent").value).description; resetRun();
});
window.addEventListener("resize", fitCanvas);

(async function init() {
  state.agents = await api("/api/agents");
  $("agent").innerHTML = state.agents.map((a) => `<option value="${a.id}">${a.name}</option>`).join("");
  $("agentDesc").textContent = state.agents[0].description;
  await newRoom();
  requestAnimationFrame(tick);
})();
