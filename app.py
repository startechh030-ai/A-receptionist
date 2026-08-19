"""
AI Receptionist -- Flask backend (v4: Groq-powered, human-like).

The brain is now an LLM (Groq Llama 3.3 70B) with Whisper STT and PlayAI TTS.
Multi-layer fallbacks: if Groq is down, STT falls back to local whisper, replies
fall back to the tag engine, and TTS falls back to edge-tts / gTTS.

CHAT API:   GET /api/health | /api/greeting | /api/topics
            POST /api/text {text} | /api/chat (audio) | /api/reset
CALL API:   POST /api/call/start | /api/call/say (text|audio)
            POST /api/call/silence | /api/call/heartbeat | /api/call/end | /api/call/ui
"""
import base64
import os
import random
import tempfile
import time
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import config as cfg
import receptionist as rc        # fallback (tag) brain
import groq_client as gq         # primary brain / STT / TTS
from tts import synthesize as _tts_fallback   # fallback TTS (mp3)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

SESSIONS = {}
CALLS = {}
MAX_STORE = 500

SILENCE_LINES = [
    "Hello? Are you still there?",
    "I'm still here \u2014 can you hear me okay?",
    "Hmm, I can't quite hear you. Are we still connected?",
    "Hey, you still on the line? Just checking.",
]
DISCONNECT_LINE = ("Alright, it seems we've gotten disconnected, so I'll let you go "
                   "for now. Please give us another call when you have a better "
                   "connection. Take care, goodbye!")


# --------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------
def _sid():
    sid = (request.headers.get("X-Session-Id")
           or request.form.get("session")
           or (request.get_json(silent=True) or {}).get("session"))
    return sid or "anon-" + uuid.uuid4().hex[:12]


def _chat(sid):
    s = SESSIONS.get(sid)
    if s is None:
        if len(SESSIONS) > MAX_STORE:
            SESSIONS.clear()
        s = {"messages": [], "rc": rc.new_session()}
        SESSIONS[sid] = s
    return s


def _call(sid):
    c = CALLS.get(sid)
    if c is None:
        if len(CALLS) > MAX_STORE:
            CALLS.clear()
        c = {"messages": [], "silence": 0, "ended": False}
        CALLS[sid] = c
    return c


def _trim(msgs, n=14):
    return msgs[-n:]


# --------------------------------------------------------------------------
# STT / TTS helpers (with fallbacks)
# --------------------------------------------------------------------------
def _transcribe(path):
    if gq.available():
        try:
            return gq.transcribe(path)
        except Exception as e:
            print("[STT] Groq failed, trying local:", e)
    try:
        from stt import transcribe as local
        return local(path)
    except Exception as e:
        print("[STT] no transcriber available:", e)
        return ""


def _speak(text):
    """Return (base64_audio, media_type)."""
    if gq.available():
        try:
            data, mtype = gq.speak(text)
            return base64.b64encode(data).decode("ascii"), mtype
        except Exception as e:
            print("[TTS] Groq failed, trying fallback:", e)
    try:
        data = _tts_fallback(text)
        return base64.b64encode(data).decode("ascii"), "audio/mpeg"
    except Exception as e:
        print("[TTS] all TTS failed:", e)
        return "", "audio/mpeg"


def _llm_reply(messages, fallback_text):
    """LLM reply with graceful tag-engine fallback."""
    if gq.available():
        try:
            return gq.chat(_trim(messages)), "llm"
        except Exception as e:
            print("[LLM] Groq failed, using tag fallback:", e)
    return fallback_text, "tags"


def _generate_greeting():
    if gq.available():
        try:
            return gq.chat([{"role": "user", "content":
                "(The call just connected and the guest is on the line. Greet them "
                "warmly and naturally in one or two short sentences and invite them to "
                "tell you how you can help. Make it fresh \u2014 never the same twice.)"}],
                max_tokens=512)
        except Exception as e:
            print("[LLM] greeting failed:", e)
    return (f"Hello, thanks for calling {cfg.HOTEL_NAME}, this is {cfg.RECEPTIONIST_NAME}. "
            f"How can I help you today?")


# --------------------------------------------------------------------------
# Pages / health
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify(status="ok", hotel=cfg.HOTEL_NAME, receptionist=cfg.RECEPTIONIST_NAME,
                   groq=gq.available())


# --------------------------------------------------------------------------
# CHAT API (conversational)
# --------------------------------------------------------------------------
@app.route("/api/greeting")
def greeting():
    sid = _sid()
    s = _chat(sid)
    text = _generate_greeting()
    s["messages"] = [{"role": "assistant", "content": text}]
    audio, atype = _speak(text)
    return jsonify(text=text, audio=audio, audio_type=atype, session_id=sid)


