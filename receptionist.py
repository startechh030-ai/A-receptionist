"""
The "brain" of the AI Receptionist (FINAL v2 -- multi-turn booking + name memory).

SEMI-AI: there is no large language model. We match what the guest said against
TAGS (keyword groups). A small state machine then walks the guest through a real
booking, one detail at a time:

    name -> check-in date -> check-out date -> room type -> guests -> confirm

Rules:
  * Confident tag match        -> answer that topic
  * 1 weak / ambiguous match   -> "Could you be more specific..."
  * No match / off-topic       -> "Let's go back to your booking..."
  * Social (hi/thanks/bye)     -> answered directly
  * Guest introduces themselves -> greet by name AND remember it
"""
import random
import re
import string
from dataclasses import dataclass
from typing import List, Optional

import config as cfg

# --------------------------------------------------------------------------
# Context used to fill {placeholders} inside responses.
# --------------------------------------------------------------------------
CTX = {
    "hotel": cfg.HOTEL_NAME,
    "receptionist": cfg.RECEPTIONIST_NAME,
    "location": cfg.HOTEL_LOCATION,
    "phone": cfg.HOTEL_PHONE,
    "email": cfg.HOTEL_EMAIL,
    "checkin": cfg.CHECK_IN,
    "checkout": cfg.CHECK_OUT,
    "price_standard": cfg.PRICE_STANDARD,
    "price_deluxe": cfg.PRICE_DELUXE,
    "price_executive": cfg.PRICE_EXECUTIVE,
    "amenities": cfg.AMENITIES,
    "payment": cfg.PAYMENT_METHODS,
}

STRONG_WORDS = {
    "price", "prices", "book", "booking", "breakfast", "wifi", "wi-fi",
    "location", "where", "address", "directions", "cancel", "cancellation",
    "confirmation", "reservation", "reserve", "parking", "payment",
    "amenities", "pool", "gym", "dog", "cat", "pet", "pets", "suite",
    "deluxe", "executive", "internet",
    "secure", "security", "safe", "safety", "id", "passport",
    "identification", "license", "document", "documents",
    "restaurant", "lunch", "dinner", "menu", "meal", "meals", "food", "dine",
    "swimming", "spa", "ac", "generator", "laundry",
}
CONFIDENT_HITS = 2


@dataclass
class Intent:
    id: str
    label: str
    keywords: List[str]
    response: str
    social: bool = False


