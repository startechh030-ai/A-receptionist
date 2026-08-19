"""
Optional LOCAL speech-to-text fallback (faster-whisper).

Groq Whisper is now the PRIMARY STT (faster, more accurate, no heavy model on the
server). This module is only used if Groq is unavailable AND faster-whisper is
installed. If it's not installed, transcribe() simply returns ''.
"""
_model = None


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str, language: str = "en") -> str:
    try:
        model = _load()
        segments, _info = model.transcribe(audio_path, language=language, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        print("[STT] local fallback unavailable:", e)
        return ""
