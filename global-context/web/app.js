/* Global Context demo UI — vanilla JS, no build step. */
const $ = (id) => document.getElementById(id);
const state = { glid: null, role: "seller", prevLines: [], waHist: [], callHist: [], inCall: false, modes: {} };

const SUGGEST = {
  seller: ["Premium plan ka charges kitna hai?", "Mujhe Delhi ke buyers chahiye, leads kam aa rahi hain", "Kal 4 baje ke baad call karna"],
  buyer: ["Iska best rate kya hai? 500 piece chahiye", "Delivery Guwahati tak ho jayegi?", "Mujhe aur suppliers chahiye"],
};
const SAY = {
  seller: ["Haan boliye", "Kitna charge lagega?", "Executive se meeting ho chuki hai", "Kal 4 baje theek hai"],
  buyer: ["Haan ji boliye", "Abhi tak sahi rate nahi mila", "Haan, suppliers bhej do"],
};

/* ---------------- api ---------------- */
async function api(path, body) {
  const opt = body instanceof FormData ? { method: "POST", body }
    : body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.detail || j.error || r.statusText), { data: j });
  return j;
}

/* ---------------- markdown render with change highlight ---------------- */
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

function renderMd(md, highlight) {
  const parts = md.split(/^---$/m);
  let fm = "", body = md;
  if (parts.length >= 3) { fm = parts[1].trim(); body = parts.slice(2).join("---"); }
  const lines = body.split("\n");
  const prev = new Set(state.prevLines);
  const out = [];
  if (fm) out.push(`<div class="fm">${esc(fm)}</div>`);
  let inList = false;
  for (const raw of lines) {
    const line = raw.trimEnd();
    const chg = highlight && line && !prev.has(line) ? " chg" : "";
    if (line.startsWith("- ")) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li class="${chg}">${inline(line.slice(2))}</li>`);
      continue;
    }
    if (inList) { out.push("</ul>"); inList = false; }
    if (!line) continue;
    if (line.startsWith("# ")) out.push(`<h1 class="${chg}">${inline(line.slice(2))}</h1>`);
    else if (line.startsWith("## ")) out.push(`<h3 class="${chg}">${inline(line.slice(3))}</h3>`);
    else if (line.startsWith("> ")) out.push(`<blockquote class="${chg}">${inline(line.slice(2))}</blockquote>`);
    else out.push(`<p class="${chg}">${inline(line)}</p>`);
  }
  if (inList) out.push("</ul>");
  $("md").innerHTML = out.join("");
  state.prevLines = lines.map((l) => l.trimEnd());
  if (highlight) setTimeout(() => document.querySelectorAll(".md .chg").forEach((e) => e.classList.add("fade")), 3500);
}

function showDoc(d, highlight = false) {
  renderMd(d.md, highlight);
  $("tokens").textContent = `${d.tokens} tokens`;
  $("version").textContent = `v${d.version}${d.llm_enriched ? " · AI-polished" : ""}`;
  $("fileName").textContent = `${d.role || state.role}.md · ${state.glid}`;
  $("rawLink").href = `/context/${state.glid}.md`;
  $("briefLink").href = `/brief/${state.glid}`;
  if (highlight && d.freshness_ms != null) stamp(`updated in ${d.freshness_ms} ms`);
  else if (highlight && d.llm_enriched) stamp("AI polish applied");
}
function stamp(text) {
  const s = $("stamp");
  s.hidden = false; s.textContent = text;
  s.style.animation = "none"; void s.offsetWidth; s.style.animation = "";
}

/* ---------------- chat bubbles ---------------- */
function bubble(logId, who, text, meta) {
  const log = $(logId);
  log.querySelector(".empty")?.remove();
  const n = $("tplMsg").content.firstElementChild.cloneNode(true);
  n.classList.add(who);
  n.querySelector(".bubble").textContent = text;
  n.querySelector(".meta").textContent = meta || "";
  log.appendChild(n);
  log.scrollTop = log.scrollHeight;
  return n;
}

/* ---------------- users ---------------- */
async function loadUsers(q) {
  const list = await api(`/api/users?role=${state.role}${q ? "&q=" + encodeURIComponent(q) : ""}`);
  const sel = $("user");
  sel.innerHTML = list.map((u) => `<option value="${u.glid}">${esc(u.name || "GLID " + u.glid)} — ${esc(u.city || "")} (${u.glid})</option>`).join("");
  if (list.length) { sel.value = list[0].glid; await selectUser(list[0].glid); }
}
async function selectUser(glid) {
  state.glid = Number(glid);
  state.prevLines = []; state.waHist = []; state.callHist = [];
  $("waLog").innerHTML = `<p class="empty">Type what the user says on WhatsApp. The memory file updates instantly — then call them on the right.</p>`;
  $("callLog").innerHTML = `<p class="empty">Start a call. Payal opens with what the memory file knows — switch memory off to hear today's cold opening.</p>`;
  $("stamp").hidden = true;
  const d = await api(`/api/context/${state.glid}`);
  $("calleeName").textContent = d.label.name || `GLID ${state.glid}`;
  $("avatar").textContent = (d.label.name || "?").trim()[0].toUpperCase();
  showDoc(d, false);
  renderSuggest();
}
function renderSuggest() {
  $("waSuggest").innerHTML = "";
  for (const s of SUGGEST[state.role]) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = s;
    b.onclick = () => { $("waText").value = s; $("waForm").requestSubmit(); };
    $("waSuggest").appendChild(b);
  }
}

