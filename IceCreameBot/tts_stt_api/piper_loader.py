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

BIN_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
BIN_DIR = os.path.join(BASE_DIR, "piper_bin")  # extraction directory (read-only may be possible)
BIN_TAR = os.path.join(BIN_DIR, "piper_linux_x86_64.tar.gz")
BIN_PATH = os.path.join(BIN_DIR, "piper")
RUN_DIR = "/tmp/piper_run"  # runtime copy to ensure executable mount
RUN_BIN_PATH = os.path.join(RUN_DIR, "piper")

MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
MODEL_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
MODELS_DIR = os.path.join(BASE_DIR, "piper_models")
MODEL_PATH = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx")
MODEL_JSON_PATH = os.path.join(MODELS_DIR, "en_US-lessac-medium.onnx.json")

_prepare_lock = asyncio.Lock()
_prepared = False

def _find_piper_executable(root: str) -> str:
    for dirpath, dirnames, filenames in os.walk(root):
        if "piper" in filenames:
            return os.path.join(dirpath, "piper")
    raise FileNotFoundError("Piper executable not found after extraction")

async def _download(url: str, dest: str, timeout: int = 180) -> None:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)

async def _ensure_binary() -> None:
    os.makedirs(BIN_DIR, exist_ok=True)
    # Download tarball if needed and extract (idempotent)
    if not os.path.exists(BIN_TAR):
        await _download(BIN_URL, BIN_TAR)
    with tarfile.open(BIN_TAR, "r:gz") as tf:
        tf.extractall(BIN_DIR)

    # Locate the actual piper executable within extracted contents
    piper_src = _find_piper_executable(BIN_DIR)
    # Source root for libs/configs alongside binary
    src_root = os.path.dirname(piper_src)

    # Prepare runtime dir under /tmp
    if not os.path.exists(RUN_DIR):
        os.makedirs(RUN_DIR, exist_ok=True)
    # Copy full source root contents into RUN_DIR (preserve structure)
    for entry in os.listdir(src_root):
        src_path = os.path.join(src_root, entry)
        dst_path = os.path.join(RUN_DIR, entry)
        if os.path.isdir(src_path):
            if not os.path.exists(dst_path):
                shutil.copytree(src_path, dst_path)
        else:
            if not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
    # Compute runtime binary path (handle nested layouts)
    rel_bin = os.path.relpath(piper_src, src_root)
    runtime_bin = os.path.join(RUN_DIR, rel_bin)
    try:
        os.chmod(runtime_bin, 0o755)
    except Exception:
        pass
    # Update global run bin path
    global RUN_BIN_PATH
    RUN_BIN_PATH = runtime_bin

async def _ensure_model() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        await _download(MODEL_URL, MODEL_PATH)
    if not os.path.exists(MODEL_JSON_PATH):
        await _download(MODEL_JSON_URL, MODEL_JSON_PATH)

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
    cmd = [RUN_BIN_PATH, "--model", MODEL_PATH, "--output_file", out_path]
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
    cmd = [RUN_BIN_PATH, "--model", MODEL_PATH, "--output_file", out_path]
    proc = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"Piper failed: {proc.stderr.decode(errors='ignore')}")
    return out_path