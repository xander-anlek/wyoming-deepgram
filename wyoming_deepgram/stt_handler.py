"""Wyoming STT handler wrapping Deepgram streaming transcription."""

import asyncio
import logging
from typing import Optional

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.asr import Transcript

from .const import DEEPGRAM_API_KEY, STT_MODEL, STT_KEYWORDS

_LOGGER = logging.getLogger(__name__)


class DeepgramSttHandler(AsyncEventHandler):
    """Handle STT events from Wyoming clients (Home Assistant)."""

    def __init__(self, wyoming_info: Info, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info = wyoming_info
        self.wyoming_info_event = wyoming_info.event()
        self.audio_buffer = bytearray()
        self.sample_rate: int = 16000
        self.sample_width: int = 2
        self.channels: int = 1

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent info")
            return True

        if AudioStart.is_type(event.type):
            audio_start = AudioStart.from_event(event)
            self.sample_rate = audio_start.rate
            self.sample_width = audio_start.width
            self.channels = audio_start.channels
            self.audio_buffer = bytearray()
            _LOGGER.debug(
                "Audio start: rate=%s, width=%s, channels=%s",
                self.sample_rate,
                self.sample_width,
                self.channels,
            )
            return True

        if AudioChunk.is_type(event.type):
            chunk = AudioChunk.from_event(event)
            self.audio_buffer.extend(chunk.audio)
            return True

        if AudioStop.is_type(event.type):
            _LOGGER.debug(
                "Audio stop, buffer size: %d bytes", len(self.audio_buffer)
            )
            transcript = await self._transcribe()
            _LOGGER.info("Transcript: %s", transcript)
            await self.write_event(Transcript(text=transcript).event())
            self.audio_buffer = bytearray()
            return True

        return True

    async def _transcribe(self) -> str:
        """Send buffered audio to Deepgram for transcription."""
        if not self.audio_buffer:
            return ""

        if not DEEPGRAM_API_KEY:
            _LOGGER.error("DEEPGRAM_API_KEY not set")
            return ""

        try:
            import aiohttp

            url = f"https://api.deepgram.com/v1/listen?model={STT_MODEL}&encoding=linear16&sample_rate={self.sample_rate}&channels={self.channels}"

            # Add keywords/keyterms for boosted recognition
            # Nova-3+ uses "keyterm", Nova-2 and earlier use "keywords"
            param_name = "keyterm" if STT_MODEL.startswith("nova-3") else "keywords"
            for kw in STT_KEYWORDS:
                url += f"&{param_name}={kw}"

            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/octet-stream",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, data=bytes(self.audio_buffer)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "Deepgram STT error %d: %s", resp.status, error_text
                        )
                        return ""

                    result = await resp.json()
                    transcript = (
                        result.get("results", {})
                        .get("channels", [{}])[0]
                        .get("alternatives", [{}])[0]
                        .get("transcript", "")
                    )
                    return transcript

        except Exception:
            _LOGGER.exception("Deepgram STT transcription failed")
            return ""
