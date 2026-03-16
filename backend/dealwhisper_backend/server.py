from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from google import genai

from .artifacts import ArtifactStore, SessionArtifactRecorder
from .config import Settings, get_settings
from .live_session import DealWhisperLiveGateway
from .security import authorize_request, authorize_websocket
from .tools import lookup_buyer_profile, search_company_intelligence, load_battle_card, search_case_studies

CALL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,127}$")
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title="DealWhisper Backend", version="0.1.0")
    gateway = DealWhisperLiveGateway(resolved_settings)
    artifact_store = ArtifactStore(resolved_settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    @app.get("/healthz")
    async def healthcheck() -> dict[str, object]:
        return {
            "status": "ok",
            "runtime_mode": resolved_settings.live_runtime_mode,
            "auth_required": bool(resolved_settings.backend_shared_secret),
            "artifacts_enabled": True,
            "max_saved_artifacts": resolved_settings.max_saved_artifacts,
        }

    @app.get("/api/sessions")
    async def list_sessions(request: Request, limit: int = 20) -> dict[str, object]:
        authorize_request(request, resolved_settings)
        return {"sessions": artifact_store.list_summaries(limit=limit)}

    @app.get("/api/sessions/{artifact_id}")
    async def get_session_artifact(request: Request, artifact_id: str) -> dict[str, object]:
        authorize_request(request, resolved_settings)
        summary = artifact_store.get_summary(artifact_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Artifact not found.")
        return summary

    @app.delete("/api/sessions/{artifact_id}")
    async def delete_session_artifact(request: Request, artifact_id: str) -> dict[str, str]:
        authorize_request(request, resolved_settings)
        deleted = artifact_store.delete_summary(artifact_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Artifact not found.")
        return {"status": "deleted"}

    @app.post("/api/research")
    async def research_buyer(request: Request) -> dict[str, object]:
        authorize_request(request, resolved_settings)
        body = await request.json()
        email = str(body.get("email", "")).strip()
        company = str(body.get("company", "")).strip()
        name = str(body.get("name", "")).strip()

        if not company:
            raise HTTPException(status_code=400, detail="company is required.")

        buyer_profile = lookup_buyer_profile(email or f"{name.lower().replace(' ', '.')}@unknown.com", company)
        company_intel = search_company_intelligence(company)
        case_studies = search_case_studies(industry=company_intel.get("industry", "technology"))

        insights: list[dict[str, str]] = []

        # Buyer profile insights
        if buyer_profile.get("status") != "new_buyer":
            if buyer_profile.get("role"):
                insights.append({"title": "Buyer role", "body": f"{buyer_profile.get('name', name)} — {buyer_profile.get('role', '')}. {buyer_profile.get('communication_style', '')}"})
            if buyer_profile.get("deal_history"):
                insights.append({"title": "Deal history", "body": str(buyer_profile["deal_history"])})
            if buyer_profile.get("known_objections"):
                objections = buyer_profile["known_objections"]
                if isinstance(objections, list):
                    insights.append({"title": "Known objections", "body": ". ".join(objections)})
        else:
            insights.append({"title": "New buyer", "body": f"No prior history with {name} at {company}. Focus on discovery and building rapport."})

        # Company intelligence
        if company_intel.get("status") != "researching":
            if company_intel.get("recent_news"):
                insights.append({"title": "Recent news", "body": str(company_intel["recent_news"])})
            if company_intel.get("financial_health"):
                insights.append({"title": "Financial health", "body": str(company_intel["financial_health"])})
            if company_intel.get("technology_stack"):
                insights.append({"title": "Technology stack", "body": str(company_intel["technology_stack"])})
            if company_intel.get("competitive_landscape"):
                insights.append({"title": "Competitive landscape", "body": str(company_intel["competitive_landscape"])})
            if company_intel.get("key_decision_makers"):
                insights.append({"title": "Decision makers", "body": str(company_intel["key_decision_makers"])})

        # Case studies
        if case_studies:
            for cs in case_studies[:2]:
                title = cs.get("title", "Case study")
                summary = cs.get("summary", cs.get("outcome", ""))
                if summary:
                    insights.append({"title": title, "body": str(summary)})

        if not insights:
            insights.append({"title": "Research pending", "body": f"No intelligence available yet for {company}. Connect to Firestore or add company data to enable pre-call research."})

        return {"insights": insights, "buyer_profile": buyer_profile, "company_intel": company_intel}

    @app.post("/api/briefing")
    async def briefing_chat(request: Request) -> dict[str, object]:
        """Pre-call briefing chat. The AI asks smart questions to understand the deal context."""
        authorize_request(request, resolved_settings)
        body = await request.json()
        buyer_context = body.get("buyer_context", {})
        messages = body.get("messages", [])

        if not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="messages must be an array.")

        system_prompt = (
            "You are DealWhisper's pre-call briefing assistant. Your job is to deeply understand "
            "the upcoming sales meeting so you can provide world-class real-time coaching during the call.\n\n"
            "BUYER CONTEXT:\n"
            f"- Name: {buyer_context.get('name', 'Unknown')}\n"
            f"- Company: {buyer_context.get('company', 'Unknown')}\n"
            f"- Title: {buyer_context.get('title', '')}\n"
            f"- Goal: {buyer_context.get('goal', '')}\n"
            f"- Anchor: {buyer_context.get('anchor', '')}\n"
            f"- Floor: {buyer_context.get('floor', '')}\n"
            f"- Watch for: {buyer_context.get('watch_for', '')}\n"
            f"- Edge: {buyer_context.get('edge', '')}\n\n"
            "INSTRUCTIONS:\n"
            "1. Ask probing questions about the deal — what happened in previous meetings, "
            "who else is involved in the decision, what objections you expect, timeline pressures, "
            "competitive threats, internal politics, budget situation.\n"
            "2. After each user message, summarize what you now understand AND ask the next most "
            "important question you still need answered.\n"
            "3. Be concise — 2-3 sentences max per response, then your question.\n"
            "4. Remember everything the user tells you across the conversation.\n"
            "5. If the user says they're ready or done briefing, give a brief strategy summary "
            "of what you'll focus on during the live call.\n"
            "6. Never use markdown formatting. Plain text only."
        )

        # Build Gemini conversation
        gemini_messages = [{"role": "user", "parts": [{"text": system_prompt + "\n\nStart by asking your first question about this deal."}]}]

        # Add conversation history
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            gemini_messages.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        # If the last message was from the user, we need the model to respond
        # If it's the first message (empty history), the system prompt asks the first question
        if not messages:
            # First call — model should ask first question
            pass
        elif messages[-1].get("role") == "assistant":
            # Last was assistant, this shouldn't happen but handle gracefully
            return {"reply": "What else would you like me to know about this deal?", "memory": []}

        try:
            client = genai.Client(vertexai=True, project=resolved_settings.project_id, location=resolved_settings.location)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_messages,
            )
            reply_text = response.text.strip() if response.text else "Tell me more about this deal."

            # Extract memory points from the conversation for passing to live session
            memory_points: list[str] = []
            for msg in messages:
                if msg.get("role") == "user" and msg.get("content", "").strip():
                    memory_points.append(msg["content"].strip())

            return {"reply": reply_text, "memory": memory_points}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Briefing AI error: {exc}")

    @app.websocket("/ws/call/{call_id}")
    async def websocket_call_handler(websocket: WebSocket, call_id: str) -> None:
        await websocket.accept()
        if not await authorize_websocket(websocket, resolved_settings):
            return

        recorder: SessionArtifactRecorder | None = None
        session_status = "completed"
        try:
            if not CALL_ID_PATTERN.match(call_id):
                raise ValueError("Call ID must be 3-128 characters using letters, numbers, hyphens, or underscores.")

            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                raise ValueError("Initial payload must be a JSON object.")

            buyer_context, visual_source = _normalize_buyer_context(payload)
            recorder = SessionArtifactRecorder.create(
                call_id=call_id,
                buyer_context=buyer_context,
                websocket_url=str(websocket.url),
                visual_source=visual_source,
            )
            await gateway.serve(websocket, buyer_context, call_id, recorder=recorder)
        except WebSocketDisconnect:
            return
        except Exception as exc:
            session_status = "error"
            if recorder:
                recorder.record_error(str(exc))
            try:
                await websocket.send_json({"type": "session.error", "message": str(exc)})
            except Exception:
                return
            await websocket.close(code=1011)
        finally:
            if recorder:
                artifact_store.save_summary(recorder.build_summary(status=session_status))

    # ── Serve frontend static build if present (production) ──────
    if STATIC_DIR.is_dir():
        @app.get("/")
        async def serve_index() -> FileResponse:
            return FileResponse(str(STATIC_DIR / "index.html"))

        app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

        @app.get("/{path:path}")
        async def serve_spa_fallback(path: str) -> FileResponse:
            candidate = STATIC_DIR / path
            if candidate.is_file() and candidate.resolve().is_relative_to(STATIC_DIR.resolve()):
                return FileResponse(str(candidate))
            return FileResponse(str(STATIC_DIR / "index.html"))

    return app


def _normalize_buyer_context(payload: dict[str, object]) -> tuple[dict[str, str], str]:
    buyer_context = payload.get("buyer_context", payload)
    if not isinstance(buyer_context, dict):
        raise ValueError("buyer_context must be an object.")

    normalized = {
        "name": str(buyer_context.get("name", "")).strip(),
        "email": str(buyer_context.get("email", "")).strip(),
        "company": str(buyer_context.get("company", "")).strip(),
        "title": str(buyer_context.get("title", "")).strip(),
        "goal": str(buyer_context.get("goal", "")).strip(),
        "anchor": str(buyer_context.get("anchor", "")).strip(),
        "floor": str(buyer_context.get("floor", "")).strip(),
        "watch_for": str(buyer_context.get("watch_for", "")).strip(),
        "edge": str(buyer_context.get("edge", "")).strip(),
    }

    if not normalized["name"] or not normalized["company"]:
        raise ValueError("buyer_context.name and buyer_context.company are required.")

    session_options = payload.get("session_options", {})
    visual_source = "none"
    if isinstance(session_options, dict):
        candidate = str(session_options.get("visual_source", "none")).strip().lower()
        if candidate in {"camera", "screen", "none"}:
            visual_source = candidate

    return normalized, visual_source


app = create_app()
