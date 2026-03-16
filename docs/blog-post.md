# Building DealWhisper: Real-Time AI Sales Coaching with Gemini Live API and Google Cloud

**Author: Tarun Kumar Mahato**

---

## The Problem Nobody Talks About in Sales

Every sales rep knows the feeling. You walk into a call with a prospect you barely researched, the buyer drops an objection you didn't anticipate, your competitor gets mentioned and you freeze, and after the call you forget half the commitments you made. Post-call analysis tools tell you what went wrong *yesterday*. But what if AI could coach you *during* the call — whispering the right response in your ear while the buyer is still talking?

That's DealWhisper. A real-time AI sales intelligence system that sees what the buyer shows, hears what they say, and coaches the rep through whispered audio — all powered by Gemini Live API on Google Cloud.

This post breaks down how it was built, the technical decisions behind it, and what we learned shipping a multimodal real-time AI agent.

---

## Architecture: The Full Stack

DealWhisper is split into three layers: a React frontend, a FastAPI backend on Cloud Run, and the Gemini Live API doing the heavy lifting.

**Frontend:** React 19 + TypeScript + Vite. The browser captures microphone audio at 16kHz PCM and camera/screen share as JPEG frames, then streams both over a WebSocket to the backend. A HUD (Heads-Up Display) overlay renders deal temperature, BANT tracking, buying signals, and whisper cards — all updated in real time.

**Backend:** FastAPI running on Python 3.12, deployed to Cloud Run. The server manages WebSocket connections, authenticates sessions, and acts as the bidirectional bridge between the browser and Gemini. It also handles session artifact storage for post-call debriefs.

**AI Layer:** Two Gemini models serve different purposes:
- **Gemini Live 2.5 Flash** (`gemini-live-2.5-flash-native-audio`) for real-time bidirectional audio/video streaming during calls
- **Gemini 2.5 Flash** for the pre-call briefing chat, where the AI asks probing questions about the buyer and builds context before the call starts

The backend uses the `google-genai` SDK with `vertexai=True` for Vertex AI integration:

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project=settings.project_id,    # "dealwhisper-prod"
    location=settings.location,      # "us-central1"
)

async with client.aio.live.connect(
    model="gemini-live-2.5-flash-native-audio",
    config=session_config,
) as session:
    # Bidirectional streaming begins
```

The WebSocket pipeline looks like this:

```
Browser (mic 16kHz PCM + camera JPEG) → WebSocket → FastAPI → Gemini Live API
Gemini Live API → FastAPI → WebSocket → Browser (whispered audio 24kHz PCM + HUD updates)
```

---

## Why Gemini Live API (Not Regular Gemini)

This was the single most important architectural decision. Regular Gemini works great for request-response. But sales calls are continuous, interruptible, and time-sensitive. We needed:

1. **Bidirectional audio streaming** — the AI listens continuously while also being able to speak (whisper) at any moment
2. **Barge-in support** — if the buyer starts talking, the AI's whisper needs to stop immediately
3. **Sub-200ms latency** — coaching that arrives 2 seconds late is useless coaching
4. **Video input** — camera frames streamed alongside audio for multimodal understanding

The Gemini Live API gives us all four. The session stays open for the entire call duration, audio flows in both directions simultaneously, and the API handles turn-taking and interruption natively.

We also configured context window compression to handle long calls without losing critical context:

```python
"context_window_compression": {
    "trigger_tokens": 25000,
    "sliding_window": {"target_tokens": 20000},
}
```

This prevents the model from hitting token limits during 45+ minute calls while preserving the most relevant conversation history.

---

## 10 Function Tools: Grounded Intelligence, Not Hallucinated Advice

The biggest risk with AI sales coaching is hallucination. If the AI invents a competitor's pricing or fabricates a case study, the rep loses credibility instantly. We solved this by registering 10 function tools with the Gemini Live session:

| Tool | Purpose |
|------|---------|
| `lookup_buyer_profile` | Retrieve buyer communication style, objection history, buying signals |
| `load_battle_card` | Competitive intelligence: advantages, weaknesses, proven rebuttals |
| `search_company_intelligence` | Funding, news, hiring signals, leadership changes, tech stack |
| `get_product_knowledge` | Features, ROI data, pricing tiers matched to conversation context |
| `get_proven_objection_responses` | Top 3 responses ranked by historical close rate per objection class |
| `search_case_studies` | Social proof matched by industry, company size, and pain point |
| `log_call_event` | Real-time event logging: objections, signals, deal temperature changes |
| `update_buyer_profile` | Write back new signals discovered during this call |
| `generate_post_call_debrief` | Compile timeline, coaching metrics, and key moments |
| `draft_followup_email` | Personalized follow-up referencing exact buyer commitments |

When Gemini detects a competitor mention, it calls `load_battle_card` and gets real competitive data — not a guess. When a price objection surfaces, `get_proven_objection_responses` returns responses ranked by actual close rate. The AI's coaching is grounded in data the sales team has validated.

Tool responses that don't need to interrupt the conversation (like profile lookups or event logging) are dispatched with `scheduling="SILENT"`, so Gemini processes them without pausing the audio stream.

---

## The HUD: Real-Time Visual Intelligence

While whispered audio is the primary coaching channel, the HUD gives reps a visual dashboard they can glance at during the call. The `HudStateManager` on the backend processes every tool result and transcript to compute:

- **Deal Temperature** — a dynamic score that shifts based on buying signals and objections detected
- **BANT Tracker** — Budget, Authority, Need, Timeline progress indicators
- **Active Whisper Card** — compact coaching directives like "PROVE FAST ROLLOUT" or "CLOSE NOW"
- **Buying Signals Feed** — real-time detection of phrases like implementation questions, future-tense language, and term-length inquiries

Every tool call result and transcript update triggers a `hud.state` WebSocket message to the frontend, keeping the display current without polling.

---

## Pre-Call Briefing: Context Before the First Word

Before the live session starts, DealWhisper runs a pre-call briefing chat using Gemini 2.5 Flash. The AI asks the rep probing questions: Who is the buyer? What happened on the last call? What competitors are in play? What's the goal for this call?

This context gets injected into the Live session as a priming message when the call begins:

```python
kickoff = (
    "CALL STARTING NOW.\n"
    f"Call ID: {call_id}\n"
    f"Buyer context: {json.dumps(buyer_context)}\n\n"
    "Activate live monitoring mode. Load buyer profile, company intelligence, "
    "case studies, and battle cards silently in the background."
)
await session.send_client_content(
    turns=types.Content(role="user", parts=[types.Part(text=kickoff)]),
    turn_complete=True,
)
```

The AI enters the call already knowing the buyer's communication style, objection history, and the rep's strategy — before the buyer says a single word.

---

## Beyond Text: Multimodal Input Changes Everything

This is not a chatbot. DealWhisper streams the buyer's camera feed as JPEG frames alongside audio. The AI can observe:

- **Facial micro-expressions** — detecting genuine interest vs. polite disengagement
- **Body language shifts** — leaning in (engagement), arms crossed (resistance), looking away (distraction)
- **Screen share content** — if the buyer shares their screen, the AI sees what they're looking at

The input pipeline sends both modalities simultaneously:

```python
# Audio chunk from microphone
await session.send_realtime_input(
    audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
)

