// ============================================================
// DAVEN CALL API CLIENT  —  drop into any frontend (vanilla JS)
// Live API: https://a-receptionist.onrender.com
// ============================================================
const DAVEN = {
  API: "https://a-receptionist.onrender.com",
  VOICE: "en-US-GuyNeural", // male voice (edge-tts)
};

// One session id per visitor keeps the call linked together.
const DAVEN_SESSION =
  localStorage.getItem("daven_call") ||
  "call-" + (crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random());
localStorage.setItem("daven_call", DAVEN_SESSION);

const _h = () => ({ "Content-Type": "application/json", "X-Session-Id": DAVEN_SESSION });
async function _post(path, body) {
  const r = await fetch(`${DAVEN.API}${path}`, { method: "POST", headers: _h(), body: JSON.stringify(body || {}) });
  return r.json();
}

// Play Daven's reply audio (base64 mp3).
function davenSpeak(audioB64) {
  if (audioB64) new Audio("data:audio/mpeg;base64," + audioB64).play();
}

// ---- CALL API (v3) -------------------------------------------------------
const DavenCall = {
  // Begin the call. Returns { reply, audio, state, ui, call_status, session_id, ... }
  async start() { return _post("/api/call/start", {}); },

  // Send a spoken/typed message. Use ONE of: text  OR  audioBlob
  async say({ text, audioBlob } = {}) {
    if (audioBlob) {
      const fd = new FormData();
      fd.append("audio", audioBlob, "speech.webm");
      fd.append("session", DAVEN_SESSION);
      const r = await fetch(`${DAVEN.API}/api/call/say`, { method: "POST", headers: { "X-Session-Id": DAVEN_SESSION }, body: fd });
      return r.json();
    }
    return _post("/api/call/say", { text });
  },

  // User clicked a payment option or submitted payment details.
  async ui(action, value) { return _post("/api/call/ui", { action, value }); },

  // Fire when the user has been silent for a while (no response).
  async silence() { return _post("/api/call/silence", {}); },

  // Randomised connection tick. Poll every few seconds.
  async heartbeat() { return _post("/api/call/heartbeat", {}); },

  // End the call.
  async end() { return _post("/api/call/end", {}); },
};

// ---- CHAT API (v2 free chat, still available) ---------------------------
const DavenChat = {
  async greeting() { return _post("/api/greeting", {}); /* GET also works */ },
  async say(text) { return _post("/api/text", { text }); },
};

// ---- EXAMPLE: a full call -----------------------------------------------
/*
  const r = await DavenCall.start();
  console.log(r.reply); davenSpeak(r.audio);          // "Hello, good day... your name?"
  showCard(r.ui);                                      // render ui if present

  const a = await DavenCall.say({ text: "my name is Grace" });
  davenSpeak(a.audio);

  const b = await DavenCall.say({ text: "I'd like to book a room" });
  davenSpeak(b.audio);

  const c = await DavenCall.say({ text: "yes" });      // triggers payment_options UI
  showCard(c.ui);

  await DavenCall.ui("select_payment", "Card");        // -> payment_form UI
  await DavenCall.ui("submit_payment", "4242424242424242"); // stub success -> id_card UI + room no.

  const m = await DavenCall.say({ text: "December 25th" });
  await DavenCall.say({ text: "yes" });                // -> warm closing, call ends

  // connection tick (poll every 5s):
  const hb = await DavenCall.heartbeat(); // { tick, call_status, state }
*/
