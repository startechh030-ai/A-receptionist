# 🏨 Daven — AI Receptionist (Semi-AI voice bot)

A simple, fast, **semi-AI** hotel receptionist for **City Resort Hotel**.

- 🎙️ **STT** — listens to the guest with `faster-whisper` (tiny model)
- 🗣️ **TTS** — replies out loud with a **male voice** ("Daven")
- 🏷️ **Tag/intent engine** — matches what the guest said to ready-made replies (no big AI, just like you asked)
- 🌐 **Flask backend**, Docker-ready, deploys to **Render**
- 💬 **Test frontend** included (voice + typing) — swap it for your own UI anytime

---

## How the "AI" works (the tag system)

It is **not** a language model. It is predictable and editable:

1. Guest speaks → Whisper turns it into text.
2. The text is matched against **tags** (groups of keywords) in `receptionist.py`.
3. A reply is chosen:

| Situation | What Daven does |
|---|---|
| Confident match (2+ keywords, or 1 strong keyword) | Answers that topic ✅ |
| Only 1 weak / ambiguous match | *"Could you be more specific…"* |
| No tag matched / off-topic | *"Let's go back to your booking…"* |
| Hi / thanks / bye | Answers directly ✅ |

Topics covered: room prices, room types, booking, check-in/out, location, amenities, Wi-Fi, contact, payment, confirmation, cancellation, pets, guests, breakfast, parking, security, ID.

---

## Project layout

```
ai-receptionist/
├── app.py              # Flask app + API routes
├── receptionist.py     # 🧠 The tag/intent engine + knowledge base (EDIT THIS)
├── stt.py              # Speech-to-text (faster-whisper)
├── tts.py              # Text-to-speech (male voice + gTTS fallback)
├── config.py           # 🏷️ All hotel info in ONE place (EDIT THIS)
├── static/index.html   # Test frontend (voice + text)
├── requirements.txt
├── Dockerfile
├── render.yaml         # Render Blueprint
└── .env.example
```

---

## 1. Edit your hotel details

Open **`config.py`** (or set env vars) and replace the placeholders with the **real** info:
hotel name, location, phone, email, check-in/out times, **room prices**, amenities, payment methods.

---

## 2. Run locally

```bash
cd ai-receptionist
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

> The first run downloads the Whisper "tiny" model (~75 MB). The browser needs
> `localhost` or HTTPS to allow the microphone — localhost works for dev.

---

## 3. Deploy to Render (Docker)

1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service → connect your repo → Runtime: Docker**.
3. **Important:** use a plan with **≥ 1 GB RAM** (e.g. *Standard*). The 512 MB
   free/starter tier will run out of memory loading Whisper.
4. (Optional) Add env vars from `.env.example` in **Environment**, or use
   `render.yaml` via **New → Blueprint**.
5. Deploy. Health check: `GET /api/health`.

Render gives you an HTTPS URL automatically — the mic works there.

---

## API (for your own frontend)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET  | `/api/health` | – | `{status, hotel, receptionist}` |
| GET  | `/api/greeting` | – | greeting `text` + base64 `audio` (play when "connected") |
| POST | `/api/chat` | `multipart/form-data` field `audio` | `transcript`, `reply`, `intent`, `status`, base64 `audio` |
| POST | `/api/text` | `{ "text": "..." }` | `reply`, `intent`, `status`, base64 `audio` (typing fallback) |
| POST | `/api/reset` | `X-Session-Id` header | clears the session (start a fresh booking) |
| GET  | `/api/topics` | – | `{ topics: [...] }` |

Reply audio is base64 MP3. Play it with:
`new Audio("data:audio/mpeg;base64," + data.audio).play()`

If your frontend is on a **different domain**, calls are CORS-enabled already.

---

## Changing the voice

`config.py` → `TTS_PROVIDER` + `TTS_VOICE`. Default is **edge-tts** with
`en-US-GuyNeural` (a natural US male voice). Other good male Edge voices:

- `en-US-GuyNeural`, `en-US-AndrewNeural`, `en-US-DavisNeural` (US male)
- `en-GB-RyanNeural`, `en-GB-ThomasNeural` (UK male)
- `en-NG-AbeoNeural` (**Nigerian accent** — a nice local touch)

edge-tts is free and needs no API key. If it's ever unavailable, the app
automatically falls back to Google TTS (gTTS) so the demo never goes silent.

> Note: "Matthew" isn't available on the key-free Edge voices, so `en-US-GuyNeural`
> is used as the closest equivalent. (StreamElements voices now require a key —
> set `TTS_PROVIDER=streamelements` + `TTS_SE_KEY` only if you have one.)

---

## Notes & next steps

- **Whisper accuracy:** "tiny" is fastest but least accurate. For a sharper ear,
  set `STT_MODEL=base` (more RAM needed).
- **Adding topics:** add a new `Intent(...)` block in `receptionist.py`.
- **Multi-turn booking collection** (asking name → dates → confirm in sequence)
  can be added later with a small per-session memory — kept out of v1 to stay simple.
# A-receptionist
# A-receptionist
