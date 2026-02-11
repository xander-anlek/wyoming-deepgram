"""Constants and defaults for Wyoming-Deepgram."""

import os

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")

STT_MODEL = os.environ.get("STT_MODEL", "nova-2")
TTS_MODEL = os.environ.get("TTS_MODEL", "aura-asteria-en")
TTS_SAMPLE_RATE = int(os.environ.get("TTS_SAMPLE_RATE", "24000"))
TTS_OUTPUT_SAMPLE_RATE = 16000  # What HA/Wyoming expects

STT_PORT = int(os.environ.get("STT_PORT", "10300"))
TTS_PORT = int(os.environ.get("TTS_PORT", "10200"))
