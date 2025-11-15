import os
import asyncio
import base64
import gzip
import shutil
import time
from typing import Tuple

import requests
from piper import PiperVoice

# Simple Piper loader: downloads and caches model on first use.
# Using en_US-lessac-medium as a balanced female voice.

MODEL_URL = "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.gz"
MODELS_DIR = os.path.join(os.path.dirname(__file__), "piper_models")
MODEL_GZ = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx.gz")
MODEL_PATH = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx")

_voice = None
_load_lock = asyncio.Lock()

async def ensure_model() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        if not os.path.exists(MODEL_GZ):
            resp = requests.get(MODEL_URL, timeout=120)
            resp.raise_for_status()
            with open(MODEL_GZ, "wb") as f:
                f.write(resp.content)
        with gzip.open(MODEL_GZ, "rb") as fin, open(MODEL_PATH, "wb") as fout:
            shutil.copyfileobj(fin, fout)

async def get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        async with _load_lock:
            if _voice is None:
                t0 = time.time()
                await ensure_model()
                _voice = PiperVoice.load(MODEL_PATH)
                print(f"Piper model loaded in {time.time() - t0:.2f}s")
    return _voice

async def synthesize(text: str) -> Tuple[str, str]:
    voice = await get_voice()
    wav_bytes = voice.synthesize(text)
    b64 = base64.b64encode(wav_bytes).decode()
    return b64, "audio/wav"

async def synthesize_to_file(text: str, filename: str) -> str:
    voice = await get_voice()
    wav_bytes = voice.synthesize(text)
    target_dir = os.path.join(os.path.dirname(__file__), "Voices")
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f"{filename}.wav")
    with open(path, "wb") as f:
        f.write(wav_bytes)
    return path