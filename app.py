"""
AI Receptionist -- Flask backend.

Endpoints:
  GET  /                -> test frontend (static/index.html)
  GET  /api/health      -> liveness check (Render health check)
  GET  /api/greeting    -> greeting text + spoken audio (played when "connected")
  POST /api/chat        -> { audio file } -> transcript + reply + spoken audio
  POST /api/text        -> { text }       -> reply + spoken audio (typing fallback)
  GET  /api/topics      -> list of topics the bot understands (for UI chips)

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
from tts import synthesize

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # lets your own (separate) frontend call the API during development

# In-memory sessions: one per browser, so a multi-turn booking remembers itself.
SESSIONS = {}
MAX_SESSIONS = 500


def _get_session():
    """Get (or create) the session for this request, from header/form/json."""
    sid = (request.headers.get("X-Session-Id")
           or request.form.get("session")
           or (request.get_json(silent=True) or {}).get("session"))
    if not sid:
        sid = "anon-" + uuid.uuid4().hex[:12]
    s = SESSIONS.get(sid)
    if s is None:
        if len(SESSIONS) > MAX_SESSIONS:  # crude cleanup to bound memory
            SESSIONS.clear()
        s = rc.new_session()
        SESSIONS[sid] = s
    return sid, s


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _speak_b64(text: str) -> str:
    """Convert text to speech and return base64-encoded MP3 (empty string on error)."""
    try:
        return base64.b64encode(synthesize(text)).decode("ascii")
    except Exception as e:
        print("[TTS] error:", e)
        return ""


def _preload_whisper() -> None:
    """Load the Whisper model in the background so the first request is fast."""
    try:
        from stt import load_model
        print("[STT] preloading Whisper model in background...")
        load_model()
        print("[STT] Whisper model ready.")
    except Exception as e:
        print("[STT] preload failed:", e)


# Start background preload once the app is ready.
threading.Thread(target=_preload_whisper, daemon=True).start()


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify(status="ok", hotel=cfg.HOTEL_NAME, receptionist=cfg.RECEPTIONIST_NAME)


@app.route("/api/greeting")
def greeting():
    sid, _session = _get_session()  # initialise the session for this browser
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
    """Typing fallback: guest types instead of speaking."""
    sid, session = _get_session()
    data = request.get_json(silent=True) or {}
    transcript = (data.get("text") or "").strip()
    reply = rc.respond(transcript, session)
    return jsonify(
        transcript=transcript,
        reply=reply.text,
        intent=reply.intent,
        status=reply.status,
        session_id=sid,
        audio=_speak_b64(reply.text),
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    """Voice path: guest records audio, we transcribe then reply with speech."""
    if "audio" not in request.files:
        return jsonify(error="no audio file provided"), 400

    file = request.files["audio"]
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"

    tmp_path = None
    transcript = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        from stt import transcribe
        transcript = transcribe(tmp_path)
    except Exception as e:
        print("[STT] transcription error:", e)
        transcript = ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    sid, session = _get_session()
    reply = rc.respond(transcript, session)
    return jsonify(
        transcript=transcript,
        reply=reply.text,
        intent=reply.intent,
        status=reply.status,
        session_id=sid,
        audio=_speak_b64(reply.text),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
