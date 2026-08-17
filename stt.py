"""
Speech-to-Text using faster-whisper (tiny model).

faster-whisper is a lighter, faster, lower-memory rewrite of OpenAI Whisper,
which makes it much friendlier for deployment on Render.

The model is loaded lazily on first use and then cached. The Flask app preloads
it in a background thread at startup so the first real request is fast.
"""
import config as cfg

_model = None


def load_model():
    """Load (and cache) the Whisper model. Safe to call repeatedly."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # CPU + int8 keeps memory low. Tiny model is fastest.
        _model = WhisperModel(cfg.STT_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str, language: str = None) -> str:
    """Transcribe an audio file (wav/mp3/webm/ogg...) to plain text."""
    model = load_model()
    language = language or cfg.STT_LANGUAGE
    segments, _info = model.transcribe(audio_path, language=language, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return text