# --------------------------------------------------------------------------
# THE KNOWLEDGE BASE (the "tags") -- edit freely.
# --------------------------------------------------------------------------
INTENTS: List[Intent] = [
    Intent("greeting", "greeting", social=True,
           keywords=["hi", "hello", "hey", "hiya", "good morning", "good afternoon",
                     "good evening", "good day", "greetings", "how are you"],
           response="Hello, and welcome to {hotel}! I'm {receptionist}, your virtual "
                    "receptionist. How may I help you today?"),
    Intent("thanks", "thanks", social=True,
           keywords=["thank", "thanks", "thank you", "appreciate", "cheers", "grateful"],
           response="You're very welcome! Is there anything else I can help you with?"),
    Intent("goodbye", "goodbye", social=True,
           keywords=["bye", "goodbye", "good bye", "see you", "later", "that's all",
                     "nothing else", "no more", "good night", "i'm done"],
           response="Thank you for considering {hotel}. We look forward to hosting you. "
                    "Have a wonderful day!"),
    Intent("price", "room prices",
           keywords=["price", "prices", "pricing", "cost", "costs", "how much", "rate",
                     "rates", "fee", "fees", "charge", "charges", "expensive", "cheap",
                     "affordable", "budget", "per night", "tariff"],
           response="Our room rates at {hotel} are very affordable. A Standard room is "
                    "{price_standard} per night, a Deluxe room is {price_deluxe} per night, "
                    "and our Executive Suite is {price_executive} per night. Would you like "
                    "to go ahead and book one?"),
    Intent("room_types", "room types",
           keywords=["room", "rooms", "room type", "room types", "types of room",
                     "what rooms", "which room", "suite", "suites", "deluxe", "executive",
                     "standard", "options", "categories", "available room", "kinds of room",
                     "room option"],
           response="We have three room types at {hotel}. The Standard room is cozy and "
                    "perfect for short stays, the Deluxe room is more spacious with extra "
                    "comfort, and our Executive Suite offers a premium experience. Which "
                    "one interests you?"),
    Intent("book", "booking a room",
           keywords=["book", "booking", "reserve", "reservation", "order", "availability",
                     "make a booking", "reserve a room", "book a room", "i want a room",
                     "get a room", "i want to stay", "check availability"],
           response="Great! Let's get your booking started."),
    Intent("check_in", "check-in time",
           keywords=["check in", "check-in", "checkin", "checking in", "arrival", "arrive",
                     "arriving", "when can i check in", "get in", "reach the hotel",
                     "early check in", "early"],
           response="Check-in at {hotel} starts from {checkin} onwards. If you arrive "
                    "earlier, we'll happily store your luggage and do our best to get you "
                    "into your room as soon as possible."),
    Intent("check_out", "check-out time",
           keywords=["check out", "check-out", "checkout", "checking out", "departure",
                     "depart", "leave", "leaving", "late checkout", "late check out"],
           response="Check-out is by {checkout}. If you need a late check-out, just let us "
                    "know in advance and we'll try our best to arrange it for you."),
    Intent("location", "the location",
           keywords=["location", "where", "address", "located", "directions", "how do i get",
                     "how to get", "find you", "map", "landmark", "near", "nearby",
                     "distance", "far"],
           response="{hotel} is located at {location}. It's easy to reach by road. For "
                    "step-by-step directions, you can also call us at {phone}."),
    Intent("amenities", "our amenities",
           keywords=["amenity", "amenities", "facility", "facilities", "features", "offer",
                     "what do you have", "services", "include", "included", "what's included",
                     "pool", "swimming pool", "gym", "fitness", "spa", "air conditioning",
                     "ac", "generator", "power", "electricity", "laundry", "bar", "lounge"],
           response="{hotel} offers {amenities}. We want your stay to be as comfortable and "
                    "convenient as possible. Is there a specific facility you'd like to know "
                    "more about?"),
    Intent("wifi", "Wi-Fi",
           keywords=["wifi", "wi-fi", "wi fi", "internet", "connection", "data", "hotspot",
                     "network"],
           response="Yes! We provide fast and free Wi-Fi throughout {hotel}, including all "
                    "rooms and public areas. You'll receive the password at check-in."),
    Intent("contact", "contact details",
           keywords=["phone", "call", "contact", "number", "reach", "reach you", "whatsapp",
                     "email", "e-mail", "front desk", "customer care"],
           response="You can reach {hotel} by phone at {phone}, or email us at {email}. "
                    "Our front desk is open and available 24 hours a day."),
    Intent("payment", "payment",
           keywords=["pay", "payment", "card", "cash", "transfer", "pos", "deposit",
                     "method", "methods", "how do i pay"],
           response="We accept {payment}. A small deposit may be required to confirm your "
                    "booking. Let me know how you'd prefer to pay."),
    Intent("confirmation", "booking confirmation",
           keywords=["confirm", "confirmation", "confirmed", "booking number",
                     "reservation number", "reference", "my booking", "booking status",
                     "status", "receipt", "proof", "did it go through"],
           response="Once your booking is complete, {hotel} will send you a confirmation "
                    "message with your reservation number and room details. If you've already "
                    "booked and need your status, please share your booking reference and our "
                    "team will confirm it for you."),
    Intent("cancel", "cancellation",
           keywords=["cancel", "cancellation", "cancelled", "refund", "change", "reschedule",
                     "modify", "move", "postpone", "booking", "reservation"],
           response="Bookings at {hotel} can be cancelled or changed free of charge up to 24 "
                    "hours before your check-in. After that, a small fee may apply."),
    Intent("pets", "pet policy",
           keywords=["pet", "pets", "dog", "cat", "animal", "animals"],
           response="We love animals! Unfortunately {hotel} does not allow pets, except for "
                    "registered service animals. Thank you for understanding."),
    Intent("guests", "number of guests",
           keywords=["guest", "guests", "people", "person", "persons", "capacity",
                     "how many", "kids", "children", "child", "family", "occupancy"],
           response="Our Standard and Deluxe rooms comfortably accommodate two guests, while "
                    "the Executive Suite can host up to four. Children are always welcome! "
                    "Let me know how many people will be staying."),
    Intent("breakfast", "meals & breakfast",
           keywords=["breakfast", "meal", "meals", "eat", "food", "menu", "lunch", "dinner",
                     "restaurant", "dine"],
           response="Yes! {hotel} serves a complimentary breakfast every morning. We also "
                    "offer lunch and dinner at our in-house restaurant."),
    Intent("parking", "parking",
           keywords=["park", "parking", "car", "vehicle", "valet", "garage"],
           response="Yes, we offer free and secure on-site parking for all our guests "
                    "throughout your stay."),
    Intent("security", "safety & security",
           keywords=["safe", "safety", "security", "secure", "guard", "cctv", "gate",
                     "protection"],
           response="Your safety is our priority. {hotel} has 24-hour security, controlled "
                    "access, and secure parking, so you can relax with complete peace of mind."),
    Intent("id_required", "ID requirements",
           keywords=["id", "identification", "passport", "document", "documents", "license",
                     "national id"],
           response="Please bring a valid form of identification, such as a national ID card, "
                    "driver's license, or passport, as it will be required at check-in."),
]

