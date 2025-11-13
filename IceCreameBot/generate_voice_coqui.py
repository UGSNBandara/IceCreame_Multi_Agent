"""
Coqui TTS voice generator (no FastAPI, no DB).
- Uses multi-speaker model: tts_models/en/vctk/vits
- Default speaker: "p225"
- Edit TEXT and FILENAME below and run the script.
- Output will be saved as Voices/<FILENAME>.wav

First time will download the model (~50–200 MB).
"""

from pathlib import Path
from TTS.api import TTS

# ====== EDIT THESE VALUES ======
TEXT = "Welcome to MoodScoop! This voice is generated with Coqui TTS VCTK speaker p225."
FILENAME = "coqui_p225_test"  # without extension
SPEAKER = "p225"              # VCTK speaker ID
MODEL_NAME = "tts_models/en/vctk/vits"
# ===================================

def main():
    voices_dir = Path("Voices")
    voices_dir.mkdir(exist_ok=True)
    out_path = voices_dir / f"{FILENAME}.wav"

    print("Loading model... this downloads (~50-200 MB) on first run, may take 30-90s")
    # gpu=False makes it safe on machines without CUDA
    tts = TTS(MODEL_NAME, progress_bar=True, gpu=False)

    # Generate and save audio
    tts.tts_to_file(text=TEXT, speaker=SPEAKER, file_path=str(out_path))

    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
