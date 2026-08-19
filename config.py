"""Central configuration. Override anything with environment variables."""
import os

# ---- Identity ----
HOTEL_NAME = os.getenv("HOTEL_NAME", "City Resort Hotel")
RECEPTIONIST_NAME = os.getenv("RECEPTIONIST_NAME", "Daven")

# ---- Contact / Location ----
HOTEL_LOCATION = os.getenv("HOTEL_LOCATION", "12 Kingsway Road, Osogbo, Osun State, Nigeria")
HOTEL_PHONE = os.getenv("HOTEL_PHONE", "+234 800 000 0000")
HOTEL_EMAIL = os.getenv("HOTEL_EMAIL", "stay@cityresorthotel.com")

# ---- Timings ----
CHECK_IN = os.getenv("CHECK_IN", "2:00 PM")
CHECK_OUT = os.getenv("CHECK_OUT", "12:00 noon")

# ---- Pricing (per night) ----
PRICE_STANDARD = os.getenv("PRICE_STANDARD", "N15,000")
PRICE_DELUXE = os.getenv("PRICE_DELUXE", "N25,000")
PRICE_EXECUTIVE = os.getenv("PRICE_EXECUTIVE", "N45,000")

# ---- Amenities ----
AMENITIES = os.getenv("AMENITIES",
    "free Wi-Fi, air conditioning, 24-hour power, free breakfast, a swimming pool, "
    "free parking, and 24-hour room service")

# ---- Payment ----
PAYMENT_METHODS = os.getenv("PAYMENT_METHODS", "card, bank transfer, and cash at the front desk")

# ---- Groq (LLM + Whisper STT + TTS) ----
# Available on this account: openai/gpt-oss-120b, openai/gpt-oss-20b (LLM);
# whisper-large-v3-turbo (STT); canopylabs/orpheus-v1-english (TTS, needs terms).
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
GROQ_TTS_MODEL = os.getenv("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english")
GROQ_TTS_VOICE = os.getenv("GROQ_TTS_VOICE", "troy")   # male; try also: austin, adam

# ---- Fallback TTS (used only if Groq TTS is unavailable, e.g. terms not accepted) ----
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")        # edge | gtts
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")   # edge-tts male fallback
