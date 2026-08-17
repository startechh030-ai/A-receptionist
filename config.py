"""
Central configuration for the AI Receptionist.

>>> EDIT THE DEFAULTS BELOW WITH YOUR REAL HOTEL INFO <<<
Every value can also be overridden with an environment variable (see .env.example).
This keeps all your business facts in ONE place so they're easy to update.
"""
import os

# ---- Identity -------------------------------------------------------------
HOTEL_NAME = os.getenv("HOTEL_NAME", "City Resort Hotel")
RECEPTIONIST_NAME = os.getenv("RECEPTIONIST_NAME", "Daven")

# ---- Contact / Location ---------------------------------------------------
HOTEL_LOCATION = os.getenv(
    "HOTEL_LOCATION",
    "12 Kingsway Road, Osogbo, Osun State, Nigeria",
)
HOTEL_PHONE = os.getenv("HOTEL_PHONE", "+234 800 000 0000")
HOTEL_EMAIL = os.getenv("HOTEL_EMAIL", "stay@cityresorthotel.com")

# ---- Timings --------------------------------------------------------------
CHECK_IN = os.getenv("CHECK_IN", "2:00 PM")
CHECK_OUT = os.getenv("CHECK_OUT", "12:00 noon")

# ---- Pricing (per night) --------------------------------------------------
PRICE_STANDARD = os.getenv("PRICE_STANDARD", "N15,000")
PRICE_DELUXE = os.getenv("PRICE_DELUXE", "N25,000")
PRICE_EXECUTIVE = os.getenv("PRICE_EXECUTIVE", "N45,000")

# ---- Amenities ------------------------------------------------------------
AMENITIES = os.getenv(
    "AMENITIES",
    "free Wi-Fi, air conditioning, 24-hour power, free breakfast, "
    "a swimming pool, free parking, and 24-hour room service",
)

# ---- Payment --------------------------------------------------------------
PAYMENT_METHODS = os.getenv(
    "PAYMENT_METHODS", "card, bank transfer, and cash at the front desk"
)

# ---- Voice / Speech settings ---------------------------------------------
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")          # edge | streamelements | gtts
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")     # male (Edge). Try en-NG-AbeoNeural (Nigerian), en-GB-RyanNeural
STT_MODEL = os.getenv("STT_MODEL", "tiny")                # faster-whisper model size: tiny | base | small
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")
