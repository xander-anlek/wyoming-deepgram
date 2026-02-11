#!/usr/bin/env python3
"""Main entrypoint for Wyoming-Deepgram bridge. Runs STT + TTS on a single port."""

import asyncio
import logging
from functools import partial

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import AsrModel, AsrProgram, Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.asr import Transcript
from wyoming.tts import Synthesize

from wyoming_deepgram import __version__
from wyoming_deepgram.const import (
    DEEPGRAM_API_KEY,
    STT_MODEL,
    STT_PORT,
    TTS_MODEL,
    TTS_OUTPUT_SAMPLE_RATE,
    TTS_PORT,
)
from wyoming_deepgram.stt_handler import DeepgramSttHandler
from wyoming_deepgram.tts_handler import DeepgramTtsHandler

_LOGGER = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if __import__("os").environ.get("DEBUG") else logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)


def build_combined_info() -> Info:
    """Build Info advertising both STT and TTS capabilities."""
    return Info(
        asr=[
            AsrProgram(
                name="deepgram",
                description="Deepgram Nova speech-to-text",
                attribution=Attribution(
                    name="Deepgram", url="https://deepgram.com"
                ),
                installed=True,
                version=__version__,
                models=[
                    AsrModel(
                        name=STT_MODEL,
                        description=f"Deepgram {STT_MODEL}",
                        attribution=Attribution(
                            name="Deepgram", url="https://deepgram.com"
                        ),
                        installed=True,
                        languages=["en"],
                        version=__version__,
                    )
                ],
            )
        ],
        tts=[
            TtsProgram(
                name="deepgram",
                description="Deepgram Aura text-to-speech",
                attribution=Attribution(
                    name="Deepgram", url="https://deepgram.com"
                ),
                installed=True,
                version=__version__,
                voices=[
                    TtsVoice(
                        name=TTS_MODEL,
                        description=f"Deepgram {TTS_MODEL}",
                        attribution=Attribution(
                            name="Deepgram", url="https://deepgram.com"
                        ),
                        installed=True,
                        languages=["en"],
                        version=__version__,
                    )
                ],
            )
        ],
    )


class DeepgramCombinedHandler(AsyncEventHandler):
    """Routes events to either STT or TTS handler based on event type."""

    def __init__(self, wyoming_info: Info, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info = wyoming_info
        self.wyoming_info_event = wyoming_info.event()
        # Lazy-init sub-handlers
        self._stt = DeepgramSttHandler(wyoming_info, *args, **kwargs)
        self._tts = DeepgramTtsHandler(wyoming_info, *args, **kwargs)
        # Track current mode
        self._mode = None  # "stt" or "tts"

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            _LOGGER.debug("Sent combined info (STT + TTS)")
            return True

        # Route to TTS if we get a Synthesize event
        if Synthesize.is_type(event.type):
            self._mode = "tts"
            self._tts.writer = self.writer
            return await self._tts.handle_event(event)

        # Route to STT for audio events
        if AudioStart.is_type(event.type):
            self._mode = "stt"
            self._stt.writer = self.writer
            return await self._stt.handle_event(event)

        if AudioChunk.is_type(event.type) or AudioStop.is_type(event.type):
            if self._mode == "stt":
                self._stt.writer = self.writer
                return await self._stt.handle_event(event)
            elif self._mode == "tts":
                self._tts.writer = self.writer
                return await self._tts.handle_event(event)

        return True


async def main() -> None:
    if not DEEPGRAM_API_KEY:
        _LOGGER.warning(
            "DEEPGRAM_API_KEY not set! Server will start but transcription/synthesis will fail."
        )

    combined_info = build_combined_info()
    COMBINED_PORT = STT_PORT  # Use STT_PORT as the single port (default 10300)

    server = AsyncServer.from_uri(f"tcp://0.0.0.0:{COMBINED_PORT}")

    _LOGGER.info(
        "Starting Deepgram Wyoming server (STT + TTS) on port %d", COMBINED_PORT
    )

    await server.run(partial(DeepgramCombinedHandler, combined_info))


if __name__ == "__main__":
    asyncio.run(main())
