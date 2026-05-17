import asyncio
import json
import os
import struct
import uuid
from pathlib import Path

from aiohttp import web, ClientSession

OPTIONS_FILE = "/data/options.json"
CONFIG_WWW = "/config/www"
HA_API = "http://supervisor/core/api"
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2   # bytes, 16-bit
CHANNELS = 1

sessions: dict[str, list[tuple[int, bytes]]] = {}


def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


def wav_header(pcm_len: int) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + pcm_len,
        b"WAVE",
        b"fmt ",
        16,
        1,                                          # PCM
        CHANNELS,
        SAMPLE_RATE,
        SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH,      # byte rate
        CHANNELS * SAMPLE_WIDTH,                    # block align
        SAMPLE_WIDTH * 8,                           # bits per sample
        b"data",
        pcm_len,
    )