/* ---------------- WhatsApp / app chat / web chat ---------------- */
$("chatChannel").addEventListener("change", () => {
  $("chatTitle").textContent = $("chatChannel").selectedOptions[0].textContent;
});
$("waForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("waText").value.trim();
  if (!text || !state.glid) return;
  $("waText").value = "";
  bubble("waLog", "user", text);
  const pending = bubble("waLog", "bot", "…", "IndiaMART assistant");
  try {
    const r = await api("/api/chat", { glid: state.glid, text, history: state.waHist, use_context: $("useCtx").checked,
                                       channel: $("chatChannel").value });
    pending.querySelector(".bubble").textContent = r.reply;
    pending.querySelector(".meta").textContent = `memory updated in ${r.freshness_ms} ms · reply by ${r.engine}`;
    state.waHist.push({ who: "user", text }, { who: "bot", text: r.reply });
  } catch (err) { pending.querySelector(".bubble").textContent = "Couldn't send: " + err.message; }
});

/* ---------------- live call: hands-free, both sides talk, caller can interrupt ----------------
   The mic stays open for the whole call. A small voice-activity detector (adaptive noise floor + pre-roll)
   cuts the caller's speech into turns; each turn goes to Saaras as 16 kHz WAV. If the caller starts talking
   while Payal is speaking or thinking, her audio stops at once and the stale reply is dropped (barge-in). */
const call = {
  phase: "idle", gen: 0, muted: false, stream: null, ctx: null, proc: null, src: null,
  noise: 0.008, inSpeech: false, voicedMs: 0, silentMs: 0, frames: [], pre: [], preMs: 0, sr: 48000,
  audio: null, timer: null, t0: 0, lastBot: null, pace: null, idleEndTimer: null,
};
const END_IDLE_MS = 3000;  // after the bot's goodbye, give the caller a few seconds to add a last word
const VAD = { startMs: 140, bargeMs: 200, endMs: 750, preRollMs: 1000, maxMs: 15000, minMs: 350 };
const PHASE_TEXT = {
  idle: "Ready to call", connecting: "Connecting…", listening: "Listening…", user: "You're speaking…",
  thinking: "Payal is thinking…", speaking: "Payal is speaking — just talk to interrupt", ended: "Call ended",
};
const MOOD_LABEL = { frustrated: "😤 frustrated", busy: "⏱ busy", confused: "🤔 confused", positive: "🙂 positive" };

function setPhase(p) {
  call.phase = p;
  $("callCard").dataset.phase = p;
  $("callState").textContent = PHASE_TEXT[p] + (state.inCall && !$("useCtx").checked ? " · cold start" : "");
}

