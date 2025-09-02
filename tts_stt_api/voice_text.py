from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import pyttsx3
import wave
import soundfile as sf
import base64
from vosk import Model, KaldiRecognizer
import asyncio

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#vosk_model = Model("tts_stt_api\vosk-model-small-en-us-0.15")  # path to vosk model folder

@app.get("/")
async def sayHello():
    return JSONResponse(status_code=200, content={"message" : "Hi this working"})


# TTS: Text to Speech
@app.post("/tts/")
async def tts(text: str = Form(...)):
    await asyncio.sleep(1)

    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    # Try setting a female voice
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():  # 'Zira' is a common female voice on Windows
            engine.setProperty('voice', voice.id)
            break

    filename = f"audio_temp/tts_{uuid.uuid4()}.mp3"
    engine.save_to_file(text, filename)
    engine.runAndWait()

    with open(filename, "rb") as f:
        audio_data = f.read()
    encoded = base64.b64encode(audio_data).decode("utf-8")

    return JSONResponse(content={"text": text, "audio_base64": encoded})
