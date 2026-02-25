# ContextIQ: Virtual Meeting Bot Implementation Roadmap

This document outlines the architecture, technology stack, and step-by-step roadmap required to build a **Virtual Meeting Bot** for the ContextIQ platform. This bot will automatically join scheduled meetings (Microsoft Teams, Zoom, Google Meet), record raw audio, and pipe it directly to ContextIQ's FastAPI backend for immediate processing—bypassing the need for manual `.mp4` file uploads.

---

## 1. Architectural Overview

Building a meeting bot requires a specialized microservice. Communication APIs (like Microsoft Graph or Zoom Developer API) require robust handling of real-time audio streams (RTP/WebSocket/WebRTC). 

It is highly recommended to build the **Bot Connector Service** in **Node.js** or **C# (.NET)**, as these languages have the most mature, official SDKs for real-time media streaming from vendors like Microsoft and Zoom. This service will then bridge the audio to your existing Python FastAPI backend.

### Architecture Diagram

```text
┌─────────────────┐       (1. Invite)         ┌───────────────────────┐
| User's Calendar | ─────────────────────────>|  Bot Orchestrator     |
| (Outlook/Google)|                           |  (Node.js / C#)       |
└─────────────────┘                           └───────────────────────┘
                                                          │
                                                          │ (2. API Join Command)
                                                          ▼
┌─────────────────┐      (3. Real-Time RTP Audio)   ┌───────────────────────┐
| Microsoft Teams | ──────────────────────────────>│  Bot Media Service    |
| Zoom / Meet     |                                 |  (Node.js / C#)       |
└─────────────────┘                                 └───────────────────────┘
                                                          │
                                                          │ (4. Audio Buffer / Stream over HTTP/WebSocket)
                                                          ▼
                                              ┌───────────────────────┐
                                              | ContextIQ Backend     |
                                              | (FastAPI + Python)    |
                                              │  • stt_service.py     │
                                              │  • rag_service.py     │
                                              └───────────────────────┘
```

---

## 2. Technology Stack Selection

To implement this reliably, we recommend adding a lightweight media microservice to your stack:

### Microsoft Teams Integration (Primary Focus)
*   **API:** Microsoft Graph Cloud Communications API (`Call.Join`).
*   **Media Handling:** Microsoft Local Media SDK (requires Windows Server or Linux Azure VM).
*   **Recommended Language:** **C# (.NET 8)** is the absolute best choice here, as the Microsoft Local Media SDK is written in C# and C++. A Node.js wrapper exists but is less stable for heavy audio processing.

### Zoom Integration
*   **API:** Zoom Meeting SDK for Linux (or Zoom Meeting Bot API).
*   **Recommended Language:** **Node.js** or **C++**. 

### Google Meet Integration
*   **API:** Google Meet REST API (currently limited for bots) OR Puppeteer/Playwright.
*   **Recommended Language:** **Node.js** (Using headless Chrome via Puppeteer to physically "join" the web client and record system audio).

### The Bridge to ContextIQ (Python)
*   **Protocol:** Server-Sent Events (SSE) or WebSockets.
*   **Action:** The C#/Node.js Bot receives the raw PCM audio chunks and streams them via WebSocket to your FastAPI server (`/api/bot/stream`). FastAPI aggregates the chunks, saves a `.wav` file, and kicks off `stt_service.py`.

---

## 3. Step-by-Step Implementation Roadmap

### Phase 1: Setup and Azure Configuration (Week 1)
To build a Teams bot, you must register it as an enterprise app.
1. **Azure Active Directory:** Register a new Bot Application in the Azure Portal.
2. **Permissions:** Grant the bot `Calls.JoinGroupCall.All` and `Calls.AccessMedia.All` Application Permissions.
3. **Bot Framework:** Register the bot via the Microsoft Bot Framework.
4. **Local Tunnel:** Setup `ngrok` or `localtunnel`. Teams requires a publicly accessible HTTPS endpoint to send webhook events (e.g., "Meeting Started").

### Phase 2: Building the Bot Connector (C# / Node.js) (Week 2-3)
1. **Webhook Listener:** Build an endpoint (`/callback`) that listens to Microsoft Graph notifications. When a user invites the bot to a meeting, Graph hits this endpoint.
2. **Join Logic:** Write the logic to accept the meeting URL and issue the `POST /communications/calls` Graph request to join the lobby.
3. **Media Socket:** Implement the Local Media SDK. When the call is active, subscribe to the AudioSocket.
4. **Speaker Mapping (Crucial):** Microsoft APIs provide the *Active Speaker ID* attached to the audio streams. The bot should log: `[Timestamp] Audio Chunk + Speaker: Pawan Uikey`. This eliminates the need for Pyannote!

### Phase 3: The ContextIQ Bridge (Week 4)
1. **FastAPI WebSocket:** In `app/api/upload.py` (or a new `bot.py`), create a WebSocket endpoint: `ws://localhost:8000/api/bot/stream/{meeting_id}`.
2. **Audio Aggregation:** As the Bot Service sends audio chunks over the WebSocket, FastAPI aggregates them in memory or appends them to a temporary `.wav` file in `data/audio/`.
3. **End of Call Trigger:** When the Bot receives a "Call Terminated" event, it sends an `EOF` signal to FastAPI.
4. **Pipeline Execution:** FastAPI automatically triggers `stt_service.py`, `summary_service.py`, and `insights_service.py` exactly as it does for manual uploads today.

### Phase 4: UI Updates & Quality of Life (Week 5)
1. **Calendar Dashboard:** Update the Svelte/Streamlit UI to allow users to link their Office 365 / Google Calendar.
2. **Toggle Bot:** Add a switch next to upcoming meetings in the UI: *"Auto-join with Bot"*.
3. **Live Status:** Build a small UI badge: *Bot Status: Waiting in Lobby 🟡 -> Recording 🔴 -> Processing 🟢*.

---

## 4. Challenges & Considerations

*   **Hosting:** The Microsoft Local Media SDK requires specific environments (usually a Windows Server or a specifically configured Linux Docker container). It cannot easily run on a standard free-tier Vercel/Render host. You will likely need a dedicated Azure VM or an EC2 instance.
*   **Lobby By-pass:** If the bot joins as a "Guest", a human must manually admit it from the Teams lobby. If it joins authenticated as a tenant user, it can bypass the lobby.
*   **Privacy Notifications:** Microsoft enforces that bots declare they are recording. You may need to inject a synthesized voice ("ContextIQ is now recording this meeting") or ensure the default Teams recording banner is triggered.

---

## 5. Next Steps

If you would like to proceed with this architecture, the first immediate step is **Phase 1: Azure Configuration**. You will need access to an Azure account with admin privileges to register the bot application and configure the Microsoft Graph permissions.