OFF_TOPIC = (
    "I'm sorry, I'm not quite sure about that. Let's focus on your stay \u2014 I can "
    "help you with room prices, room types, booking, location, check-in times, and our "
    "amenities. What would you like to know?"
)
MORE_SPECIFIC = (
    "I want to make sure I help you correctly. Could you be a bit more specific? "
    "It sounds like it might be about {topics}."
)

ABORT_KEYWORDS = {"cancel", "never mind", "nevermind", "stop", "start over",
                  "forget it", "abort", "quit", "no thanks"}
YES_KEYWORDS = {"yes", "yeah", "yep", "yes please", "correct", "sure", "ok", "okay",
                "that's right", "right", "go ahead", "book it", "confirm", "please do",
                "confirmed", "sounds good", "perfect"}
NO_KEYWORDS = {"no", "nope", "wrong", "incorrect", "change", "not right",
               "that's wrong", "don't", "do not"}
ACK_WORDS = {"ok", "okay", "k", "sure", "yes", "yeah", "yep", "cool",
             "alright", "all right", "fine", "got it"}


# --------------------------------------------------------------------------
# Matching helpers
# --------------------------------------------------------------------------
def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_strong(keyword: str) -> bool:
    kw = keyword.strip().lower()
    return (" " in kw) or ("-" in kw) or (kw in STRONG_WORDS)


def _keyword_hits(keywords, norm_text, tokens):
    hits = []
    for kw in keywords:
        kw = kw.strip().lower()
        if not kw:
            continue
        matched = (kw in norm_text) if " " in kw else (kw in tokens)
        if matched:
            hits.append(kw)
    return hits


def analyze(transcript: str):
    norm = _normalize(transcript)
    tokens = set(norm.split())
    scored = []
    for intent in INTENTS:
        hits = _keyword_hits(intent.keywords, norm, tokens)
        if hits:
            scored.append({"intent": intent, "score": len(hits),
                           "has_strong": any(_is_strong(k) for k in hits)})
    return scored


def _best_intent(norm: str):
    scored = analyze(norm)
    if not scored:
        return None
    scored.sort(key=lambda s: (s["score"], s["has_strong"]), reverse=True)
    return scored[0]


def _side_question(norm: str):
    """A strong NON-booking, NON-social intent the guest asked mid-flow."""
    best = _best_intent(norm)
    if not best:
        return None
    if best["intent"].id in ("book",) or best["intent"].social:
        return None
    if best["score"] >= CONFIDENT_HITS or best["has_strong"]:
        return best["intent"]
    return None


def _social_intent(norm: str):
    tokens = set(norm.split())
    for it in INTENTS:
        if it.social and _keyword_hits(it.keywords, norm, tokens):
            return it
    return None


# --------------------------------------------------------------------------
# Sessions (in-memory; one per browser)
# --------------------------------------------------------------------------
def new_session():
    return {"state": "idle", "slot": None, "name": None, "draft": {}, "reference": None}


def reset_session(s):
    s["state"] = "idle"
    s["slot"] = None
    s["draft"] = {}
    s["reference"] = None
    # keep s["name"] so Daven still remembers who they are after a booking