@app.route("/api/reset", methods=["POST"])
def reset():
    sid = _sid()
    SESSIONS.pop(sid, None)
    CALLS.pop(sid, None)
    return jsonify(status="ok", session_id=sid)


@app.route("/api/topics")
def topics():
    return jsonify(topics=rc.topics())


def _do_chat(sid, user_text):
    s = _chat(sid)
    if user_text:
        s["messages"].append({"role": "user", "content": user_text})
    # LLM with tag-engine fallback
    fb = rc.respond(user_text, s["rc"]).text
    reply, engine = _llm_reply(s["messages"], fb)
    s["messages"].append({"role": "assistant", "content": reply})
    audio, atype = _speak(reply)
    return {"transcript": user_text, "reply": reply, "engine": engine,
            "audio": audio, "audio_type": atype, "session_id": sid}


@app.route("/api/text", methods=["POST"])
def text_chat():
    sid = _sid()
    data = request.get_json(silent=True) or {}
    return jsonify(_do_chat(sid, (data.get("text") or "").strip()))


@app.route("/api/chat", methods=["POST"])
def chat():
    if "audio" not in request.files:
        return jsonify(error="no audio file provided"), 400
    sid = _sid()
    transcript = _transcribe_save(request.files["audio"])
    return jsonify(_do_chat(sid, transcript))


def _transcribe_save(file_storage):
    suffix = os.path.splitext(file_storage.filename or "")[1] or ".webm"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
            file_storage.save(t.name)
            tmp = t.name
        return _transcribe(tmp)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


# --------------------------------------------------------------------------
# CALL API (conversational phone call)
# --------------------------------------------------------------------------
@app.route("/api/call/start", methods=["POST"])
def call_start():
    sid = _sid()
    c = {"messages": [], "silence": 0, "ended": False}
    CALLS[sid] = c
    text = _generate_greeting()
    c["messages"] = [{"role": "assistant", "content": text}]
    audio, atype = _speak(text)
    return jsonify(reply=text, audio=audio, audio_type=atype, call_status="active",
                   state="greeting", session_id=sid)


@app.route("/api/call/say", methods=["POST"])
def call_say():
    sid = _sid()
    c = _call(sid)
    if c["ended"]:
        return jsonify(reply="This call has ended. Please start a new call.",
                       call_status="ended", session_id=sid)
    if "audio" in request.files:
        transcript = _transcribe_save(request.files["audio"])
    else:
        transcript = (request.get_json(silent=True) or {}).get("text", "")
    transcript = (transcript or "").strip()
    c["silence"] = 0
    if transcript:
        c["messages"].append({"role": "user", "content": transcript})
    fb = ("I'm here and happy to help. Could you say a bit more about what you need?"
          if not transcript else "I didn't quite catch that \u2014 could you repeat it?")
    reply, engine = _llm_reply(c["messages"], fb)
    c["messages"].append({"role": "assistant", "content": reply})
    audio, atype = _speak(reply)
    return jsonify(reply=reply, transcript=transcript, engine=engine, audio=audio,
                   audio_type=atype, call_status="active", session_id=sid)


@app.route("/api/call/silence", methods=["POST"])
def call_silence():
    sid = _sid()
    c = _call(sid)
    c["silence"] += 1
    if c["silence"] >= 3:
        c["ended"] = True
        text = DISCONNECT_LINE
        status = "ended"
    else:
        text = random.choice(SILENCE_LINES)
        status = "active"
    audio, atype = _speak(text) if text else ("", "audio/mpeg")
    return jsonify(reply=text, audio=audio, audio_type=atype, call_status=status,
                   session_id=sid)


@app.route("/api/call/heartbeat", methods=["POST"])
def call_heartbeat():
    sid = _sid()
    c = _call(sid)
    return jsonify(tick=random.randint(1000, 9999),
                   call_status="ended" if c["ended"] else "active",
                   session_id=sid)


@app.route("/api/call/end", methods=["POST"])
def call_end():
    sid = _sid()
    c = _call(sid)
    c["ended"] = True
    return jsonify(call_status="ended", session_id=sid)


@app.route("/api/call/ui", methods=["POST"])
def call_ui():
    # Reserved for Phase 2 (payment / ID UI triggers).
    sid = _sid()
    c = _call(sid)
    return jsonify(call_status="ended" if c["ended"] else "active", session_id=sid)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
