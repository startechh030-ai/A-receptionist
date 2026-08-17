# AI Receptionist -- deployable on Render
FROM python:3.11-slim

# ffmpeg lets faster-whisper decode webm/ogg/mp3/wav audio from the browser
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides PORT. Bind to 0.0.0.0 so the service is reachable.
ENV PORT=10000
EXPOSE 10000

# 1 worker = 1 copy of the Whisper model in RAM. threads=4 for concurrency.
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120"]