# --------------------------------------------------------------------------
# Slot extractors
# --------------------------------------------------------------------------
QUESTION_TOKENS = {
    "what", "how", "when", "where", "why", "which", "who", "price", "prices",
    "cost", "much", "located", "location", "wifi", "phone", "email", "cancel",
    "book", "booking", "room", "check", "amenities", "breakfast", "parking",
    "pay", "payment", "available", "internet", "contact", "number",
}
NON_NAME_WORDS = {
    "urgent", "important", "fine", "good", "great", "okay", "ok", "awesome",
    "amazing", "terrible", "awful", "serious", "emergency", "crazy", "funny",
    "nice", "cool", "perfect", "true", "false", "ready", "wrong", "right",
    "yes", "no", "maybe", "here", "there", "done", "over",
}

_NAME_PREFIXES = ["my name is", "my name's", "name is", "name's", "the name is",
                  "i am called", "i'm called", "this is", "call me", "i am", "i'm",
                  "it's", "its", "the"]
_FILLERS = {"ok", "okay", "k", "yeah", "yes", "yep", "hi", "hello", "hey",
            "well", "so", "um", "uh", "please", "ah", "oh", "and", "actually"}


def _clean_name(cand):
    """Validate a candidate string into a proper Name, or None."""
    if not cand:
        return None
    words = cand.split()
    if not (1 <= len(words) <= 4):
        return None
    if any(t in QUESTION_TOKENS for t in words):
        return None
    if any(w in NON_NAME_WORDS for w in words):
        return None
    if not all(w.replace("'", "").replace("-", "").isalpha() for w in words):
        return None
    return " ".join(w.capitalize() for w in words)


def _extract_name(norm):
    """Booking-slot extractor: the user is known to be giving a name."""
    toks = norm.split()
    while toks and toks[0] in _FILLERS:   # drop leading 'ok', 'hi', etc.
        toks = toks[1:]
    text = " ".join(toks)
    for p in _NAME_PREFIXES:
        if text.startswith(p + " ") or text == p:
            text = text[len(p):].strip()
            break
    return _clean_name(text)


# Matches "my name is X", "name's X", "call me X", "this is X", "I'm called X"
_NAME_INTRO = re.compile(
    r"(?:my name is|my name's|name is|name's|the name is|call me|"
    r"i am called|i'm called|this is)\s+(.*)")


def _detect_name(norm):
    """Catch a name introduction in idle chat (e.g. 'ok, my name is Destiny')."""
    m = _NAME_INTRO.search(norm)
    if not m:
        return None
    cand = m.group(1).strip()
    cand = re.split(r"\b(and|i want|i'd|i would|i'm|i am|how|what|can you|"
                    r"do you|could you|is there|are there)\b", cand)[0].strip()
    return _clean_name(cand)


_MONTHS = ("january|february|march|april|may|june|july|august|september|october|"
           "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
_MONTH_FULL = {"jan": "January", "feb": "February", "mar": "March", "apr": "April",
               "may": "May", "jun": "June", "jul": "July", "aug": "August",
               "sep": "September", "sept": "September", "oct": "October",
               "nov": "November", "dec": "December",
               "january": "January", "february": "February", "march": "March",
               "april": "April", "june": "June", "july": "July", "august": "August",
               "september": "September", "october": "October", "november": "November",
               "december": "December"}
_WEEKDAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"


def _extract_date(norm):
    toks = norm.split()
    if "today" in toks:
        return "today"
    if "tomorrow" in toks:
        return "tomorrow"
    if "weekend" in norm:
        return "this weekend"
    m = re.search(rf"\bnext ({_WEEKDAYS})\b", norm)
    if m:
        return "next " + m.group(1).capitalize()
    m = re.search(rf"\b({_WEEKDAYS})\b", norm)
    if m:
        return m.group(1).capitalize()
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)? (?:of )?({_MONTHS})\b", norm)
    if m:
        return f"{_MONTH_FULL.get(m.group(2), m.group(2).capitalize())} {m.group(1)}"
    m = re.search(rf"\b({_MONTHS}) (\d{{1,2}})(?:st|nd|rd|th)?\b", norm)
    if m:
        return f"{_MONTH_FULL.get(m.group(1), m.group(1).capitalize())} {m.group(2)}"
    m = re.search(r"\b(\d{1,2})(st|nd|rd|th)\b", norm)
    if m:
        return "the " + m.group(1) + m.group(2)
    return None


