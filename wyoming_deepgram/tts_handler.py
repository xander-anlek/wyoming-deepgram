"""Wyoming TTS handler wrapping Deepgram text-to-speech API."""

import asyncio
import io
import logging
import re
import struct
from typing import Optional

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import Synthesize

from .const import DEEPGRAM_API_KEY, TTS_MODEL, TTS_OUTPUT_SAMPLE_RATE

_LOGGER = logging.getLogger(__name__)

SAMPLES_PER_CHUNK = 1024


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS reads clean text."""
    # Remove bold/italic markers: **text**, *text*, __text__, _text_
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove strikethrough: ~~text~~
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    # Remove inline code: `text`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove code blocks: ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove headers: # Header
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove links: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove images: ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    # Remove bullet points: - item, * item
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered lists: 1. item
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove blockquotes: > text
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules: --- or ***
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines/spaces
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


class DeepgramTtsHandler(AsyncEventHandler):
    """Handle TTS events from Wyoming clients (Home Assistant)."""

    def __init__(self, wyoming_info: Info, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info = wyoming_info
        self.wyoming_info_event = wyoming_info.event()

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if not Synthesize.is_type(event.type):
            return True

        synthesize = Synthesize.from_event(event)
        text = synthesize.text.strip()
        if not text:
            _LOGGER.warning("Empty text for TTS")
            return True

        # Strip markdown syntax that LLMs tend to include
        text = _strip_markdown(text)

        _LOGGER.info("Synthesizing: %s", text)

        try:
            audio_bytes = await self._synthesize(text)
            if not audio_bytes:
                _LOGGER.warning("No audio returned from Deepgram TTS")
                return True

            # Send audio back to Wyoming client
            await self.write_event(
                AudioStart(
                    rate=TTS_OUTPUT_SAMPLE_RATE,
                    width=2,
                    channels=1,
                ).event()
            )

            # Send in chunks
            chunk_size = SAMPLES_PER_CHUNK * 2  # 2 bytes per sample (16-bit)
            offset = 0
            while offset < len(audio_bytes):
                chunk = audio_bytes[offset : offset + chunk_size]
                await self.write_event(
                    AudioChunk(
                        audio=chunk,
                        rate=TTS_OUTPUT_SAMPLE_RATE,
                        width=2,
                        channels=1,
                    ).event()
                )
                offset += chunk_size

            await self.write_event(AudioStop().event())
            _LOGGER.debug("TTS audio sent: %d bytes", len(audio_bytes))

        except Exception:
            _LOGGER.exception("Deepgram TTS synthesis failed")

        return True

    async def _synthesize(self, text: str) -> Optional[bytes]:
        """Call Deepgram TTS API and return raw PCM audio bytes."""
        if not DEEPGRAM_API_KEY:
            _LOGGER.error("DEEPGRAM_API_KEY not set")
            return None

        try:
            import aiohttp

            url = f"https://api.deepgram.com/v1/speak?model={TTS_MODEL}&encoding=linear16&sample_rate={TTS_OUTPUT_SAMPLE_RATE}&container=none"

            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {"text": text}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "Deepgram TTS error %d: %s", resp.status, error_text
                        )
                        return None

                    audio_data = await resp.read()
                    _LOGGER.debug("Received %d bytes from Deepgram TTS", len(audio_data))
                    return audio_data

        except Exception:
            _LOGGER.exception("Deepgram TTS request failed")
            return None
