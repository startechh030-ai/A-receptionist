# 🏷️ Tags — what Daven understands

Daven is **semi-AI**: it matches what the guest says against **tags** (groups of
keywords). Each tag has a ready-made reply. If a guest uses any of a tag's
keywords, that tag is a candidate.

## The tags (and their keywords)

**Social** (answered on a single word):
- `greeting` → hi, hello, hey, hiya, good morning/afternoon/evening, good day, greetings, how are you
- `thanks` → thank, thanks, appreciate, cheers, grateful
- `goodbye` → bye, goodbye, see you, later, that's all, nothing else, good night

**Hotel topics:**
- `price` → price, cost, how much, rate, fee, charge, expensive, cheap, affordable, budget, per night, tariff
- `room_types` → room, room type, suite, deluxe, executive, standard, options, categories
- `book` → book, booking, reserve, reservation, order, availability, i want to stay, book a room
- `check_in` → check in, check-in, arrival, arrive, when can i check in, early
- `check_out` → check out, check-out, departure, leave, late checkout
- `location` → location, where, address, directions, how do i get, map, landmark, near, nearby
- `amenities` → amenities, facility, facilities, features, services, what's included
- `wifi` → wifi, wi-fi, internet, connection, data, hotspot, network
- `contact` → phone, call, contact, number, reach, whatsapp, email, front desk
- `payment` → pay, payment, card, cash, transfer, pos, deposit, method
- `confirmation` → confirm, confirmation, booking number, reference, status, receipt
- `cancel` → cancel, cancellation, refund, change, reschedule, modify, postpone
- `pets` → pet, dog, cat, animal
- `guests` → guest, people, person, capacity, how many, kids, children, family
- `breakfast` → breakfast, meal, food, menu, lunch, dinner, restaurant
- `parking` → park, parking, car, vehicle, valet, garage
- `security` → safe, safety, security, guard, cctv, gate
- `id_required` → id, identification, passport, document, license

**Plus a smart name detector:** "my name is X", "call me X", "this is X", "I'm
called X" → Daven greets them by name and remembers it for the booking.

## How matching decides what to reply

| What the guest said | Daven's response |
|---|---|
| 2+ keywords of one tag, **or** 1 strong keyword | Answers that tag ✅ |
| Only 1 weak keyword | "Could you be more specific — sounds like X or Y" |
| No tag matched | "Let's focus on your stay…" (off-topic) |
| A name intro | "Nice to meet you, X!" |
| "I want to book…" | Starts the booking flow |

## Add your own tag

Open `receptionist.py`, find the `INTENTS` list, and copy any block:

```python
Intent(
    "pool_hours",                       # unique id
    "pool opening hours",               # label (shown in "be more specific")
    keywords=["pool hours", "pool", "swim", "pool time", "pool open"],
    response="Our pool is open daily from 7 AM to 9 PM.",
),
```
That's it — restart the app and Daven now understands it.
