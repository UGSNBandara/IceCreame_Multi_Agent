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

async def tts_async(text: str, voice: str = "en-US-JennyNeural") -> tuple[str, str]:
    """Return (audio_base64, mime) for the given text using Edge TTS."""
    try:
        import edge_tts  # lazy import
    except Exception as e:
        raise RuntimeError(
            "edge-tts is not installed. Run 'pip install edge-tts' in your environment."
        ) from e

    async with _tts_lock:
        loop = asyncio.get_running_loop()
        # Use edge_tts instead of pyttsx3
        communicate = edge_tts.Communicate(text, voice=voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

    return base64.b64encode(audio_bytes).decode("utf-8"), "audio/mpeg"

async def tts_save_to_file(text: str, filename: str, voice: str = "en-US-JennyNeural") -> str:
    """Generate TTS audio using Edge TTS and save to Voices folder. Returns the file path."""
    try:
        import edge_tts  # lazy import
    except Exception as e:
        raise RuntimeError(
            "edge-tts is not installed. Run 'pip install edge-tts' in your environment."
        ) from e

    from pathlib import Path

    voices_dir = Path("Voices")
    voices_dir.mkdir(exist_ok=True)  # Ensure directory exists

    filepath = voices_dir / f"{filename}.mp3"  # Changed to .mp3

    async with _tts_lock:
        communicate = edge_tts.Communicate(text, voice=voice)
        await communicate.save(str(filepath))

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
