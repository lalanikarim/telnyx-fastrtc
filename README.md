# Telnyx FastRTC Demo

## Overview
This is a proof-of-concept (POC) project integrating **Telnyx** with **FastRTC** to build a real-time voice chat application powered by AI. The project leverages WebRTC for real-time audio communication and LangChain for AI-driven conversational capabilities.

## Features
- **Real-Time Voice Chat**: Stream audio between users using WebRTC.
- **AI-Powered Conversations**: Process audio input to generate AI responses using LangChain and text-to-speech models.
- **Telnyx Integration**: Handles Telnyx webhook events for SMS and call control.
- **Web-Based Interface**: A simple front-end interface to interact with the AI and monitor WebRTC connection status.

## Components
1. **Backend (app.py)**:
   - Built with FastAPI.
   - Manages WebRTC signaling, Telnyx webhooks, and AI processing.
   - Utilizes FastRTC for seamless audio streaming.
   - Handles Telnyx webhook events for SMS and call logic.

2. **Frontend (index.html)**:
   - A responsive web interface for initiating conversations.
   - Displays WebRTC connection status and chat history with AI.

3. **Client-Side Logic (static/client.js)**:
   - Manages WebRTC peer connections and data channels.
   - Handles audio input/output and communicates with the backend for AI responses.

## Requirements
- Python 3.8+
- Node.js (for front-end development, optional)
- Environment variables:
  - `TELNYX_API_KEY`: Telnyx API key.
  - `TELNYX_PUBLIC_KEY`: Telnyx public key.
  - `MESSAGING_PROFILE`: Telnyx Messaging Profile ID.
  - `PHONE_NUMBER`: Telnyx phone number.
  - `SERVER_ADDRESS`: Public server address.
  - `MODEL`: AI model name.
  - `OLLAMA_BASE_URL`: Base URL for LangChain integration.

## Usage
1. Install dependencies:
```
pip install -r requirements.txt
```

2. Start the server:
```
uvicorn app:app --host 0.0.0.0 --port 8000
```

3. Access the application via your browser:
```
http://<SERVER_ADDRESS>:8000
```


4. Interact with the AI voice chat through the web interface.

## Future Enhancements
- Improved error handling for WebRTC connections.
- Support for additional AI models and conversational flows.
- Enhanced UI/UX for the front-end.
