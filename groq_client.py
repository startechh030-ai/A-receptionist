"""
Groq integration: LLM chat (Llama 3.3 70B), Whisper STT, and PlayAI TTS.
All OpenAI-compatible endpoints. Powers natural, human-like conversation.

Set GROQ_API_KEY in the environment (see .env / Render Environment tab).
"""
import os
import requests

import config as cfg

BASE = "https://api.groq.com/openai/v1"


def _key():
    return cfg.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")


def available() -> bool:
    return bool(_key())


def _auth():
    return {"Authorization": f"Bearer {_key()}"}


# --------------------------------------------------------------------------
# Daven's persona / system prompt
# --------------------------------------------------------------------------
def system_prompt() -> str:
    return (
        f"You are Daven, the warm and professional virtual receptionist at "
        f"{cfg.HOTEL_NAME}, located at {cfg.HOTEL_LOCATION}. You are on a live phone "
        f"call with a guest.\n\n"
        f"Your job: make the guest feel welcome, answer their questions naturally, and "
        f"help them book a room if they'd like to.\n\n"
        f"About the hotel:\n"
        f"- Rooms: Standard {cfg.PRICE_STANDARD} per night, Deluxe {cfg.PRICE_DELUXE} per "
        f"night, Executive Suite {cfg.PRICE_EXECUTIVE} per night.\n"
        f"- Check-in from {cfg.CHECK_IN}, check-out by {cfg.CHECK_OUT}.\n"
        f"- Amenities: {cfg.AMENITIES}.\n"
        f"- Payment accepted: {cfg.PAYMENT_METHODS}.\n"
        f"- Contact: {cfg.HOTEL_PHONE}, {cfg.HOTEL_EMAIL}.\n\n"
        f"How to sound:\n"
        f"- Talk like a real, friendly human on a phone call. Never robotic or scripted.\n"
        f"- Keep replies short and spoken, usually 1 to 3 sentences.\n"
        f"- Vary your wording every single time. Never repeat the same greeting or phrase.\n"
        f"- Be warm and a little personable; small natural reactions are fine "
        f"('got it', 'sure thing', 'oh, nice').\n"
        f"- Once you know the guest's name, use it now and then, naturally.\n"
        f"- NEVER assume the guest's gender. Do not use 'Sir' or 'Ma' unless the guest "
        f"explicitly tells you how they'd like to be addressed.\n"
        f"- The guest's words come from voice transcription and may be slightly imperfect; "
        f"use context to understand them, and ask a quick clarifying question if unclear.\n"
        f"- If they want to book, help one step at a time (name, check-in date, check-out, "
        f"room type, number of guests), in a friendly, conversational way.\n"
        f"- Stay in role as a hotel receptionist; gently steer off-topic chats back to their stay.\n"
        f"- Output ONLY the words Daven says out loud. No emojis, no bullet lists, no "
        f"markdown, no stage directions."
    )


# --------------------------------------------------------------------------
# LLM chat
# --------------------------------------------------------------------------
def chat(messages, system=None, temperature=0.85, max_tokens=600):
    msgs = [{"role": "system", "content": system or system_prompt()}] + messages
    r = requests.post(f"{BASE}/chat/completions",
                      headers={**_auth(), "Content-Type": "application/json"},
                      json={"model": cfg.GROQ_CHAT_MODEL, "messages": msgs,
                            "temperature": temperature, "max_tokens": max_tokens},
                      timeout=35)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# --------------------------------------------------------------------------
# STT (Whisper)
# --------------------------------------------------------------------------
def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        r = requests.post(f"{BASE}/audio/transcriptions", headers=_auth(),
                          files={"file": f},
                          data={"model": cfg.GROQ_STT_MODEL, "language": "en",
                                "response_format": "json"},
                          timeout=35)
    r.raise_for_status()
    return r.json().get("text", "").strip()


# --------------------------------------------------------------------------
# TTS (PlayAI / Orpheus)  -> returns (audio_bytes, media_type)
# --------------------------------------------------------------------------
def speak(text: str):
    r = requests.post(f"{BASE}/audio/speech",
                      headers={**_auth(), "Content-Type": "application/json"},
                      json={"model": cfg.GROQ_TTS_MODEL, "input": text,
                            "voice": cfg.GROQ_TTS_VOICE, "response_format": "wav"},
                      timeout=35)
    r.raise_for_status()
    return r.content, "audio/wav"
