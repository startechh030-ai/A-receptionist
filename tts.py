"""
Text-to-Speech.

Primary : edge-tts (Microsoft Edge neural voices) -- FREE, no API key, and offers
          natural MALE voices. Default voice: en-US-GuyNeural (US male).
Fallback: gTTS (Google) -- always works, so the bot never goes silent mid-demo.
Optional: StreamElements (needs a JWT key via TTS_SE_KEY env var).

All backends return MP3 bytes. Change the voice via TTS_VOICE in config / env.
Good male Edge voices: en-US-GuyNeural, en-US-AndrewNeural, en-US-DavisNeural,
en-GB-RyanNeural, en-NG-AbeoNeural (Nigerian accent).
"""
import asyncio
import io
import os

import requests

import config as cfg


def _edge(text: str, voice: str) -> bytes:
    import edge_tts

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    return asyncio.run(_run())


def _streamelements(text: str, voice: str) -> bytes:
    key = os.environ.get("TTS_SE_KEY")
    params = {"voice": voice, "text": text}
    if key:  # StreamElements now requires a JWT-derived key
        params["key"] = key
    r = requests.get("https://api.streamelements.com/kappa/v2/speech",
                     params=params, timeout=15)
    r.raise_for_status()
    return r.content


def _gtts(text: str) -> bytes:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang="en", tld="com").write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def synthesize(text: str) -> bytes:
    """Return MP3 audio bytes for the given text."""
    text = (text or "").strip()
    if not text:
        text = "I didn't quite catch that."

    provider = (cfg.TTS_PROVIDER or "edge").lower()
    try:
        if provider == "edge":
            return _edge(text, cfg.TTS_VOICE)
        if provider == "streamelements":
            return _streamelements(text, cfg.TTS_VOICE)
    except Exception as e:  # graceful fallback so a demo never goes silent
        print(f"[TTS] {provider} failed, falling back to gTTS:", e)

    try:
        return _gtts(text)
    except Exception as e:
        print("[TTS] gTTS also failed:", e)
        return b""
