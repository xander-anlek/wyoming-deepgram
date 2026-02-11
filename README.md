# Wyoming-Deepgram

A [Wyoming protocol](https://github.com/rhasspy/wyoming) bridge for [Deepgram](https://deepgram.com) Speech-to-Text and Text-to-Speech. Deploy as a Docker container and connect to [Home Assistant](https://www.home-assistant.io/) via the Wyoming integration.

Both STT and TTS run on a **single port** — one Wyoming integration entry in Home Assistant gives you both services.

## Features

- 🎤 **Speech-to-Text** — Deepgram Nova-2/Nova-3 with custom keyword/keyterm boosting
- 🔊 **Text-to-Speech** — Deepgram Aura voices
- 🔌 **Single port** — Both STT and TTS on one Wyoming connection (port 10300)
- 🏠 **Home Assistant native** — Auto-discovered via Wyoming protocol
- 🐳 **Docker ready** — One container, minimal config

## Quick Start

### 1. Get a Deepgram API Key

Sign up at [console.deepgram.com](https://console.deepgram.com/) — new accounts get **$200 in free credits**.

### 2. Deploy with Docker Compose

Create a `.env` file:

```env
DEEPGRAM_API_KEY=your_key_here
```

Run:

```bash
docker compose up -d
```

The server starts on port **10300** and advertises both STT and TTS capabilities.

### 3. Connect to Home Assistant

1. Go to **Settings → Devices & Services**
2. Click **Add Integration** → search for **Wyoming Protocol**
3. Enter:
   - **Host:** IP address of the machine running the container (e.g., `localhost` if on the same machine as HA, or the machine's LAN/Tailscale IP)
   - **Port:** `10300`
4. Click **Submit**

Home Assistant will discover both **Deepgram Speech-to-Text** and **Deepgram Text-to-Speech** from this single connection.

### 4. Set Up a Voice Pipeline

1. Go to **Settings → Voice Assistants**
2. Click **Add Assistant** (or edit an existing one)
3. Set:
   - **Speech-to-Text:** Deepgram Speech-to-Text
   - **Text-to-Speech:** Deepgram Text-to-Speech
   - **Conversation Agent:** Your preferred agent (e.g., OpenAI, OpenRouter, built-in)
4. Save

You can now use this pipeline with any voice satellite, the Voice PE, or the HA mobile app's Assist feature.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPGRAM_API_KEY` | *(required)* | Your Deepgram API key |
| `STT_MODEL` | `nova-2` | Deepgram STT model (`nova-2`, `nova-3`, etc.) |
| `TTS_MODEL` | `aura-asteria-en` | Deepgram TTS voice ([available voices](https://developers.deepgram.com/docs/tts-models)) |
| `STT_PORT` | `10300` | Server port (both STT and TTS) |
| `STT_KEYWORDS` | *(empty)* | Comma-separated keywords for boosted recognition (see below) |
| `DEBUG` | *(unset)* | Set to any value for debug logging |

## Custom Keywords

Deepgram can boost recognition of specific words — useful for names, brands, or non-standard terms. Spell them exactly how you want them transcribed:

```env
STT_KEYWORDS=MyBrand,CustomWord,PlaceName
```

- **Nova-2** uses the `keywords` API parameter
- **Nova-3** uses the `keyterm` API parameter

The bridge auto-detects which to use based on your `STT_MODEL`.

## Deepgram Pricing

Both STT and TTS are very affordable for home assistant use:

| Service | Cost | With $200 free credits |
|---------|------|----------------------|
| STT (Nova-2) | ~$0.0036/min | ~55,000 minutes |
| STT (Nova-3) | ~$0.0043/min | ~46,000 minutes |
| TTS (Aura) | $0.03/1K chars | ~6.6M characters |

For a voice assistant with short commands and responses, credits last a very long time.

## Run Without Docker

```bash
pip install -r requirements.txt
DEEPGRAM_API_KEY=your_key python3 run.py
```

## How It Works

The bridge runs a single Wyoming protocol server that handles both STT and TTS:

- **STT flow:** Home Assistant sends `AudioStart` → `AudioChunk` (PCM audio) → `AudioStop`. The handler buffers the audio and sends it to Deepgram's REST API for transcription, returning a `Transcript` event.
- **TTS flow:** Home Assistant sends a `Synthesize` event with text. The handler calls Deepgram's TTS API for raw PCM audio and streams it back as `AudioChunk` events.

Events are automatically routed to the correct handler based on type.

## Architecture

```
Voice Input (mic/satellite)
    ↓ audio
┌─────────────────────────┐
│  Wyoming-Deepgram       │
│  (port 10300)           │
│                         │
│  STT: audio → Deepgram  │
│        Nova API → text  │
│                         │
│  TTS: text → Deepgram   │
│        Aura API → audio │
└─────────────────────────┘
    ↕ Wyoming protocol
Home Assistant Assist Pipeline
    ↕
Conversation Agent (LLM)
```

## Private Registry Deployment

If you're running a private Docker registry (e.g., for air-gapped or local deployments):

```bash
# Build and push
docker build -t your-registry:5000/wyoming-deepgram:latest .
docker push your-registry:5000/wyoming-deepgram:latest

# Update docker-compose.yml to use your registry image
# Add to /etc/docker/daemon.json if using HTTP:
# { "insecure-registries": ["your-registry:5000"] }
```

## Troubleshooting

**Container starts but STT/TTS fails:**
- Check logs: `docker logs wyoming-deepgram`
- Verify `DEEPGRAM_API_KEY` is set and valid
- Ensure the container can reach `api.deepgram.com` (outbound HTTPS)

**HA doesn't discover the services:**
- Verify the container is running: `docker ps`
- Check the port is accessible from HA: `curl -v telnet://container-ip:10300`
- Try removing and re-adding the Wyoming integration in HA

**Keywords error with Nova-3:**
- Nova-3 uses `keyterm` instead of `keywords` — the bridge handles this automatically. Make sure you're running the latest image.

**"Object of type time is not JSON serializable" error:**
- This is a Home Assistant conversation agent bug (not related to this bridge). Try restarting HA or updating to the latest version.

## License

MIT
