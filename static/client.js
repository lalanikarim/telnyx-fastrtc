let connectionStatus = document.querySelector("span#connectionStatus");
let wave = document.querySelector("div.wave");
let processing = document.querySelector("div.processing");
let messagesContainer = document.querySelector("div#messagesContainer");
let chatNameContainer = document.querySelector(
    "div.chat-container .user-bar .name",
);
let powerButton = document.querySelector("button#power");
let presetsSelect = document.querySelector("select#presets");
let modelsSelect = document.querySelector("select#models");
let startRecordDiv = document.querySelector("div.circle.start");
let stopRecordDiv = document.querySelector("div.circle.stop");
let waitRecordDiv = document.querySelector("div.circle.wait");
let cameraImg = document.querySelector("div.photo i");
let fileInput = document.querySelector("div.file input[type=file]");
let pc;
let dc;

function getcconnectionstatus() {
    let status = "closed";
    if (pc) {
        status = pc.connectionState;
    }
    connectionStatus.textContent = status;
}

async function negotiate() {
    //pc.addTransceiver('audio', { direction: 'sendrecv' });
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    let webrtc_id = Math.random().toString(36).substring(7);

    // Send ICE candidates to server
    // (especially needed when server is behind firewall)
    pc.onicecandidate = ({ candidate }) => {
        if (candidate) {
            console.debug("Sending ICE candidate", candidate);
            fetch("/webrtc/offer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    candidate: candidate.toJSON(),
                    webrtc_id: webrtc_id,
                    type: "ice-candidate",
                }),
            });
        }
    };

    // Send offer to server
    const response = await fetch("/webrtc/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            sdp: offer.sdp,
            type: offer.type,
            webrtc_id: webrtc_id,
        }),
    });

    // Handle server response
    const serverResponse = await response.json();
    await pc.setRemoteDescription(serverResponse);

    const eventSource = new EventSource(
        "/outputs?webrtc_id=" + webrtc_id,
    );
    eventSource.onmessage = (event) => {
        console.log(`event: ${event.data}`);
        const eventJson = JSON.parse(event.data);

        if (eventJson.role == "user" || eventJson.role == "ai") {
            // showStatus("Query Sent. Processing...");
            logmessage(eventJson);
        }
        if (eventJson.role == "speech") {
            hideElement(processing);
            if (eventJson.state == "starting") {
                showElement(wave);
            } else {
                hideElement(wave);
            }
            // showStatus("Response Received. Ready for conversation.");
        }
    };
}

async function start() {
    stop();
    toggleMic("starting");

    const config = {
        sdpSemantics: "unified-plan",
    };

    if (document.getElementById("use-stun").checked) {
        config.iceServers = [{ urls: ["stun:stun.l.google.com:19302"] }];
    }

    pc = new RTCPeerConnection(config);
    pc.onconnectionstatechange = (ev) => {
        getcconnectionstatus();
    };
    dc = pc.createDataChannel("chat");
    dc.onopen = (ev) => {
        console.log("Data channel is open and ready to use");
        dc.send("Hello server");
    };
    dc.onmessage = (ev) => {
        console.log("Received message: " + ev.data);
        eventJson = JSON.parse(ev.data);
        if (eventJson.type === "log") {
            if (eventJson.data === "started_talking") {
                hideElement(processing);
            }
            if (eventJson.data === "pause_detected") {
                showElement(processing);
            }
            if (eventJson.data === "response_starting") {
                hideElement(processing);
                showElement(wave);
            }
        }
    };
    dc.onclose = () => {
        console.log("Data channel is closed");
    };

    // connect audio / video
    pc.ontrack = (ev) => {
        console.log("Received remote stream");
        document.querySelector("audio#remoteAudio").srcObject = ev.streams[0];
    };
    // Adding tracks
    // stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))
    // document.querySelector('button#start').style.display = 'none';
    //negotiate()
    await getMedia();
    showElement(chatNameContainer);
    showElement(presetsSelect);
    showElement(modelsSelect);
    showElement(messagesContainer);
    showElement(cameraImg);
    toggleMic("on");
    //document.querySelector('button#stop').style.display = 'inline-block';
}
function logmessage(message) {
    const log = document.querySelector("div.conversation-container");
    console.log(message);
    const messageText = message.content;
    if (messageText.trim().length > 0) {
        const newMessage = document.createElement("div");
        newMessage.classList.add("message");
        if (
            message.role === "user"
        ) {
            newMessage.classList.add("sent");
        } else {
            newMessage.classList.add("received");
        }
        newMessage.textContent = messageText;
        log.appendChild(newMessage);
        log.scrollTop = log.scrollHeight;
    }
}
async function getMedia() {
    const constraints = {
        audio: true,
        video: false,
    };
    const stream = await navigator.mediaDevices
        .getUserMedia(constraints);
    await handleSuccess(stream);
    //.catch(handleFailure);
}

function toggleMic(state) {
    switch (state) {
        case "on":
            hideElement(startRecordDiv);
            hideElement(waitRecordDiv);
            showElement(stopRecordDiv);
            break;
        case "off":
            hideElement(stopRecordDiv);
            hideElement(waitRecordDiv);
            showElement(startRecordDiv);
            break;
        default:
            hideElement(startRecordDiv);
            hideElement(stopRecordDiv);
            showElement(waitRecordDiv);
    }
}

function stop() {
    toggleMic("stopping");
    hideElement(chatNameContainer);
    hideElement(presetsSelect);
    hideElement(modelsSelect);
    hideElement(cameraImg);
    if (pc) {
        // close peer connection
        toggleMic("off");
        setTimeout(() => {
            pc.close();
            getcconnectionstatus();
            pc = null;
            dc = null;
        }, 500);
    }
}
async function handleSuccess(stream) {
    const tracks = stream.getAudioTracks();
    console.log("Received: ", tracks.length, " tracks");
    stream = stream;
    stream.getAudioTracks().forEach((track) => {
        pc.addTrack(track);
    });
    await negotiate();
}

function handleFailure(error) {
    console.log("navigator.getUserMedia error: ", error);
}

function showElement(element) {
    if (element) {
        element.classList.remove("d-none");
    }
}
function hideElement(element) {
    if (element) {
        element.classList.add("d-none");
    }
}

function changePreset() {
    let preset = document.querySelector("select#presets").value;
    dc.send("preset:" + preset);
}
function changeModel() {
    let model = document.querySelector("select#models").value;
    dc.send("model:" + model);
    chatNameContainer.textContent = model;
}

document.addEventListener("DOMContentLoaded", () => {
    getcconnectionstatus();
    startRecordDiv.onclick = async () => {
        if (pc && pc.connectionState === "connected") {
            stop();
            powerButton.classList.remove("text-danger");
            powerButton.classList.add("text-success");
        } else {
            await start();
            powerButton.classList.remove("text-success");
            powerButton.classList.add("text-danger");
        }
    };
    fileInput.addEventListener("change", (ev) => {
        console.log(`Files: ${ev.target.files.length}`);
        if (ev.target.files.length > 0) {
            let photo = ev.target.files[0];
            const fileName = photo.name;
            photo
                .arrayBuffer()
                .then((buffer) => processPhotoUpload(fileName, buffer));
        }
    });
});