function setCall(on) {
  state.inCall = on;
  $("callBtn").hidden = on; $("endBtn").hidden = !on; $("muteBtn").hidden = !on;
  $("sayText").disabled = !on; $("sayBtn").disabled = !on;
  clearInterval(call.timer);
  if (on) {
    call.t0 = Date.now();
    call.timer = setInterval(() => {
      const s = Math.floor((Date.now() - call.t0) / 1000);
      $("callTimer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    }, 500);
  } else { $("callTimer").textContent = ""; }
}

/* ---------- audio out ---------- */
function stopSpeaking() {
  if (call.audio) { call.audio.onended = null; call.audio.pause(); call.audio = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
}

function playOne(text, b64, gen) {
  return new Promise((resolve) => {
    if (gen !== call.gen) return resolve(false);
    const done = () => resolve(gen === call.gen);
    if (b64) {
      call.audio = new Audio("data:audio/wav;base64," + b64);
      call.audio.onended = done; call.audio.onerror = done;
      call.audio.play().catch(done);
      return;
    }
    if (!("speechSynthesis" in window)) return done();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = state.lang || "hi-IN"; u.rate = 1.02;
    const v = speechSynthesis.getVoices().find((x) => x.lang.replace("_", "-") === u.lang)
      || speechSynthesis.getVoices().find((x) => /[-_]IN$/i.test(x.lang));
    if (v) u.voice = v;
    u.onend = done; u.onerror = done;
    speechSynthesis.speak(u);
  });
}

/* Bulbul time grows with length: synthesise a short head phrase and the rest in parallel and start playing the
   head as soon as it arrives (same rule as Sarvam.speech_chunks — 2 TTS requests per reply). */
function speechChunks(text) {
  text = text.trim();
  if (text.length <= 70) return text ? [text] : [];
  let head = text.split(/(?<=[.?!।|])\s+/).find((x) => x.trim());
  if (head.length > 60) {
    const cl = head.split(/(?<=[,—;])\s+/).filter((c) => c.trim());
    let short = cl[0];
    for (const c of cl.slice(1, -1)) { if (short.length >= 20) break; short += " " + c; }
    if (short.length < head.length - 10) head = short;
  }
  const rest = text.slice(head.length).trim();
  return rest ? [head, rest] : [head];
}

async function say(text, firstAudio) {
  const gen = call.gen;
  setPhase("speaking");
  if (firstAudio || state.modes.tts !== "sarvam") {
    await playOne(text, firstAudio, gen);
  } else {
    const parts = speechChunks(text);
    const jobs = parts.map((p) => api("/api/tts", { text: p, lang: state.lang || "hi-IN", pace: call.pace })
      .then((r) => r.audio).catch(() => null));
    for (let i = 0; i < parts.length; i++) {
      if (!(await playOne(parts[i], await jobs[i], gen))) break;
    }
  }
  if (gen === call.gen && state.inCall && call.phase === "speaking") setPhase("listening");
}

/* ---------- conversation ---------- */
function cancelAutoEnd() {
  clearTimeout(call.idleEndTimer);
  call.idleEndTimer = null;
}

function scheduleAutoEnd(gen) {
  cancelAutoEnd();
  call.idleEndTimer = setTimeout(() => {
    if (gen === call.gen && state.inCall) endCall();
  }, END_IDLE_MS);
}

function bargeIn() {
  call.gen++;  // any reply still on its way is now stale
  cancelAutoEnd();
  stopSpeaking();
  if (call.lastBot && !call.lastBot.dataset.cut) {
    call.lastBot.dataset.cut = "1";
    call.lastBot.querySelector(".meta").textContent += " · interrupted";
    // Deliberately not written into state.callHist: that array is sent back as literal conversation
    // history on the next turn, and a bracketed note there reads to the LLM as something it said out
    // loud — it has no way to know it's a system annotation, so it tries to explain or repeat it.
  }
}

async function handleReply(r, gen, heardMeta) {
  if (r.user_text) bubble("callLog", "user", r.user_text, [heardMeta, MOOD_LABEL[r.mood]].filter(Boolean).join(" · "));
  state.callHist.push({ who: "user", text: r.user_text });
  if (gen !== call.gen) return;  // caller spoke again before this reply arrived: drop it, keep their words
  if (r.lang) state.lang = r.lang;
  call.pace = r.pace || null;
  state.callHist.push({ who: "bot", text: r.text });
  call.lastBot = bubble("callLog", "bot", r.text, `Payal · ${r.engine} · ${r.llm_ms} ms${r.lang && r.lang !== "hi-IN" ? " · " + r.lang : ""}`);
  await say(r.text, r.audio);
  if (r.end && gen === call.gen) scheduleAutoEnd(gen);  // let the caller add a last word before cutting the call
}

async function sendAudioTurn(wav) {
  const gen = call.gen;
  setPhase("thinking");
  const fd = new FormData();
  fd.append("glid", state.glid); fd.append("use_context", $("useCtx").checked);
  fd.append("history", JSON.stringify(state.callHist));
  fd.append("lang", state.lang || "hi-IN"); fd.append("tts", "false");
  fd.append("audio", wav, "turn.wav");
  try {
    const r = await api("/api/call/turn-audio", fd);
    await handleReply(r, gen, `Saaras · ${r.stt_ms} ms`);
  } catch (err) {
    if (gen === call.gen && state.inCall) setPhase("listening");  // noise or silence: just keep listening
  }
}

async function sendTextTurn(text) {
  cancelAutoEnd();
  if (call.phase === "speaking" || call.phase === "thinking") bargeIn();
  const gen = call.gen;
  setPhase("thinking");
  try {
    const r = await api("/api/call/turn", { glid: state.glid, text, history: state.callHist, use_context: $("useCtx").checked, lang: state.lang || "hi-IN", tts: false });
    await handleReply({ ...r, user_text: text }, gen, "typed");
  } catch (err) { if (state.inCall) setPhase("listening"); }
}

/* ---------- microphone + voice activity detection ---------- */
function encodeWav(frames, inRate, outRate = 16000) {
  const len = frames.reduce((n, f) => n + f.length, 0);
  const all = new Float32Array(len); let o = 0;
  for (const f of frames) { all.set(f, o); o += f.length; }
  const ratio = inRate / outRate, n = Math.floor(len / ratio);
  const view = new DataView(new ArrayBuffer(44 + n * 2));
  const str = (p, s) => [...s].forEach((c, i) => view.setUint8(p + i, c.charCodeAt(0)));
  str(0, "RIFF"); view.setUint32(4, 36 + n * 2, true); str(8, "WAVE"); str(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, outRate, true); view.setUint32(28, outRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  str(36, "data"); view.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {  // average each window = simple anti-aliased downsample
    let s = 0; const a = Math.floor(i * ratio), b = Math.min(len, Math.floor((i + 1) * ratio));
    for (let j = a; j < b; j++) s += all[j];
    view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s / Math.max(1, b - a))) * 0x7fff, true);
  }
  return new Blob([view], { type: "audio/wav" });
}

function showLevel(rms) {
  const bars = $("wave").children, lvl = Math.min(1, rms / 0.08);
  for (let i = 0; i < bars.length; i++) {
    const k = 0.45 + 0.55 * Math.abs(Math.sin((i + 1) * 1.7 + Date.now() / 160));
    bars[i].style.height = call.phase === "user" ? `${6 + 20 * lvl * k}px` : "";
  }
}

function onFrame(d) {
  const ms = (d.length / call.sr) * 1000;
  let sum = 0; for (let i = 0; i < d.length; i++) sum += d[i] * d[i];
  const rms = Math.sqrt(sum / d.length);
  showLevel(rms);
  if (call.muted || !state.inCall || call.phase === "connecting" || call.phase === "ended") return;
  // noise floor = min-tracker: follows quiet frames down quickly, creeps up very slowly, so the caller's own
  // first syllables can never inflate it (that delayed barge-in by ~2 s in testing)
  if (!call.inSpeech) call.noise = Math.min(0.03, Math.max(0.002,
    rms < call.noise ? call.noise * 0.85 + rms * 0.15 : call.noise * 0.998 + rms * 0.002));
  // while Payal talks, demand a clearly louder voice so her own audio (speaker echo) does not interrupt her
  const talking = call.phase === "speaking";
  const thr = talking ? Math.max(0.035, call.noise * 4) : Math.max(0.014, call.noise * 2.8);
  const voiced = rms > thr;
  if (!call.inSpeech) {
    call.pre.push(d); call.preMs += ms;
    while (call.preMs > VAD.preRollMs && call.pre.length > 1) call.preMs -= (call.pre.shift().length / call.sr) * 1000;
    // short gaps between syllables only leak the counter instead of resetting it
    call.voicedMs = voiced ? call.voicedMs + ms : Math.max(0, call.voicedMs - ms * 0.5);
    if (call.voicedMs >= (talking || call.phase === "thinking" ? VAD.bargeMs : VAD.startMs)) {
      call.inSpeech = true; call.silentMs = 0;
      call.frames = call.pre.slice(); call.pre = []; call.preMs = 0;
      cancelAutoEnd();  // the caller is adding a last word — don't cut the call under them
      if (call.phase === "speaking" || call.phase === "thinking") bargeIn();
      setPhase("user");
    }
    return;
  }
  call.frames.push(d);
  call.silentMs = voiced ? 0 : call.silentMs + ms;
  const total = call.frames.reduce((n, f) => n + f.length, 0) / call.sr * 1000;
  if (call.silentMs >= VAD.endMs || total >= VAD.maxMs) {
    call.inSpeech = false; call.voicedMs = 0;
    const frames = call.frames; call.frames = [];
    if (total - call.silentMs < VAD.minMs) { setPhase("listening"); return; }  // a cough or click
    sendAudioTurn(encodeWav(frames, call.sr));
  }
}

async function startMic() {
  call.stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
  });
  call.ctx = new (window.AudioContext || window.webkitAudioContext)();
  call.sr = call.ctx.sampleRate;
  call.src = call.ctx.createMediaStreamSource(call.stream);
  call.proc = call.ctx.createScriptProcessor(2048, 1, 1);
  call.proc.onaudioprocess = (e) => onFrame(new Float32Array(e.inputBuffer.getChannelData(0)));
  const mute = call.ctx.createGain(); mute.gain.value = 0;  // keep the graph running without echoing the mic
  call.src.connect(call.proc); call.proc.connect(mute); mute.connect(call.ctx.destination);
}

