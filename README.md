# Wyoming-Deepgram

A [Wyoming protocol](https://github.com/rhasspy/wyoming) bridge for [Deepgram](https://deepgram.com) Speech-to-Text and Text-to-Speech. Deploy as a Docker container and connect to Home Assistant via the Wyoming integration.

## Features

- **STT** (port 10300): Streams audio to Deepgram Nova-2 for transcription
- **TTS** (port 10200): Sends text to Deepgram Aura for speech synthesis
- Single container runs both servers
- Designed for Home Assistant Wyoming integration

## Quick Start

1. Get a [Deepgram API key](https://console.deepgram.com/)

2. Create a `.env` file:
   ```
   DEEPGRAM_API_KEY=your_key_here
   ```

3. Run with Docker Compose:
   ```bash
   docker compose up -d
   ```

4. In Home Assistant, add two Wyoming integrations:
   - **STT**: `host:10300`
   - **TTS**: `host:10200`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPGRAM_API_KEY` | (required) | Your Deepgram API key |
| `STT_MODEL` | `nova-2` | Deepgram STT model |
| `TTS_MODEL` | `aura-asteria-en` | Deepgram TTS voice/model |
| `TTS_SAMPLE_RATE` | `24000` | Deepgram TTS sample rate |
| `STT_PORT` | `10300` | STT server port |
| `TTS_PORT` | `10200` | TTS server port |
| `DEBUG` | unset | Set to any value for debug logging |

## Run Without Docker

```bash
pip install -r requirements.txt
DEEPGRAM_API_KEY=your_key python3 run.py
```

## How It Works

- **STT**: Collects audio chunks from Home Assistant, sends as a batch to Deepgram's REST API, returns the transcript via Wyoming protocol.
- **TTS**: Receives text from Home Assistant, calls Deepgram's TTS REST API requesting raw PCM (linear16, 16kHz), streams audio chunks back via Wyoming protocol.

## License

MIT
