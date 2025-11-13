"""
Simple TTS generator script using Edge TTS (no FastAPI, no DB).
- Requires: pip install edge-tts
- Default voice: en-US-JennyNeural (female)
- Edit TEXT and FILENAME below and run the script.
- Output will be saved as Voices/<FILENAME>.mp3
"""

import asyncio
from tts_stt_api.tts_helper import tts_save_to_file

# ====== EDIT THESE VALUES ======
TEXT = "Welcome to MoodScoop! This voice is generated with Edge TTS."
FILENAME = "welcome_edge_test"  # without extension
VOICE = "en-US-JennyNeural"     # female voice
# ===================================

async def main():
    path = await tts_save_to_file(TEXT, FILENAME, VOICE)
    print(f"Saved: {path}")

if __name__ == "__main__":
    asyncio.run(main())