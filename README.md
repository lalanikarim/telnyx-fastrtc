# AI Chatbot and Phone Agent Demo with Telnyx/FastRTC

## Overview
This is a proof-of-concept (POC) project integrating **Telnyx** with **FastRTC** to build a real-time voice chat application powered by AI. The project leverages WebRTC for real-time audio communication and LangChain for AI-driven conversational capabilities. In addition to AI-powered voice chat via the web interface, the project also supports phone-based interactions. Users can call the AI agent and have real-time conversations over the phone.

## Features
- **Real-Time Voice Chat**: Stream audio between users using WebRTC.
- **AI-Powered Conversations**: Process audio input to generate AI responses using LangChain and text-to-speech models.
- **Phone-Based AI Conversations**: Users can call a designated phone number to interact with the AI agent in real time.
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
  - `TELNYX_API_KEY`: Telnyx API key for authenticating API requests.
  - `TELNYX_PUBLIC_KEY`: Telnyx public key for verifying webhooks.
  - `SERVER_ADDRESS`: Public-facing address of the server.
  - `WEBSOCKET_SERVER`: WebSocket server URL for real-time communication.
  - `MESSAGING_PROFILE`: Telnyx Messaging Profile ID for SMS and phone call handling.
  - `PHONE_NUMBER`: Telnyx phone number for AI agent interaction.
  - `OLLAMA_API_SERVER`: Base URL for the Ollama API.
  - `MODEL`: AI model name to be used for generating responses.

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

4. Set up phone-based interaction:
   - Configure the `MESSAGING_PROFILE` and `PHONE_NUMBER` in the `.env` file with your Telnyx credentials.
   - Ensure your server is publicly accessible to handle incoming webhook requests from Telnyx.
   - Dial the configured phone number to interact with the AI agent over the phone.

5. Interact with the AI voice chat through the web interface or via phone.

## Future Enhancements
- Improved error handling for WebRTC connections.
- Support for additional AI models and conversational flows.
- Enhanced UI/UX for the front-end.
