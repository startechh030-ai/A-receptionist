// ============================================================
// Daven API config  —  drop into any frontend (vanilla JS / framework)
// Live API: https://a-receptionist.onrender.com
// ============================================================
const DAVEN = {
  API: "https://a-receptionist.onrender.com",
  // optional: change the male voice (en-US-GuyNeural, en-NG-AbeoNeural, en-GB-RyanNeural)
  VOICE: "en-US-GuyNeural",
};

// One session id per visitor keeps the multi-turn booking linked together.
const DAVEN_SESSION =
  localStorage.getItem("daven_session") ||
  "web-" + (crypto.randomUUID ? crypto.randomUUID() : Date.now() + Math.random());
localStorage.setItem("daven_session", DAVEN_SESSION);

// Send a message (typed), get Daven's reply + spoken audio.
async function davenSay(text) {
  const res = await fetch(`${DAVEN.API}/api/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-Id": DAVEN_SESSION },
    body: JSON.stringify({ text, session: DAVEN_SESSION }),
  }).then((r) => r.json());

  if (res.audio) new Audio("data:audio/mpeg;base64," + res.audio).play(); // Daven speaks
  return res; // { reply, transcript, status, intent, session_id, audio }
}

// Play the welcome line when the user "connects".
async function davenGreet() {
  const res = await fetch(`${DAVEN.API}/api/greeting`, {
    headers: { "X-Session-Id": DAVEN_SESSION },
  }).then((r) => r.json());
  if (res.audio) new Audio("data:audio/mpeg;base64," + res.audio).play();
  return res;
}

// Start a fresh booking/conversation.
function davenReset() {
  return fetch(`${DAVEN.API}/api/reset`, {
    method: "POST",
    headers: { "X-Session-Id": DAVEN_SESSION },
  });
}

// Example usage:
//   const r = await davenSay("I want to book a room");
//   console.log(r.reply);
//   const r2 = await davenSay("December 25th");
//   ...
