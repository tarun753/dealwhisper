<p align="center">
  <h1 align="center">DealWhisper</h1>
  <p align="center"><strong>AI copilot that listens to your sales calls and whispers winning moves in real time.</strong></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gemini_Live-2.5_Flash-4285F4?logo=google&logoColor=white" alt="Gemini Live" />
  <img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Cloud_Run-Deploy-4285F4?logo=googlecloud&logoColor=white" alt="Cloud Run" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" />
</p>

---

## Why DealWhisper?

- **Never walk into a call blind.** Get an AI-generated war-room briefing with buyer intel, battle cards, and deal context before you dial.
- **Real-time coaching, not post-mortems.** Gemini Live listens to the conversation and whispers objection handlers, pricing nudges, and next-best-actions as the call happens.
- **Turn every call into a playbook.** Automatic post-call debriefs score your performance, extract commitments, and feed insights back into your next call.

---

## Screenshot

> _Replace with a product screenshot or demo GIF._

```
[ screenshot placeholder ]
```

---

## Architecture

```
 Browser (React 19 / Vite)
    |
    | WebSocket  /ws/call/{call_id}
    v
 FastAPI Backend
    |
    |--- Gemini Live 2.5 Flash (audio + video streaming)
    |--- Firestore (buyer profiles, battle cards, call events)
    |--- Mock Runtime (local dev without cloud credentials)
```

The frontend streams microphone audio and camera frames over a WebSocket. The FastAPI backend bridges those streams to the Gemini Live API, which returns real-time whisper audio and transcriptions. The backend packages whispers into structured HUD payloads and pushes them back to the browser.

When Google Cloud credentials are unavailable, the backend automatically falls back to a furnished mock runtime so you can develop and demo the full product locally.

---

## Features

### Pre-Call War Room
Buyer intelligence, company research, deal history, and battle cards assembled into a briefing packet. Hand off the packet directly into the live session.

### Live Call Intelligence
Real-time AI whispers delivered as audio and structured HUD overlays. Includes objection coaching, sentiment tracking, and talk-time monitoring. Supports mic/camera capture or a guided demo mode that drives scripted buyer moments.

### Post-Call Debrief
Automatic session scoring, commitment extraction, and next-step recommendations. Replay saved sessions, export debriefs as JSON, or feed insights back into your next call setup as a reusable preset.

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- (Optional) Google Cloud project with Vertex AI enabled

### Frontend

```bash
cd dealwhisper
npm install
cp .env.example .env.local   # configure backend WebSocket URL
npm run dev                   # http://localhost:5173
```

### Backend

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

### Run the Full Stack (Mock Mode -- No Cloud Required)

```bash
npm run dev:stack:mock
```

This starts the backend in mock mode and the Vite frontend together. Use this to explore the full product experience without any Google Cloud access.

### Run with Vertex AI

```bash
gcloud auth application-default login
npm run dev:stack
```

If Vertex credentials are missing, the backend falls back to mock mode automatically.

---

## Environment Variables

### Frontend (`.env.local`)

| Variable | Description |
|---|---|
| `VITE_DEALWHISPER_BACKEND_WS_BASE` | Backend WebSocket URL (default: `ws://127.0.0.1:8080/ws/call`) |
| `VITE_DEALWHISPER_BACKEND_TOKEN` | Shared secret for backend auth (optional) |

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `PROJECT_ID` | Google Cloud project ID |
| `LOCATION` | Vertex AI region |
| `LIVE_MODEL_ID` | Gemini Live model identifier |
| `LIVE_RUNTIME_MODE` | `auto` / `vertex` / `mock` |
| `VOICE_NAME` | Gemini voice preset |
| `FRONTEND_ORIGIN` | CORS origin for the frontend |
| `ENABLE_GOOGLE_SEARCH` | Enable grounded search tool |
| `BACKEND_SHARED_SECRET` | Shared secret for WebSocket and REST auth (optional) |
| `ARTIFACT_DIR` | Directory for persisted call artifacts (optional) |
| `MAX_SAVED_ARTIFACTS` | Retention cap for saved session files |

See `.env.example` and `backend/.env.example` for defaults.

---

## Deployment

DealWhisper ships with a `cloudbuild.yaml` and `backend/Dockerfile` for deployment to Google Cloud Run.

```bash
gcloud builds submit --config cloudbuild.yaml
```

The Cloud Build pipeline builds the container image and deploys it to Cloud Run. Configure your production environment variables in the Cloud Run service settings.

---

## Project Structure

```
dealwhisper/
  src/
    App.tsx                          # Frontend shell
    data/dealData.ts                 # Seeded buyer and call intelligence
  backend/
    dealwhisper_backend/
      server.py                      # FastAPI entrypoint
      live_session.py                # Gemini Live session bridge
      tools.py                       # Firestore and product-knowledge tools
      agent.py                       # ADK agent and runner factory
    Dockerfile                       # Cloud Run container
    requirements.txt
  cloudbuild.yaml                    # Cloud Build deployment
  vite.config.ts
  package.json
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | Python, FastAPI, WebSockets |
| AI | Gemini Live 2.5 Flash (Vertex AI) |
| Infrastructure | Google Cloud Run, Cloud Build, Firestore |

---

## License

[MIT](./LICENSE) -- Tarun Kumar Mahato
