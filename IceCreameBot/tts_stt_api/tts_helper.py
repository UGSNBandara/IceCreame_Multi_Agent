# tts_helper.py
import os, tempfile, base64, asyncio, concurrent.futures
import pyttsx3

_tts_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_tts_lock = asyncio.Lock()  # pyttsx3 isn't thread-safe

def _tts_blocking(text: str) -> bytes:
    engine = pyttsx3.init()
    # Try to pick a female voice (e.g., "Zira" on Windows)
    try:
        for v in engine.getProperty("voices"):
            n = (v.name or "").lower()
            if "female" in n or "zira" in n:
                engine.setProperty("voice", v.id)
                break
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

async def tts_async(text: str) -> tuple[str, str]:
    """Return (audio_base64, mime) for the given text."""
    async with _tts_lock:
        loop = asyncio.get_running_loop()
        audio_bytes = await loop.run_in_executor(_tts_pool, _tts_blocking, text)
    return base64.b64encode(audio_bytes).decode("utf-8"), "audio/wav"
