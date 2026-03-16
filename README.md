# DealWhisper

DealWhisper now has two layers in this workspace:

- The existing React/Vite frontend MVP that demonstrates the product experience with seeded call data.
- A Python backend that can run either against Vertex Gemini Live or a furnished local mock runtime.

## What Exists

Frontend demo modes:

- `Pre-Call War Room`
- `Live Call Intelligence`
- `Post-Call Debrief`

Backend production scaffold:

- FastAPI WebSocket server for `/ws/call/{call_id}`
- Gemini Live session bridge using Vertex AI
- Automatic fallback to a furnished local mock runtime when Vertex is unavailable
- Firestore-backed tool stubs for buyer profiles, battle cards, company intelligence, call events, and debrief inputs
- Server-side HUD state packaging and whisper JSON envelopes
- Cloud Run Dockerfile and `cloudbuild.yaml`
- ADK agent factory for future non-live orchestration

## Important Runtime Correction

The current `gemini-live-2.5-flash-native-audio` API supports `AUDIO` output, not simultaneous `AUDIO` plus `TEXT`. The backend scaffold handles this by:

- using native audio for whispers
- enabling input/output audio transcription
- converting spoken whisper transcripts into frontend-friendly JSON/HUD payloads server-side

It also expects video frames as `image/jpeg` snapshots rather than `video/webm`.

## Frontend

Run the existing demo:

```bash
npm install
npm run dev
```

Optional frontend env:

```bash
cp .env.example .env.local
```

Set `VITE_DEALWHISPER_BACKEND_WS_BASE` if your backend is not on `ws://127.0.0.1:8080/ws/call`.
Set `VITE_DEALWHISPER_BACKEND_TOKEN` if you enable backend shared-secret auth.
The live console persists your buyer context, backend endpoint, and visual-source defaults in browser storage.
It also supports a local preset library for repeat buyer/deal setups, import/export of preset bundles, one-click preset launch, and shows backend health/runtime state in the operator console.
Pre-Call War Room can now hand off a briefing packet into Live Call, where queued preflight notes are auto-injected into the session when you connect.
Live Call also has a permission-free guided demo button that skips mic/camera capture and drives the furnished mock runtime with scripted buyer moments.

Quality checks:

```bash
npm run build
npm run lint
```

## Backend

Create a virtualenv and install dependencies:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

Copy env defaults:

```bash
cp backend/.env.example backend/.env
```

Runtime modes:

- `LIVE_RUNTIME_MODE=auto`: try Vertex first, then fall back to the furnished local simulator
- `LIVE_RUNTIME_MODE=vertex`: require Vertex and fail if cloud access is unavailable
- `LIVE_RUNTIME_MODE=mock`: always run the furnished local simulator

Optional backend protection and persistence:

- `BACKEND_SHARED_SECRET`: if set, both websocket and REST artifact endpoints require this token
- `ARTIFACT_DIR`: directory for persisted call artifacts
- `MAX_SAVED_ARTIFACTS`: retention cap for saved session JSON files

Run the API locally:

```bash
npm run dev:backend
```

Run the furnished local product with one command:

```bash
npm run dev:stack:mock
```

That starts the backend in mock mode plus the Vite frontend. Use this when you want the full operator console, whispers, HUD state, and post-call debrief without any Google Cloud access.

Local Vertex auth uses Application Default Credentials, not an API key:

```bash
gcloud auth application-default login
```

Run against Vertex with automatic mock fallback:

```bash
npm run dev:stack
```

If credentials are missing or the configured Vertex project is inaccessible, the websocket now returns `session.ready` with `runtime_mode: "mock"` and continues in furnished local mode instead of terminating the session.

Every session is now persisted by the backend as a JSON artifact. The frontend Post-Call tab can replay saved artifacts via:

- `GET /api/sessions`
- `GET /api/sessions/{artifact_id}`
- `DELETE /api/sessions/{artifact_id}`

The Post-Call tab now behaves like a local session library:

- replay saved backend artifacts
- send a saved or active debrief back into Live Call as the next setup
- save any active or saved debrief as a reusable preset
- download the active debrief as JSON
- delete local artifacts you no longer need

## WebSocket Contract

Connect to `/ws/call/{call_id}` and send an initial JSON payload with buyer context:

```json
{
  "buyer_context": {
    "name": "Maya Chen",
    "company": "Northstar Health Systems",
    "goal": "Confirm budget owner and secure CFO follow-up."
  }
}
```

Then stream these message types:

- `audio.chunk`: base64 PCM audio, default MIME type `audio/pcm;rate=16000`
- `video.frame`: base64 JPEG frame, default MIME type `image/jpeg`
- `text.turn`: manual text turn for notes or overrides
- `audio.end`: marks end of the current audio stream

The backend emits:

- `session.ready`
- `session.error`
- `live.audio`
- `transcript.input`
- `transcript.output`
- `whisper.payload`
- `hud.state`
- `session.warning`

## Project Structure

- `src/App.tsx`: frontend shell and seeded product experience
- `src/data/dealData.ts`: seeded buyer, live-call, and debrief intelligence
- `backend/dealwhisper_backend/server.py`: FastAPI entrypoint
- `backend/dealwhisper_backend/live_session.py`: Gemini Live session bridge
- `backend/dealwhisper_backend/tools.py`: Firestore and product-knowledge tool layer
- `backend/dealwhisper_backend/agent.py`: ADK agent and runner factory
- `backend/Dockerfile`: Cloud Run container image
- `cloudbuild.yaml`: Cloud Build deployment flow

## Current Scope

The local product is now furnished end to end: frontend transport is real, the backend websocket is real, and the operator console stays usable even without cloud access by falling back to a deterministic mock runtime. The cloud side is still partial: Firestore and vector search remain scaffolded, and full production behavior still depends on valid Vertex and Google Cloud credentials.
