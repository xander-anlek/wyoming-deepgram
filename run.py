#!/usr/bin/env python3
"""Main entrypoint for Wyoming-Deepgram bridge. Starts both STT and TTS servers."""

import asyncio
import logging
from functools import partial

from wyoming.info import AsrModel, AsrProgram, Attribution, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncServer

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


def build_stt_info() -> Info:
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
    )


def build_tts_info() -> Info:
    return Info(
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


async def main() -> None:
    if not DEEPGRAM_API_KEY:
        _LOGGER.warning(
            "DEEPGRAM_API_KEY not set! Servers will start but transcription/synthesis will fail."
        )

    stt_info = build_stt_info()
    tts_info = build_tts_info()

    stt_server = AsyncServer.from_uri(f"tcp://0.0.0.0:{STT_PORT}")
    tts_server = AsyncServer.from_uri(f"tcp://0.0.0.0:{TTS_PORT}")

    _LOGGER.info("Starting Deepgram STT server on port %d", STT_PORT)
    _LOGGER.info("Starting Deepgram TTS server on port %d", TTS_PORT)

    await asyncio.gather(
        stt_server.run(partial(DeepgramSttHandler, stt_info)),
        tts_server.run(partial(DeepgramTtsHandler, tts_info)),
    )


if __name__ == "__main__":
    asyncio.run(main())
