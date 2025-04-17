import os

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

load_dotenv()
telnyx.api_key = os.environ.get("TELNYX_API_KEY")
telnyx.public_key = os.environ.get("TELNYX_PUBLIC_KEY")
MESSAGING_PROFILE = os.environ.get("MESSAGING_PROFILE")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER")
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS")
WEBSOCKET_SERVER = os.environ.get(f"wss://{SERVER_ADDRESS}/ws")
FASTRTC_SERVER = os.environ.get(f"https://{SERVER_ADDRESS}/webrtc/offer")
MODEL = os.environ.get("MODEL")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")

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


def talk(audio):
    prompt = stt_model.stt(audio)
    user_message = {"role": "user", "content": prompt}
    yield AdditionalOutputs(user_message)
    ai_message = agent(user_message)
    yield AdditionalOutputs(ai_message)
    yield AdditionalOutputs({"role": "speech", "state": "starting"})
    for audio_chunk in tts_model.stream_tts_sync(prompt):
        yield audio_chunk
    yield AdditionalOutputs({"role": "speech", "state": "completed"})


stream = Stream(ReplyOnPause(talk), modality="audio", mode="send-receive")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
stream.mount(app)

# Optional: Add routes


@app.get("/")
async def _():
    return HTMLResponse(content=open("index.html").read())


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
            resp = call.answer(client_state=client_state_str,
                               stream_url=WEBSOCKET_SERVER, stream_track="both_tracks")
            print(f"{resp=}")

    response.status_code = 200
    return ""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async with websockets.connect(FASTRTC_SERVER) as server:

            pass
    except WebSocketDisconnect:
        print("Call disconnected")
    except Exception as e:
        print("WebSocket error: ", e)
    stop = False
    while not stop:
        data = await websocket.receive_text()
        event = json.loads(data)
        print(f"WebSocket: {data=}")
        stop = "stop" in event
# uvicorn app:app --host 0.0.0.0 --port 8000