def _extract_room(norm):
    if "executive" in norm or "suite" in norm:
        return "Executive Suite"
    if "deluxe" in norm:
        return "Deluxe"
    if "standard" in norm:
        return "Standard"
    return None


_NUMWORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
             "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
             "eleven": "11", "twelve": "12"}


def _extract_guests(norm):
    m = re.search(r"\b(\d{1,2})\b", norm)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 20:
            return str(n)
    for w, val in _NUMWORDS.items():
        if re.search(rf"\b{w}\b", norm):
            return val
    return None


EXTRACTORS = {
    "name": _extract_name,
    "check_in": _extract_date,
    "check_out": _extract_date,
    "room_type": _extract_room,
    "guests": _extract_guests,
}
SLOT_ORDER = ["name", "check_in", "check_out", "room_type", "guests"]


def _next_slot(slot):
    if slot in SLOT_ORDER:
        i = SLOT_ORDER.index(slot)
        return SLOT_ORDER[i + 1] if i + 1 < len(SLOT_ORDER) else "confirm"
    return "confirm"


# --------------------------------------------------------------------------
# Prompts / acknowledgements for the booking flow
# --------------------------------------------------------------------------
def _prompt(slot, draft):
    if slot == "name":
        return "Great! Let's get your booking started. What's your full name?"
    if slot == "check_in":
        return ("What date would you like to check in? You can say something like "
                "'December 25th' or 'tomorrow'.")
    if slot == "check_out":
        return "And what date would you like to check out?"
    if slot == "room_type":
        return (f"Which room would you prefer? We have the Standard at "
                f"{cfg.PRICE_STANDARD}, the Deluxe at {cfg.PRICE_DELUXE}, or the Executive "
                f"Suite at {cfg.PRICE_EXECUTIVE} per night.")
    if slot == "guests":
        return "And how many guests will be staying?"
    return ""


def _ack(slot, value):
    msgs = {
        "name": f"Nice to meet you, {value}.",
        "check_in": f"Noted, checking in {value}.",
        "check_out": f"Great, checking out {value}.",
        "room_type": f"Excellent choice, the {value}.",
        "guests": f"Noted, {value} guest(s).",
    }
    return msgs.get(slot, "")


def _reask(slot):
    msgs = {
        "name": "I didn't quite catch your name. What's your full name?",
        "check_in": "I didn't catch the check-in date. When would you like to check in?",
        "check_out": "Sorry, what date would you like to check out?",
        "room_type": "Which room would you like \u2014 Standard, Deluxe, or Executive Suite?",
        "guests": "How many guests will be staying? Just say a number.",
    }
    return msgs.get(slot, "Could you repeat that?")


def _gen_ref():
    return "CRH-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _summary(draft, ref):
    return (f"Here's your booking summary: {draft['name']}, a {draft['room_type']} room from "
            f"{draft['check_in']} to {draft['check_out']}, for {draft['guests']} guest(s). "
            f"Your reservation reference is {ref}. Shall I go ahead and confirm this booking?")


def _final(draft, ref):
    return (f"All set, {draft['name']}! Your {draft['room_type']} room is booked from "
            f"{draft['check_in']} to {draft['check_out']}. We've sent your confirmation with "
            f"reference {ref} to our front desk. Is there anything else I can help you with?")


def _any_phrase(phrases, norm):
    return any(p in norm for p in phrases)


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------
@dataclass
class Reply:
    text: str
    intent: Optional[str]
    status: str  # ok | vague | off_topic | empty | booking


