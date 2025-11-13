"""
Simple Edge TTS generator script (no FastAPI, no DB).
- Requires: pip install edge-tts
- Default voice: en-US-JennyNeural (female)
- Edit TEXT / FILENAME / VOICE below and run the script.
- Output saved as Voices/<FILENAME>.mp3
"""

import asyncio
from tts_stt_api.tts_helper import edge_tts_save_to_file

# ====== EDIT THESE VALUES ======
TEXT = "Welcome to MoodScoop! How can I assist you today?"
FILENAME = "edge_jenny_test"   # without extension
VOICE = "en-US-JennyNeural"
# ===================================

async def main():
    path, mime = await edge_tts_save_to_file(TEXT, FILENAME, VOICE)
    print(f"Saved: {path} ({mime})")

if __name__ == "__main__":
    asyncio.run(main())