function stopMic() {
  try { call.proc && (call.proc.onaudioprocess = null); call.src?.disconnect(); call.proc?.disconnect(); } catch {}
  call.stream?.getTracks().forEach((t) => t.stop());
  call.ctx?.close().catch(() => {});
  Object.assign(call, { stream: null, ctx: null, proc: null, src: null, inSpeech: false, frames: [], pre: [], preMs: 0 });
}

/* Offline mode (no Sarvam key): the browser's own continuous speech recognition, with the same barge-in. */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
function startBrowserRecognition() {
  if (!SR) { bubble("callLog", "system", "This browser has no speech recognition — type below, or add a Sarvam key."); return; }
  const r = new SR(); r.lang = state.lang || "hi-IN"; r.continuous = true; r.interimResults = true;
  r.onresult = (e) => {
    const res = e.results[e.results.length - 1];
    if (!res.isFinal) { cancelAutoEnd(); if (call.phase === "speaking" || call.phase === "thinking") bargeIn(); setPhase("user"); return; }
    const text = res[0].transcript.trim();
    if (text && !call.muted) sendTextTurn(text).then(() => {});
  };
  r.onend = () => { if (state.inCall) try { r.start(); } catch {} };
  r.start(); call.rec = r;
}

/* ---------- Samvaad real-engine call: native turn-taking/barge-in/silence handling, replaces the DIY loop
   above entirely for the duration of the call. The platform's own on_end "save_call" tool writes the summary
   back (same /sarvam/call-ended hook used by phone calls), so this path never calls /api/call/end itself. */
