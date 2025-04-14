from fastapi import FastAPI, Request, Response, WebSocket
from dotenv import load_dotenv
import telnyx
from telnyx import Event, Call
import os
import base64
import json

load_dotenv()

telnyx.api_key = os.environ.get("TELNYX_API_KEY")
telnyx.public_key = os.environ.get("TELNYX_PUBLIC_KEY")
WEBSOCKET_SERVER = os.environ.get("WEBSOCKET_SERVER")

print(f"{telnyx.api_key=},{telnyx.public_key=}")
print("Getting User Balance")

resp = telnyx.Balance.retrieve()

print("Your available credit: {} {}".format(
    resp.available_credit, resp.currency))
print(resp)
app = FastAPI()


@app.get("/")
def index(request: Request, response: Response):
    response.status_code = 200
    return {"hello": "world"}


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
    stop = False
    while not stop:
        data = await websocket.receive_text()
        event = json.loads(data)
        print(f"WebSocket: {data=}")
        stop = "stop" in event