# Video frame from camera
await session.send_realtime_input(
    video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
)
```

Multimodal input (audio + video + buyer context) produces multimodal output: whispered coaching through the rep's earpiece, visual HUD updates on screen, and structured artifacts for post-call review. The AI doesn't just hear the words — it reads the room.

---

## Challenges and Learnings

**WebSocket reconnection.** Sales calls can last 45+ minutes. Network blips happen. We implemented an `auto` runtime mode that falls back to a local mock simulation if the Vertex connection drops, so the rep never gets a dead screen mid-call.

**Whisper frequency calibration.** Early testing showed that too many whispers are worse than none — they distract the rep and create unnatural pauses. We tuned the system instruction to keep whispers short and strategic, and the HUD compact text function condenses coaching into 3-5 word directives.

**Context compression for long calls.** Gemini's sliding window compression (`trigger_tokens: 25000`, `target_tokens: 20000`) was essential. Without it, late-call coaching quality degraded as the context window filled with earlier conversation.

**Mock mode for development.** We built a full `MockDealWhisperGateway` that simulates the Gemini Live API behavior locally — complete with tool calls, HUD updates, and whisper delivery. This let us iterate on the frontend and tool logic without burning API credits during development.

---

## What's Next

DealWhisper currently stores session artifacts locally. The roadmap includes:

- **Firestore integration** for persistent buyer intelligence that accumulates across calls — the tool layer is already wired with Firestore client code, waiting to be activated
- **CRM sync** to push call summaries, BANT progress, and follow-up emails directly into Salesforce
- **Team analytics dashboard** to aggregate coaching patterns, objection frequency, and win/loss signals across the entire sales org

---

## Built With

- **Gemini Live 2.5 Flash** — real-time bidirectional audio/video streaming via Vertex AI
- **Gemini 2.5 Flash** — pre-call briefing chat
- **google-genai SDK** with `vertexai=True` — unified Python client for Vertex AI
- **Google Cloud Run** — serverless backend deployment
- **Google Cloud Firestore** — buyer intelligence persistence (in progress)
- **FastAPI + WebSocket** — real-time bidirectional gateway
- **React 19 + TypeScript + Vite** — frontend with HUD overlay

The Gemini Live API turned a concept that would have required stitching together STT, LLM, and TTS into a single, native multimodal stream. That's the unlock. Real-time AI coaching is only possible when the latency budget is measured in milliseconds, not seconds — and Gemini Live delivers exactly that.