let samvaadAgent = null;
let callEngine = "diy"; // "diy" | "samvaad" — which engine the active call is using
let samvaadFellBack = false; // this call already dropped from Samvaad to the DIY loop; don't do it twice

function samvaadPhase(agentState) {
  return { idle: "idle", connecting: "connecting", connected: "connecting", listening: "listening",
          speaking: "speaking", error: "ended" }[agentState] || "listening";
}

async function startSamvaadCall() {
  const s = state.samvaad;
  const { ConversationAgent, BrowserAudioInterface, InteractionType } = window.SarvamConvAI;
  // Inline the memory as agent variables, exactly as samvaad.build_request does for phone calls: the agent's
  // on_start load_context tool reaches this server only through the public tunnel, so without one running it
  // would fall back to its own default glid and open on the wrong seller. Same-origin, so no token needed.
  const vars = { glid: String(state.glid) };
  if ($("useCtx").checked) {
    try {
      const ctx = await api("/sarvam/context?glid=" + encodeURIComponent(state.glid));
      Object.assign(vars, { context: ctx.context_md, opening: ctx.opening_line, language: ctx.language });
      state.lang = ctx.language || "hi-IN";
    } catch (err) {
      bubble("callLog", "system", "Could not load the memory file — the agent will open cold: " + err.message);
    }
  }
  samvaadAgent = new ConversationAgent({
    apiKey: "", baseUrl: "/api/samvaad/",
    config: {
      org_id: s.org_id, workspace_id: s.workspace_id, app_id: s.app_id, version: s.app_version,
      user_identifier: String(state.glid), user_identifier_type: "glid",
      interaction_type: InteractionType.CALL, input_sample_rate: 16000, output_sample_rate: 16000,
      agent_variables: vars,
    },
    audioInterface: new BrowserAudioInterface(16000),
    transcriptCallback: async (msg) => {
      if (!msg.content) return;
      const who = msg.role === "bot" ? "bot" : "user";
      state.callHist.push({ who, text: msg.content });
      call.lastBot = bubble("callLog", who, msg.content, who === "bot" ? "Payal · Samvaad" : undefined);
    },
    stateCallback: (next) => {
      if (next === "error") { fallBackToDiy("Samvaad engine error"); return; }
      setPhase(samvaadPhase(next));
    },
  });
  await samvaadAgent.start();
  await samvaadAgent.waitForConnect(10);
}