def respond(transcript: str, session: dict = None) -> Reply:
    session = session if session is not None else new_session()
    norm = _normalize(transcript)

    if not norm:
        return Reply(OFF_TOPIC.format(**CTX), None, "empty")

    # ---- Mid-booking: confirm step -------------------------------------
    if session["state"] == "booking" and session["slot"] == "confirm":
        if _any_phrase(YES_KEYWORDS, norm):
            ref = session["reference"]
            draft = session["draft"]
            text = _final(draft, ref)
            reset_session(session)
            return Reply(text, "book_confirmed", "ok")
        if _any_phrase(NO_KEYWORDS, norm) or _any_phrase(ABORT_KEYWORDS, norm):
            reset_session(session)
            return Reply("No problem, I've cancelled that booking. Is there anything else "
                         "I can help you with?", None, "ok")
        side = _side_question(norm)
        if side:
            return Reply(side.response.format(**CTX) + " So, shall I go ahead and confirm "
                         "this booking?", side.id, "booking")
        return Reply("I just need a yes or no \u2014 shall I go ahead and confirm this "
                     "booking?", None, "booking")

    # ---- Mid-booking: collecting a slot --------------------------------
    if session["state"] == "booking" and session["slot"] in EXTRACTORS:
        if _any_phrase(ABORT_KEYWORDS, norm):
            reset_session(session)
            return Reply("No problem, I've cancelled that booking. Is there anything else "
                         "I can help you with?", None, "ok")

        slot = session["slot"]
        value = EXTRACTORS[slot](norm)
        if value:
            session["draft"][slot] = value
            nxt = _next_slot(slot)
            session["slot"] = nxt
            if nxt == "confirm":
                session["reference"] = _gen_ref()
                return Reply(_ack(slot, value) + " " + _summary(session["draft"],
                             session["reference"]), "book", "booking")
            return Reply(_ack(slot, value) + " " + _prompt(nxt, session["draft"]),
                         "book", "booking")

        side = _side_question(norm)
        social = _social_intent(norm)
        if social:
            return Reply(social.response.format(**CTX) + " " + _reask(slot),
                         social.id, "booking")
        if side:
            return Reply(side.response.format(**CTX) + " " + _reask(slot), side.id, "booking")
        return Reply("I didn't quite catch that. " + _reask(slot), None, "booking")

    # ---- Idle: normal intent matching ----------------------------------
    best = _best_intent(norm)
    confident = bool(best) and (best["score"] >= CONFIDENT_HITS or best["has_strong"])
    name = _detect_name(norm)

    # 1) A confident NON-social intent wins (prices, location, booking, ...).
    if confident and not best["intent"].social:
        if best["intent"].id == "book":
            session["state"] = "booking"
            known = session.get("name") or name  # they may have said it just now
            if known:
                session["draft"]["name"] = known
                session["slot"] = "check_in"
                return Reply(f"Great, {known}! Let's get your booking started. "
                             + _prompt("check_in", session["draft"]), "book", "booking")
            session["slot"] = "name"
            return Reply(_prompt("name", {}), "book", "booking")
        return Reply(best["intent"].response.format(**CTX), best["intent"].id, "ok")

    # 2) A name introduction beats weak / vague / off-topic replies.
    if name:
        session["name"] = name
        return Reply(
            f"Nice to meet you, {name}! I'm {cfg.RECEPTIONIST_NAME} at "
            f"{cfg.HOTEL_NAME}. How can I help you today \u2014 would you like to "
            f"book a room, hear our prices, or ask about our location?",
            "name_intro", "ok")

    # 3) Social (hi / thanks / bye).
    if best and best["intent"].social:
        return Reply(best["intent"].response.format(**CTX), best["intent"].id, "ok")

    # 4) Bare acknowledgment (ok / sure / yes).
    if norm in ACK_WORDS:
        return Reply("Great! How can I help you? You can ask about rooms, prices, "
                     "booking, or our location.", None, "ok")

    # 5) Weak / ambiguous match.
    if best:
        scored = analyze(norm)
        scored.sort(key=lambda s: (s["score"], s["has_strong"]), reverse=True)
        topics = " or ".join(s["intent"].label for s in scored[:2])
        return Reply(MORE_SPECIFIC.format(topics=topics, **CTX), None, "vague")

    # 6) Off-topic.
    return Reply(OFF_TOPIC.format(**CTX), None, "off_topic")


def topics() -> List[str]:
    return [i.label for i in INTENTS if not i.social]


def tags_overview() -> str:
    """Human-readable list of all tags and their keywords (for inspection)."""
    lines = []
    for it in INTENTS:
        tag = "[social] " if it.social else ""
        lines.append(f"{tag}{it.id} ({it.label}): " + ", ".join(it.keywords))
    return "\n".join(lines)


if __name__ == "__main__":
    for q in ["do you have a pool", "is it secure", "do i need id",
              "ok my name is destiny", "how much is a room"]:
        r = respond(q)
        print(f"[{r.status:9}] {q!r:24} -> {r.intent}: {r.text[:50]}")
