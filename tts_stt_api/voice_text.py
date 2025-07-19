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
    
    text_to_send = "Hi, how Can i help you today. Do you wana test new ice cream"
    engine = pyttsx3.init()
    filename = f"tts_{uuid.uuid4()}.mp3"
    engine.save_to_file(text_to_send, filename)
    engine.runAndWait()

    
    with open(filename, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")

    os.remove(filename)  # optional cleanup

    return JSONResponse({
        "text": text_to_send,
        "audio_base64": audio_data
    })

# STT: Speech to Text
'''
@app.post("/stt/")
async def stt(file: UploadFile = File(...)):
    original_path = f"audio_{uuid.uuid4()}_{file.filename}"
    wav_path = original_path.replace(".mp3", ".wav")

    # Save uploaded audio file
    with open(original_path, "wb") as f:
        f.write(await file.read())

    # Convert to mono WAV format if needed
    try:
        data, samplerate = sf.read(original_path)
        sf.write(wav_path, data, samplerate, subtype='PCM_16')
    except:
        return JSONResponse(status_code=400, content={"error": "Audio conversion failed"})

    # STT with Vosk
    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in [8000, 16000, 44100]:
        return JSONResponse(status_code=400, content={"error": "Unsupported audio format"})

    recognizer = KaldiRecognizer(vosk_model, wf.getframerate())
    results = []

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            results.append(result)

    final_result = recognizer.FinalResult()
    results.append(final_result)

    # Clean up
    wf.close()
    os.remove(original_path)
    os.remove(wav_path)

    # Extract only the final text
    import json
    transcript = " ".join([json.loads(r).get("text", "") for r in results])
    return {"text": transcript.strip()}
'''