async function endSamvaadCall() {
  if (!samvaadAgent) return;
  try { await samvaadAgent.stop(); } catch {}
  samvaadAgent = null;
}

/* ---------- call lifecycle ---------- */
async function startDiyCall() {
  callEngine = "diy";
  $("muteBtn").hidden = false;                       // undo whatever the Samvaad branch disabled, in case
  $("sayText").disabled = false; $("sayBtn").disabled = false;   // we got here by falling back
  $("sayText").placeholder = "…or type what the caller says";
  setCall(true); setPhase("connecting"); renderSayChips();
  const sarvamEars = state.modes.stt === "sarvam" && navigator.mediaDevices?.getUserMedia;
  try { if (sarvamEars) await startMic(); }
  catch (err) {
    bubble("callLog", "system", "Microphone blocked — allow it from the lock icon next to the address bar, or type below.");
  }
  bubble("callLog", "system", $("useCtx").checked ? `Payal loaded ${state.role}.md (v${$("version").textContent.replace(/^v/, "")})` : "Cold start — no memory loaded (today's VANI)");
  try {
    const r = await api("/api/call/start", { glid: state.glid, use_context: $("useCtx").checked });
    state.lang = r.lang || "hi-IN";
    state.callHist.push({ who: "bot", text: r.text });
    call.lastBot = bubble("callLog", "bot", r.text, `Payal · ${r.audio ? "Sarvam Bulbul" : "browser voice"}${r.prewarmed ? " · ready in " + r.ms + " ms" : ""}${state.lang !== "hi-IN" ? " · " + state.lang + " (from call history)" : ""}`);
    if (!sarvamEars) startBrowserRecognition();
    await say(r.text, r.audio);
  } catch (err) { bubble("callLog", "system", "Could not start the call: " + err.message); endCall(); }
}

/* Samvaad can fail at two points — a throw from start(), or an async "error" state once connected. Either way
   the demo should keep working on the built-in loop rather than dead-ending on an ended call. */
async function fallBackToDiy(why) {
  if (samvaadFellBack || !state.inCall) return;
  samvaadFellBack = true;
  bubble("callLog", "system", why + " — falling back to the built-in voice loop for this call.");
  try { await endSamvaadCall(); } catch {}
  await startDiyCall();
}

