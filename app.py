import os
import uuid
import asyncio

import requests

import websockets
from fastrtc import (ReplyOnPause, Stream, get_stt_model,
                     get_tts_model, AdditionalOutputs)
from fastapi import FastAPI, WebSocket, Request, Response, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
import json
import telnyx
from telnyx import Event, Call, Message
import base64
import librosa
from pydantic import BaseModel
import aiohttp

load_dotenv()
telnyx.api_key = os.environ.get("TELNYX_API_KEY")
telnyx.public_key = os.environ.get("TELNYX_PUBLIC_KEY")
MESSAGING_PROFILE = os.environ.get("MESSAGING_PROFILE")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER")
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS")
WEBSOCKET_SERVER = f"wss://{SERVER_ADDRESS}/ws"
FASTRTC_SERVER = f"wss://{SERVER_ADDRESS}/websocket/offer"
MODEL = os.environ.get("MODEL")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")


class InputData(BaseModel):
    webrtc_id: str
    sample_rate: int = 24000


llm = init_chat_model(
    model=MODEL, base_url=OLLAMA_BASE_URL
)
stt_model = get_stt_model()
tts_model = get_tts_model()

chat_history = []


def agent(user_message):
    chat_history.append(user_message)
    response = llm.invoke(chat_history)
    prompt = response.content
    ai_message = {"role": "ai", "content": prompt}
    chat_history.append(ai_message)
    return ai_message


def talk(audio, target_sr: int = 24000):
    prompt = stt_model.stt(audio)
    print(f"{prompt=}")
    user_message = {"role": "user", "content": prompt}
    yield AdditionalOutputs(user_message)
    ai_message = agent(user_message)
    print(f"{ai_message['content']=}")
    yield AdditionalOutputs(ai_message)
    yield AdditionalOutputs({"role": "speech", "state": "starting"})
    for audio_chunk in tts_model.stream_tts_sync(ai_message["content"]):
        orig_sr, audio = audio_chunk
        if orig_sr == target_sr:
            yield audio_chunk
        else:
            down_sampled = librosa.resample(
                audio, orig_sr=orig_sr, target_sr=target_sr)
            yield target_sr, down_sampled
    yield AdditionalOutputs({"role": "speech", "state": "completed"})


def startup():
    prompt = "Hi! I am an AI Agent. How can I help you?"
    ai_message = {"role": "ai", "content": prompt}
    chat_history.append(ai_message)
    yield AdditionalOutputs(ai_message)
    yield AdditionalOutputs({"role": "speech", "state": "starting"})
    for chunk in tts_model.stream_tts_sync(prompt):
        yield chunk
    yield AdditionalOutputs({"role": "speech", "state": "completed"})


stream = Stream(ReplyOnPause(talk),  # startup_fn=startup),
                modality="audio", mode="send-receive")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
stream.mount(app)

# Optional: Add routes


@app.get("/")
async def _():
    return HTMLResponse(content=open("index.html").read())


@app.post("/input_hook")
def input_hook(data: InputData):
    print(f"Input Hook: {data=}")
    stream.set_input(data.webrtc_id, data.sample_rate)


@app.get("/outputs")
async def stream_updates(webrtc_id: str):
    async def output_stream():
        async for output in stream.output_stream(webrtc_id):
            print(f"{output.args[0]=}")
            # Output is the AdditionalOutputs instance
            # Be sure to serialize it however you would like
            yield f"data: {json.dumps(output.args[0])}\n\n"

    return StreamingResponse(
        output_stream(),
        media_type="text/event-stream"
    )


@app.post("/webhooks")
async def hooks(request: Request, response: Response):
    body = await request.body()
    body = body.decode("utf-8")
    signature = request.headers.get("Telnyx-Signature-ed25519", None)
    timestamp = request.headers.get("Telnyx-Timestamp", None)
    host = request.headers.get('Host')

    # print(f"{signature=},{timestamp=}")
    # print(f"{body=}")
    try:
        event_data = telnyx.Webhook.construct_event(
            body, signature, timestamp)
    except ValueError:
        print("Error while decoding event!")
        response.status_code = 400
        return "Bad payload"
    except telnyx.error.SignatureVerificationError:
        print("Invalid signature!")
        response.status_code = 400
        return "Bad signature"

    # print(f"{event_data=}")
    event = Event.construct_from(event_data["data"], telnyx.api_key)
    # print(f"{event=}")
    print("Received event: id={id}, type={type}".format(
        id=event.id, type=event.event_type))
    if event.event_type == "message.received":
        print(f"{event=}")
        to_address = event.payload["from_"]["phone_number"]
        text = event.payload["text"]
        resp = Message.create(
            messaging_profile_id=MESSAGING_PROFILE,
            from_=PHONE_NUMBER,
            to=to_address,
            text=f"Hello, World! {text}",
            subject="From Telnyx!",
            type="SMS"
        )
        print(f"{resp=}")
    if event.event_type == "call.initiated":
        call = Call()
        call_control_id = event.payload["call_control_id"]
        # print(f"{call=}")
        # print(f"{call.payload=}")
        # Call.reject(call.payload, command_id="123", cause="USER_BUSY")
        direction = event.payload["direction"]
        print(f"{call_control_id=},{direction=}")
        call.call_control_id = call_control_id

        if direction == "incoming":
            encoded_client_state = base64.b64encode(
                direction.encode("ascii"))
            client_state_str = str(encoded_client_state, 'utf-8')
            print(f"{WEBSOCKET_SERVER=}")
            resp = call.answer(client_state=client_state_str,
                               stream_url=WEBSOCKET_SERVER,
                               stream_bidirectional_mode="rtp",
                               stream_track="inbound_track")
            print(f"{resp=}")

    response.status_code = 200
    return ""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("Websocket connection established")
    await websocket.accept()
    websocket_id = str(uuid.uuid4())
    print(f"{websocket_id=}")
    try:
        async with websockets.connect(FASTRTC_SERVER) as rtc:
            await rtc.send(json.dumps({"event": "start", "websocket_id": websocket_id}))

            async def receive_rtc_messages():
                async for message in rtc:
                    try:
                        response = json.loads(message)
                        if "event" in response:
                            if response["event"] == "media":
                                await websocket.send_text(message)
                        else:
                            print(f"From FreeRTC: {message=}")
                            if response["type"] == "send_input":
                                async with aiohttp.ClientSession() as session:
                                    resp = await session.post(
                                        f"https://{SERVER_ADDRESS}/input_hook",
                                        json={
                                            "webrtc_id": websocket_id,
                                            "sample_rate": 8000
                                        }
                                    )
                                    print(f"{resp=}")
                    except Exception as _e:
                        print(f"""
                        Error processing FastRTC response: {str(_e)},
                        Raw message: {message}""")

            async def receive_ws_messages():
                stop = False
                while not stop:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    # print(f"WebSocket: {data=}")
                    event_type = message["event"]
                    if event_type != "media":
                        print(f"From Telnyx: {message=}")
                    if event_type == "media":
                        # print("Sending to server...")
                        await rtc.send(data)
                    elif event_type == "start":
                        stream_sid = message["stream_id"]
                        print(f"Incoming stream has started: {stream_sid}")
                    else:
                        print(f"Received non-media event: {event_type}")
                    stop = "stop" == "event_type"
            await asyncio.gather(receive_ws_messages(),
                                 receive_rtc_messages())
    except WebSocketDisconnect:
        print("Call disconnected")
    except Exception as e:
        print("WebSocket error: ", e)
# uvicorn app:app --host 0.0.0.0 --port 8000
