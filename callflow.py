"""
V3 -- The Call Flow engine.

A scripted, phone-call-style conversation driven by a state machine. Each turn
the frontend sends an event (start / say / silence / ui / heartbeat) and gets
back Daven's spoken line, the new state, an optional UI trigger (payment options,
payment form, ID card), and the call status (active/ended).

Flow:
  greeting_name -> (ask_title) -> ask_help -> offer_price ->
  ask_payment_method -> collect_payment(stub) -> assign room + ID card ->
  ask_movein -> confirm_movein -> closing (warm) -> ENDED

Silence: if the user doesn't respond, Daven asks "can you hear me?" up to 3 times,
then ends the call with a graceful disconnect message.
"""
import random
import string
import time

import config as cfg
import receptionist as rc


# --------------------------------------------------------------------------
# Gender guess for "Sir" / "Ma"  (extend freely)
# --------------------------------------------------------------------------
FEMALE_NAMES = {
    "ada", "grace", "joy", "mercy", "blessing", "chidinma", "chioma", "ngozi",
    "fatima", "amaka", "tolu", "bisi", "kemi", "folake", "zainab", "aisha",
    "mary", "sarah", "elizabeth", "rachel", "destiny", "faith", "hope", "peace",
    "precious", "patience", "hauwa", "funke", "nneka", "esther", "hannah",
    "anna", "linda", "susan", "glory", "victoria", "cynthia", "jane", "emily",
    "olivia", "sophie", "amina", "hadiza", "balaraba", "titilayo",
}
MALE_NAMES = {
    "daven", "john", "james", "david", "emeka", "chidi", "tunde", "seun", "femi",
    "bayo", "kunle", "ibrahim", "musa", "abdullahi", "yakubu", "emmanuel",
    "samuel", "peter", "paul", "raphael", "michael", "daniel", "joseph",
    "richard", "victor", "henry", "george", "mark", "alex", "chris", "philip",
    "stephen", "andrew", "thomas", "yusuf", "taiwo", "kehinde", "obinna",
    "goodluck", "godwin", "sunday", "francis",
}


def guess_gender(first_name: str):
    n = (first_name or "").strip().lower()
    if n in FEMALE_NAMES:
        return "female"
    if n in MALE_NAMES:
        return "male"
    return None  # unknown -> ask


# --------------------------------------------------------------------------
# Small recognisers
# --------------------------------------------------------------------------
def _norm(t):
    return rc._normalize(t)


def _is_booking(text):
    norm = _norm(text)
    best = rc._best_intent(norm)
    if best and best["intent"].id == "book":
        return True
    return any(w in norm for w in ("book", "reserve", "room", "lodge", "stay", "order"))


def _is_yes(text):
    norm = _norm(text)
    if any(w in norm for w in ("no", "nope", "not", "don't", "cancel")):
        return False
    return any(w in norm for w in ("yes", "yeah", "yep", "sure", "ok", "okay",
                                   "correct", "right", "go ahead", "book it",
                                   "confirm", "please do", "sounds good", "affirm"))


def _is_no(text):
    norm = _norm(text)
    return any(w in norm for w in ("no", "nope", "not really", "later", "maybe", "pass", "don't"))


def _detect_method(text):
    norm = _norm(text)
    if "cheque" in norm or "check" in norm:
        return "Cheque"
    if "transfer" in norm or "bank" in norm:
        return "Transfer"
    if "card" in norm or "credit" in norm or "debit" in norm or "pos" in norm or "atm" in norm:
        return "Card"
    return None


def _detect_gender_word(text):
    norm = _norm(text)
    if any(w in norm for w in ("sir", "mr", "mister", "male", "man", "boy", "guy", "gentleman")):
        return "male"
    if any(w in norm for w in ("ma", "madam", "madame", "ms", "miss", "mrs", "female", "woman", "lady", "girl")):
        return "female"
    return None


def _gen_ref():
    return "CRH-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _gen_room():
    return str(random.randint(101, 419))


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------
def new_call():
    return {
        "state": "greeting_name", "name": None, "title": None, "gender": None,
        "room": None, "ref": None, "method": None, "movein": None,
        "want_booking": False, "silence": 0, "started_at": time.time(),
        "ended": False,
    }


def _ok(call, text, state=None, ui=None, end=False):
    if state:
        call["state"] = state
    if end:
        call["ended"] = True
    return {
        "reply": text, "state": call["state"], "ui": ui,
        "call_status": "ended" if call["ended"] else "active",
        "name": call["name"], "title": call["title"],
        "room": call["room"], "ref": call["ref"], "method": call["method"],
    }


