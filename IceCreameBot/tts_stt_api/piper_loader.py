import os
import asyncio
import base64
import gzip
import shutil
import tarfile
import subprocess
import time
from typing import Tuple

import requests

# Piper binary approach (no python package) for Python 3.13 compatibility.
# Downloads Linux x86_64 binary + model on first use. Intended for Railway (Linux).

IS_LINUX = os.name == "posix"
BASE_DIR = os.path.dirname(__file__)

BIN_URL = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_x86_64.tar.gz"
BIN_DIR = os.path.join(BASE_DIR, "piper_bin")
BIN_TAR = os.path.join(BIN_DIR, "piper_linux_x86_64.tar.gz")
BIN_PATH = os.path.join(BIN_DIR, "piper")

MODEL_URL = "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.gz"
MODELS_DIR = os.path.join(BASE_DIR, "piper_models")
MODEL_GZ = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx.gz")
MODEL_PATH = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx")

_prepare_lock = asyncio.Lock()
_prepared = False

async def _download(url: str, dest: str, timeout: int = 180) -> None:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)

async def _ensure_binary() -> None:
    os.makedirs(BIN_DIR, exist_ok=True)
    if not os.path.exists(BIN_PATH):
        if not os.path.exists(BIN_TAR):
            await _download(BIN_URL, BIN_TAR)
        # extract tar
        with tarfile.open(BIN_TAR, "r:gz") as tf:
            tf.extractall(BIN_DIR)
        # after extract, binary might be inside 'piper_linux_x86_64' directory
        inner = os.path.join(BIN_DIR, "piper_linux_x86_64", "piper")
        if os.path.exists(inner):
            shutil.move(inner, BIN_PATH)
            shutil.rmtree(os.path.join(BIN_DIR, "piper_linux_x86_64"), ignore_errors=True)
        os.chmod(BIN_PATH, 0o755)

async def _ensure_model() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        if not os.path.exists(MODEL_GZ):
            await _download(MODEL_URL, MODEL_GZ)
        with gzip.open(MODEL_GZ, "rb") as fin, open(MODEL_PATH, "wb") as fout:
            shutil.copyfileobj(fin, fout)

async def prepare() -> None:
    global _prepared
    if _prepared:
        return
    async with _prepare_lock:
        if _prepared:
            return
        if not IS_LINUX:
            raise RuntimeError("Piper binary TTS only supported on Linux in this setup.")
        t0 = time.time()
        await _ensure_binary()
        await _ensure_model()
        _prepared = True
        print(f"Piper binary + model prepared in {time.time() - t0:.2f}s")

async def synthesize(text: str) -> Tuple[str, str]:
    await prepare()
    # Run Piper via subprocess, feeding text through stdin.
    # Output wav stored in temporary file then read.
    tmp_dir = os.path.join(BASE_DIR, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    out_path = os.path.join(tmp_dir, "out.wav")
    # Remove any previous file
    try:
        if os.path.exists(out_path):
            os.remove(out_path)
    except Exception:
        pass
    cmd = [BIN_PATH, "--model", MODEL_PATH, "--output_file", out_path]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"Piper failed: {proc.stderr.decode(errors='ignore')}")
    with open(out_path, "rb") as f:
        wav_bytes = f.read()
    b64 = base64.b64encode(wav_bytes).decode()
    return b64, "audio/wav"

async def synthesize_to_file(text: str, filename: str) -> str:
    await prepare()
    voices_dir = os.path.join(BASE_DIR, "Voices")
    os.makedirs(voices_dir, exist_ok=True)
    out_path = os.path.join(voices_dir, f"{filename}.wav")
    cmd = [BIN_PATH, "--model", MODEL_PATH, "--output_file", out_path]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"Piper failed: {proc.stderr.decode(errors='ignore')}")
    return out_path