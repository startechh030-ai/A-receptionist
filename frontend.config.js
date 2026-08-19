// ============================================================
// DAVEN CALL API CLIENT  —  drop into any frontend
// Live API: https://a-receptionist.onrender.com
// Powered by Groq (LLM + Whisper STT + PlayAI/Orpheus TTS)
// ============================================================
const DAVEN = { API: "https://a-receptionist.onrender.com" };

// One session id per visitor keeps the conversation linked.
const DAVEN_SESSION =
  localStorage.getItem("daven_call") ||
  "call-" + (crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random());
localStorage.setItem("daven_call", DAVEN_SESSION);

const _h = extra => Object.assign({ "Content-Type": "application/json", "X-Session-Id": DAVEN_SESSION }, extra || {});

// Play Daven's reply. audio_type is "audio/wav" (Groq) or "audio/mpeg" (fallback).
function davenSpeak(audioB64, audioType = "audio/mpeg") {
  if (audioB64) new Audio(`data:${audioType};base64,${audioB64}`).play();
}

// ---- CALL API ----
const DavenCall = {
  async start() { return _post("/api/call/start", {}); },
  async say({ text, audioBlob } = {}) {
    if (audioBlob) {
      const fd = new FormData(); fd.append("audio", audioBlob, "speech.webm"); fd.append("session", DAVEN_SESSION);
      const r = await fetch(`${DAVEN.API}/api/call/say`, { method: "POST", headers: { "X-Session-Id": DAVEN_SESSION }, body: fd });
      return r.json();
    }
    return _post("/api/call/say", { text });
  },
  async silence() { return _post("/api/call/silence", {}); },
  async heartbeat() { return _post("/api/call/heartbeat", {}); },
  async end() { return _post("/api/call/end", {}); },
};

// ---- CHAT API (text) ----
const DavenChat = {
  async greeting() { return fetch(`${DAVEN.API}/api/greeting`, { headers: { "X-Session-Id": DAVEN_SESSION } }).then(r => r.json()); },
  async say(text) { return _post("/api/text", { text }); },
};

async function _post(path, body) {
  return fetch(`${DAVEN.API}${path}`, { method: "POST", headers: _h(), body: JSON.stringify(body || {}) }).then(r => r.json());
}

// ---- EXAMPLE ----
/*
const g = await DavenCall.start();          // greeting
davenSpeak(g.audio, g.audio_type);

const a = await DavenCall.say({ text: "I'm Ada, I'd like to book a room" });
davenSpeak(a.audio, a.audio_type);          // natural LLM reply

const hb = await DavenCall.heartbeat();     // poll for connection tick {tick, call_status}
*/