def _price_prompt(call):
    text = (f"Wonderful, {call['title'] or ''}! Our Standard room is "
            f"{cfg.PRICE_STANDARD} per night, and that includes free breakfast and "
            f"free Wi-Fi. Would you like to go ahead and book it?")
    return _ok(call, text, state="offer_price")


def _complete_payment(call):
    """Stub: any payment input is accepted. Assign room + show ID card."""
    call["room"] = _gen_room()
    call["ref"] = _gen_ref()
    ui = {"type": "id_card", "name": call["name"], "room": call["room"],
          "ref": call["ref"], "title": call["title"], "hotel": cfg.HOTEL_NAME}
    return _ok(call,
               f"Payment successful, thank you! Your room number is {call['room']}. "
               f"Congratulations, {call['title']} {call['name']}! When will you be moving in?",
               state="ask_movein", ui=ui)


# --------------------------------------------------------------------------
# State handlers
# --------------------------------------------------------------------------
def _h_greeting_name(call, text):
    name = rc._detect_name(text) or rc._extract_name(text)
    if _is_booking(text):
        call["want_booking"] = True
    if not name:
        return _ok(call, "I'm sorry, I didn't catch your name. Could you say your name again, please?",
                   state="greeting_name")
    call["name"] = name
    g = guess_gender(name.split()[0])
    if g:
        call["gender"] = g
        call["title"] = "Sir" if g == "male" else "Ma"
        if call["want_booking"]:
            return _price_prompt(call)
        return _ok(call, f"Lovely to meet you, {call['title']} {name}. How may I help you today?",
                   state="ask_help")
    call["title"] = None
    return _ok(call, f"Lovely to meet you, {name}. Should I call you Sir or Ma?",
               state="ask_title")


def _h_ask_title(call, text):
    g = _detect_gender_word(text)
    if not g:
        return _ok(call, "I'm sorry, would you prefer I call you Sir or Ma?", state="ask_title")
    call["gender"] = g
    call["title"] = "Sir" if g == "male" else "Ma"
    if call["want_booking"]:
        return _price_prompt(call)
    return _ok(call, f"Thank you, {call['title']}. How may I help you today?", state="ask_help")


def _h_ask_help(call, text):
    if _is_booking(text):
        return _price_prompt(call)
    norm = _norm(text)
    best = rc._best_intent(norm)
    if best and not best["intent"].social:
        ans = best["intent"].response.format(**rc.CTX)
        return _ok(call, ans + f" {call['title']}, would you also like to go ahead and book a room?",
                   state="ask_help")
    return _ok(call, f"{call['title']}, I'm here to help you book a room today. Would you like to book one?",
               state="ask_help")


def _h_offer_price(call, text):
    if _is_yes(text):
        ui = {"type": "payment_options", "options": ["Card", "Transfer", "Cheque"]}
        return _ok(call, f"Great, {call['title']}! How would you like to pay \u2014 by Card, Transfer, or Cheque?",
                   state="ask_payment_method", ui=ui)
    if _is_no(text):
        return _ok(call, "No problem at all. The offer stands whenever you're ready. Would you like to book the room?",
                   state="offer_price")
    return _ok(call, "Would you like to go ahead and book the room?", state="offer_price")


def _h_ask_payment_method(call, text):
    method = _detect_method(text)
    if method:
        return _enter_payment(call, method)
    return _ok(call, "Please choose Card, Transfer, or Cheque.", state="ask_payment_method",
               ui={"type": "payment_options", "options": ["Card", "Transfer", "Cheque"]})


def _enter_payment(call, method):
    call["method"] = method
    return _ok(call, f"You chose {method}. Please enter your payment details on the screen, or just say them.",
               state="collect_payment", ui={"type": "payment_form", "method": method})


def _h_collect_payment(call, text):
    # STUB: any non-empty input (typed card number OR spoken) = successful payment.
    if (text or "").strip():
        return _complete_payment(call)
    return _ok(call, "I didn't catch that. Please enter or say your payment details.",
               state="collect_payment", ui={"type": "payment_form", "method": call.get("method")})


def _h_ui(call, value):
    action = (value or {}).get("action")
    st = call["state"]

    if action == "select_payment" and st == "ask_payment_method":
        method = (value or {}).get("value")
        if method:
            return _enter_payment(call, method)

    if action == "submit_payment" and st == "collect_payment":
        return _complete_payment(call)

    return _ok(call, "I'm here whenever you're ready.", state=st)


