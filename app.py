"""
AI Receptionist -- Flask backend (v3: chat + call).

CHAT API (free chat, v2):
  GET  /api/health, /api/greeting, /api/topics
  POST /api/chat (audio), /api/text (text), /api/reset

CALL API (v3 phone-call experience):
  POST /api/call/start     -> greeting + first prompt (call begins)
  POST /api/call/say       -> { text } OR audio file -> Daven's reply + audio
  POST /api/call/ui        -> { action, value } (payment options / form / id)
  POST /api/call/silence   -> "can you hear me?" / disconnect line
  POST /api/call/heartbeat -> { tick } randomised connection tick
  POST /api/call/end       -> end the call

Run locally:  python app.py
On Render:    gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
"""
import base64
import os
import tempfile
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import config as cfg
import receptionist as rc
import callflow as cf
from tts import synthesize

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# In-memory stores (capped). Swap for Redis in production.
SESSIONS = {}
CALLS = {}
MAX_STORE = 500


def _sid():
    """Session id from header / form / json (auto-generated if missing)."""
    sid = (request.headers.get("X-Session-Id")
           or request.form.get("session")
           or (request.get_json(silent=True) or {}).get("session"))
    if not sid:
        sid = "anon-" + uuid.uuid4().hex[:12]
    return sid


def _get_session():
    sid = _sid()
    s = SESSIONS.get(sid)
    if s is None:
        if len(SESSIONS) > MAX_STORE:
            SESSIONS.clear()
        s = rc.new_session()
        SESSIONS[sid] = s
    return sid, s


def _get_call():
    sid = _sid()
    c = CALLS.get(sid)
    if c is None:
        if len(CALLS) > MAX_STORE:
            CALLS.clear()
        c = cf.new_call()
        CALLS[sid] = c
    return sid, c


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _speak_b64(text: str) -> str:
    try:
        return base64.b64encode(synthesize(text)).decode("ascii")
    except Exception as e:
        print("[TTS] error:", e)
        return ""


def _transcribe_file(file_storage) -> str:
    suffix = os.path.splitext(file_storage.filename or "")[1] or ".webm"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file_storage.save(tmp.name)
            tmp_path = tmp.name
        from stt import transcribe
        return transcribe(tmp_path)
    except Exception as e:
        print("[STT] transcription error:", e)
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _preload_whisper() -> None:
    try:
        from stt import load_model
        print("[STT] preloading Whisper model in background...")
        load_model()
        print("[STT] Whisper model ready.")
    except Exception as e:
        print("[STT] preload failed:", e)


threading.Thread(target=_preload_whisper, daemon=True).start()


# --------------------------------------------------------------------------
# Pages / health
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify(status="ok", hotel=cfg.HOTEL_NAME, receptionist=cfg.RECEPTIONIST_NAME)


# --------------------------------------------------------------------------
# CHAT API (v2 free chat)
# --------------------------------------------------------------------------
@app.route("/api/greeting")
def greeting():
    sid, _s = _get_session()
    text = (f"Hi, my name is {cfg.RECEPTIONIST_NAME} from {cfg.HOTEL_NAME}. "
            f"How can I help you today?")
    return jsonify(text=text, audio=_speak_b64(text), session_id=sid)


@app.route("/api/reset", methods=["POST"])
def reset():
    sid, session = _get_session()
    rc.reset_session(session)
    return jsonify(status="ok", session_id=sid)


@app.route("/api/topics")
def topics():
    return jsonify(topics=rc.topics())


@app.route("/api/text", methods=["POST"])
def text_chat():
    sid, session = _get_session()
    data = request.get_json(silent=True) or {}
    transcript = (data.get("text") or "").strip()
    reply = rc.respond(transcript, session)
    return jsonify(transcript=transcript, reply=reply.text, intent=reply.intent,
                   status=reply.status, session_id=sid, audio=_speak_b64(reply.text))


@app.route("/api/chat", methods=["POST"])
def chat():
    if "audio" not in request.files:
        return jsonify(error="no audio file provided"), 400
    transcript = _transcribe_file(request.files["audio"])
    sid, session = _get_session()
    reply = rc.respond(transcript, session)
    return jsonify(transcript=transcript, reply=reply.text, intent=reply.intent,
                   status=reply.status, session_id=sid, audio=_speak_b64(reply.text))


# --------------------------------------------------------------------------
# CALL API (v3)
# --------------------------------------------------------------------------
@app.route("/api/call/start", methods=["POST"])
def call_start():
    sid, call = _get_call()
    # fresh call each time Start is pressed
    call.update(cf.new_call())
    r = cf.handle_call(call, "start")
    r["audio"] = _speak_b64(r["reply"])
    r["session_id"] = sid
    return jsonify(r)


@app.route("/api/call/say", methods=["POST"])
def call_say():
    sid, call = _get_call()
    transcript = ""
    if "audio" in request.files:
        transcript = _transcribe_file(request.files["audio"])
    else:
        data = request.get_json(silent=True) or {}
        transcript = data.get("text", "")
    r = cf.handle_call(call, "say", transcript=transcript)
    r["transcript"] = transcript
    r["audio"] = _speak_b64(r["reply"])
    r["session_id"] = sid
    return jsonify(r)


@app.route("/api/call/ui", methods=["POST"])
def call_ui():
    sid, call = _get_call()
    data = request.get_json(silent=True) or {}
    value = {"action": data.get("action"), "value": data.get("value")}
    r = cf.handle_call(call, "ui", value=value)
    r["audio"] = _speak_b64(r["reply"])
    r["session_id"] = sid
    return jsonify(r)


@app.route("/api/call/silence", methods=["POST"])
def call_silence():
    sid, call = _get_call()
    r = cf.handle_call(call, "silence")
    r["audio"] = _speak_b64(r.get("reply", ""))
    r["session_id"] = sid
    return jsonify(r)


@app.route("/api/call/heartbeat", methods=["POST"])
def call_heartbeat():
    sid, call = _get_call()
    r = cf.handle_call(call, "heartbeat")
    r["session_id"] = sid
    return jsonify(r)


@app.route("/api/call/end", methods=["POST"])
def call_end():
    sid, call = _get_call()
    cf.handle_call(call, "end")
    return jsonify(call_status="ended", session_id=sid, summary=cf.summary(call))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