$("callBtn").addEventListener("click", async () => {
  if (!state.glid || state.inCall) return;
  state.callHist = []; call.gen++; cancelAutoEnd(); call.lastBot = null; call.pace = null; call.muted = false;
  samvaadFellBack = false;
  $("muteBtn").setAttribute("aria-pressed", "false"); $("muteBtn").textContent = "Mute";
  $("callLog").innerHTML = "";
  // same three conditions that reveal the toggle: on by default, so a missing SDK or unconfigured agent has to
  // fall through to the DIY loop rather than throw inside startSamvaadCall
  if ($("useSamvaad").checked && state.samvaad && state.samvaad.configured && window.SarvamConvAI) {
    callEngine = "samvaad";
    setCall(true); setPhase("connecting"); renderSayChips();
    $("muteBtn").hidden = true; // mic muting isn't exposed by the SDK yet
    $("sayText").disabled = true; $("sayBtn").disabled = true; $("sayText").placeholder = "Real-time engine — just talk, typed replies aren't routed to it";
    bubble("callLog", "system", "Connecting to the real Samvaad engine — native turn-taking, barge-in and silence handling.");
    try { await startSamvaadCall(); }
    catch (err) { await fallBackToDiy("Samvaad unavailable (" + err.message + ")"); }
    return;
  }
  await startDiyCall();
});

async function endCall() {
  if (!state.inCall) return;
  if (callEngine === "samvaad") {
    await endSamvaadCall();
    call.gen++; cancelAutoEnd();
    setCall(false); setPhase("ended"); $("muteBtn").hidden = true;
    bubble("callLog", "system", "Call ended — the agent's own save_call tool writes the summary back to memory.");
    return;
  }
  call.gen++; cancelAutoEnd(); stopSpeaking(); stopMic();
  if (call.rec) { call.rec.onend = null; try { call.rec.stop(); } catch {} call.rec = null; }
  setCall(false); setPhase("ended");
  if (!state.callHist.some((h) => h.who === "user")) {
    bubble("callLog", "system", "Call ended before the user said anything — nothing new to save.");
    return;
  }
  try {
    const r = await api("/api/call/end", { glid: state.glid, history: state.callHist });
    if (r.summary) bubble("callLog", "system", `Saved to memory: ${r.summary.disposition} — ${r.summary.summary}`, `file v${r.version} · ${r.freshness_ms} ms`);
  } catch (err) { bubble("callLog", "system", "Could not save the call: " + err.message); }
}
$("endBtn").addEventListener("click", endCall);

$("muteBtn").addEventListener("click", () => {
  call.muted = !call.muted;
  call.stream?.getAudioTracks().forEach((t) => { t.enabled = !call.muted; });
  $("muteBtn").setAttribute("aria-pressed", String(call.muted));
  $("muteBtn").textContent = call.muted ? "Unmute" : "Mute";
  if (call.muted && call.phase === "user") { call.inSpeech = false; call.frames = []; setPhase("listening"); }
});

$("sayForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("sayText").value.trim();
  if (!text || !state.inCall) return;
  $("sayText").value = "";
  await sendTextTurn(text);
});
function renderSayChips() {  // quick replies for a silent demo (typing works alongside the live mic)
  const box = $("saySuggest"); box.innerHTML = "";
  for (const s of SAY[state.role]) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = s;
    b.onclick = () => { $("sayText").value = s; $("sayForm").requestSubmit(); };
    box.appendChild(b);
  }
}