def _h_ask_movein(call, text):
    norm = _norm(text)
    date = rc._extract_date(norm)
    if not date:
        stop = ("i", "will", "be", "moving", "in", "on", "at", "the", "by", "im", "move")
        words = [w for w in norm.split() if w not in stop and w.isalpha()]
        date = " ".join(words[:4]).strip() if words else None
    if not date:
        return _ok(call, f"{call['title']}, could you tell me the date you'll be moving in?", state="ask_movein")
    call["movein"] = date
    return _ok(call, f"Perfect, I've got you down for {date}. Is that correct?", state="confirm_movein")


def _h_confirm_movein(call, text):
    if _is_yes(text):
        call["state"] = "closing"
        call["ended"] = True
        msg = (f"Thank you, {call['title']}, for your time. Your room {call['room']} is confirmed "
               f"for {call.get('movein', 'your date')}. We hope to see you soon at {cfg.HOTEL_NAME}. "
               f"If you ever have any issues, you're always free to call this line. Have a wonderful day. Goodbye!")
        return _ok(call, msg, state="closing", end=True)
    return _ok(call, "No problem. What date works for you, then?", state="ask_movein")


# --------------------------------------------------------------------------
# Silence / disconnect handling
# --------------------------------------------------------------------------
def _h_silence(call):
    if call["ended"]:
        return {"reply": "", "call_status": "ended", "state": call["state"]}
    call["silence"] += 1
    n = call["silence"]
    if n == 1:
        return _ok(call, "Hello? Do I confirm you can hear me?", state=call["state"])
    if n == 2:
        return _ok(call, "I'm still here... can you hear me?", state=call["state"])
    call["state"] = "closing"
    return _ok(call, "Ok, looks like you've disconnected. I'll have to end the call. "
                     "Please try again with a better connection. Goodbye!",
               state="closing", end=True)


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------
GREETING = ("Hello, good day! My name is {rec}, calling from {hotel}. "
            "Can I know your name, please?")


def handle_call(call, event, value=None, transcript=None):
    """Process one call event and return a response dict."""
    if event == "start":
        call["silence"] = 0
        return _ok(call, GREETING.format(rec=cfg.RECEPTIONIST_NAME, hotel=cfg.HOTEL_NAME),
                   state="greeting_name")

    if event == "heartbeat":
        return {"tick": random.randint(1000, 9999),
                "call_status": "ended" if call["ended"] else "active",
                "state": call["state"]}

    if event == "end":
        call["ended"] = True
        call["state"] = "closing"
        return {"reply": "", "call_status": "ended", "state": call["state"]}

    if event == "silence":
        return _h_silence(call)

    if event == "ui":
        return _h_ui(call, value)

    if event == "say":
        if call["ended"]:
            return _ok(call, "This call has ended. Please start a new call to talk again.",
                       state="closing")
        call["silence"] = 0  # user responded -> reset the silence counter
        st = call["state"]
        handlers = {
            "greeting_name": _h_greeting_name,
            "ask_title": _h_ask_title,
            "ask_help": _h_ask_help,
            "offer_price": _h_offer_price,
            "ask_payment_method": _h_ask_payment_method,
            "collect_payment": _h_collect_payment,
            "ask_movein": _h_ask_movein,
            "confirm_movein": _h_confirm_movein,
        }
        h = handlers.get(st)
        if h:
            return h(call, transcript or "")
        return _ok(call, "I'm sorry, could you repeat that?", state=st)

    return _ok(call, "I'm sorry, I didn't catch that.", state=call["state"])


def summary(call):
    return {
        "name": call["name"], "title": call["title"], "room": call["room"],
        "ref": call["ref"], "method": call["method"], "movein": call["movein"],
    }


if __name__ == "__main__":
    print("=== simulated call (typed + UI) ===")
    c = new_call()
    print("DAVEN:", handle_call(c, "start")["reply"])
    steps = [
        ("say", "my name is Grace"),
        ("say", "i'd like to book a room"),
        ("say", "yes please"),
        ("ui", {"action": "select_payment", "value": "Card"}),
        ("ui", {"action": "submit_payment", "value": "4242424242424242"}),
        ("say", "december 25th"),
        ("say", "yes"),
    ]
    for ev, val in steps:
        r = handle_call(c, ev, value=val if ev == "ui" else None,
                        transcript=val if ev == "say" else None)
        label = val if ev == "say" else f"[UI {val}]"
        print(f"\nYOU: {label}\nDAVEN: {r['reply']}")
        if r.get("ui"):
            print("   [UI]", r["ui"])
        if r["call_status"] == "ended":
            print("   --- call ended ---")
            print("   SUMMARY:", summary(c))
            break
