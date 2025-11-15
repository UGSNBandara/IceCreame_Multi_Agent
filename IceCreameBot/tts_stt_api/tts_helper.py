# tts_helper.py
import os, tempfile, base64, asyncio, concurrent.futures, platform
import pyttsx3

_tts_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_tts_lock = asyncio.Lock()  # pyttsx3 isn't thread-safe

def _init_engine():
    try:
        if platform.system() == "Linux":
            return pyttsx3.init(driverName="espeak")
        return pyttsx3.init()
    except Exception as e:
        raise

def _tts_blocking(text: str) -> bytes:
    engine = _init_engine()
    # Try to pick Zira (female voice on Windows) or any female voice
    try:
        voices = engine.getProperty("voices")
        selected_voice = None
        for v in voices:
            n = (v.name or "").lower()
            if "zira" in n:
                selected_voice = v
                break
            elif "female" in n or "woman" in n:
                selected_voice = v
        if selected_voice:
            engine.setProperty("voice", selected_voice.id)
    except Exception:
        pass

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        engine.save_to_file(text, path)
        engine.runAndWait()
        with open(path, "rb") as f:
            return f.read()
    finally:
        try: engine.stop()
        except Exception: pass
        try: os.remove(path)
        except Exception: pass

async def tts_async(text: str, voice: str = "en-US-JennyNeural") -> tuple[str, str]:
    """Return (audio_base64, mime) using pyttsx3 for offline TTS.

    Requires eSpeak/eSpeak-ng on Linux. Ensure it's installed in the container.
    """
    loop = asyncio.get_running_loop()
    audio_bytes = await loop.run_in_executor(_tts_pool, _tts_blocking, text)
    return base64.b64encode(audio_bytes).decode("utf-8"), "audio/wav"

async def tts_save_to_file(text: str, filename: str, voice: str = "en-US-JennyNeural") -> str:
    """Generate TTS audio using pyttsx3 and save to Voices folder. Returns the file path."""
    from pathlib import Path

    voices_dir = Path("Voices")
    voices_dir.mkdir(exist_ok=True)

    filepath = voices_dir / f"{filename}.wav"

    loop = asyncio.get_running_loop()
    audio_bytes = await loop.run_in_executor(_tts_pool, _tts_blocking, text)

    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    return str(filepath)


async def edge_tts_save_to_file(text: str, filename: str, voice: str = "en-US-JennyNeural") -> tuple[str, str]:
    """
    Generate TTS using Microsoft Edge online neural voices and save to Voices as MP3.
    Returns (filepath, mime). Requires `pip install edge-tts` and internet access.

    Popular female voices examples:
      - en-US-JennyNeural, en-US-AriaNeural
      - en-GB-SoniaNeural, en-GB-LibbyNeural
    Full list: https://github.com/rany2/edge-tts#voices
    """
    try:
        import edge_tts  # lazy import so module remains usable without it
    except Exception as e:
        raise RuntimeError(
            "edge-tts is not installed. Run 'pip install edge-tts' in your environment."
        ) from e

    from pathlib import Path

    voices_dir = Path("Voices")
    voices_dir.mkdir(exist_ok=True)
    out_path = voices_dir / f"{filename}.mp3"

    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(str(out_path))

    return str(out_path), "audio/mpeg"