/* ---------------- live updates + status ---------------- */
function connectStream() {
  const es = new EventSource("/api/stream");
  es.onmessage = (e) => {
    const d = JSON.parse(e.data);
    if (d.type === "phone") return phoneUpdate(d);
    if (d.glid === state.glid && d.md) showDoc(d, true);
  };
}
/* ---------------- real phone call (Sarvam Voice Agents · Instant Outbound) ---------------- */
const PHONE_STATUS = { connected: "answered", no_answer: "not answered", busy: "line busy", failed: "could not be placed" };
const phoneSeen = new Set();
function phoneUpdate(d) {
  if (d.glid !== state.glid) return;
  const key = `${d.attempt_id}:${d.status}:${d.version || ""}`;
  if (phoneSeen.has(key)) return;
  phoneSeen.add(key);
  if (d.status === "dialing") { bubble("callLog", "system", `Payal is ringing ${d.phone} from Sarvam Voice Agents…`, `attempt ${d.attempt_id.slice(0, 8)}`); return; }
  const dur = d.duration ? ` · ${Math.round(d.duration)} s` : "";
  bubble("callLog", "system", `Phone call ${PHONE_STATUS[d.status] || d.status}${d.failure_reason ? " — " + d.failure_reason : ""}`, `Sarvam phone call${dur}`);
  if (d.summary) bubble("callLog", "system", `Saved to memory: ${d.summary.disposition} — ${d.summary.summary}`, `file v${d.version}`);
}
function setupPhone(p) {
  const ready = p && p.ready;
  $("phoneBtn").disabled = !ready;
  $("phoneForm").title = ready ? `Payal rings this number from ${p.agent_phone_number}${p.webhook ? "" : " (no public_url: outcome saved by the agent's on_end tool)"}`
    : "Phone calls need: " + ((p && p.missing) || []).join(", ") + " — see config.yaml → samvaad";
}
$("phoneForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const phone = $("phoneNum").value.trim();
  if (!phone || !state.glid) return;
  $("phoneBtn").disabled = true;
  try {
    const r = await api("/api/phone-call", { glid: state.glid, phone });
    phoneUpdate({ ...r, glid: state.glid });
  } catch (err) { bubble("callLog", "system", "Phone call not placed: " + err.message); }
  finally { $("phoneBtn").disabled = false; }
});

async function loadStatus() {
  const s = await api("/api/status");
  setupPhone(s.samvaad && s.samvaad.phone);
  state.modes = s.modes;
  state.samvaad = s.samvaad;
  $("engineToggleWrap").hidden = !(s.samvaad && s.samvaad.configured && window.SarvamConvAI);
  const chip = (label, val, live) => `<span class="chip ${live ? "live" : "off"}">${label}: ${val}</span>`;
  $("status").innerHTML =
    chip("LLM", s.modes.llm === "sarvam" ? "Sarvam-105B" : s.modes.llm, s.modes.llm !== "offline") +
    chip("Voice", s.modes.tts === "sarvam" ? "Bulbul + Saaras" : "browser", s.modes.tts === "sarvam") +
    chip("Data as of", s.as_of.slice(0, 16), true) +
    chip("Events", s.events.toLocaleString("en-IN"), true);
  $("modeNote").textContent = s.modes.llm === "offline" ? "Offline mode: rule-based replies and browser voice. Add SARVAM_API_KEY to .env for Sarvam voice + LLM." : "";
}
async function loadMetrics() {
  try {
    const m = await api("/api/metrics");
    if (m.live_events) $("metrics").textContent = `Freshness over ${m.live_events} live events — p50 ${m.deterministic_ms.p50} ms, p95 ${m.deterministic_ms.p95} ms` + (m.llm_enriched_ms.p50 ? ` · AI polish p50 ${(m.llm_enriched_ms.p50 / 1000).toFixed(1)} s` : "");
  } catch {}
}

$("role").addEventListener("change", (e) => { state.role = e.target.value; loadUsers(); });
$("user").addEventListener("change", (e) => selectUser(e.target.value));
let t; $("search").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => loadUsers(e.target.value.trim()), 300); });
$("rebuild").addEventListener("click", async () => { const d = await api(`/api/context/${state.glid}?rebuild=true`); showDoc(d, true); stamp("rebuilt from history"); });
function applyTheme(theme) {
  const dark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  $("themeToggle").setAttribute("aria-pressed", String(dark));
  $("themeToggle").title = dark ? "Switch to light mode" : "Switch to dark mode";
  $("themeLabel").textContent = dark ? "Light mode" : "Dark mode";
}
applyTheme(document.documentElement.dataset.theme || "light");
$("themeToggle").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try { localStorage.setItem("gcx-theme", next); } catch {}
});
$("useCtx").addEventListener("change", () => { document.querySelector(".toggle span").textContent = $("useCtx").checked ? "Bot memory on" : "Bot memory off"; });

(async () => {
  if ("speechSynthesis" in window) speechSynthesis.getVoices();
  await loadStatus();
  connectStream();
  await loadUsers();
  loadMetrics(); setInterval(loadMetrics, 8000);
})();
