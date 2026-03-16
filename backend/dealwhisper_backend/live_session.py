from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from fastapi import WebSocket
from google import genai
from google.genai import types

from .artifacts import SessionArtifactRecorder
from .config import Settings, get_settings
from .hud import HudStateManager
from .mock_live import MockDealWhisperGateway
from .system_instruction import PRODUCTION_SYSTEM_INSTRUCTION
from .tools import get_live_tool_declarations, get_tool_registry, is_non_blocking_tool


def _model_dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if isinstance(value, dict):
        return value
    return {}


def _extract_text(candidate: Any) -> str | None:
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, dict):
        return candidate.get("text") or candidate.get("transcript")
    return None


def _decode_media_chunk(message: dict[str, Any], field: str) -> bytes:
    encoded = message.get(field)
    if not encoded:
        raise ValueError(f"Missing {field} in media message.")
    return base64.b64decode(encoded)


def _strategy_card_from_context(buyer_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": buyer_context.get("goal", "Confirm pain, authority, and next step."),
        "anchor": buyer_context.get("anchor", "TBD"),
        "floor": buyer_context.get("floor", "TBD"),
        "watch_for": buyer_context.get("watch_for", "Hidden objection masked as process."),
        "edge": buyer_context.get("edge", "Faster path to measurable ROI."),
    }


class DealWhisperLiveGateway:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.tool_registry = get_tool_registry()
        self.mock_gateway = MockDealWhisperGateway()

    def _build_session_config(self) -> dict[str, Any]:
        return {
            "response_modalities": ["TEXT"],
            "system_instruction": PRODUCTION_SYSTEM_INSTRUCTION,
            "temperature": 0.3,
            "top_p": 0.85,
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": self.settings.voice_name,
                    }
                }
            },
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "context_window_compression": {
                "trigger_tokens": 25000,
                "sliding_window": {"target_tokens": 20000},
            },
            "tools": get_live_tool_declarations(self.settings.enable_google_search),
        }

    async def serve(
        self,
        websocket: WebSocket,
        buyer_context: dict[str, Any],
        call_id: str,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        if self.settings.live_runtime_mode == "mock":
            await self.mock_gateway.serve(websocket, buyer_context, call_id, recorder=recorder)
            return

        if self.settings.live_runtime_mode not in {"auto", "vertex"}:
            raise ValueError("LIVE_RUNTIME_MODE must be one of: auto, vertex, mock.")

        try:
            await self._serve_vertex(websocket, buyer_context, call_id, recorder=recorder)
        except Exception as exc:
            if self.settings.live_runtime_mode != "auto":
                raise
            await self.mock_gateway.serve(
                websocket,
                buyer_context,
                call_id,
                startup_message=f"Vertex unavailable ({exc}). Switched to local simulation mode.",
                recorder=recorder,
            )

    async def _serve_vertex(
        self,
        websocket: WebSocket,
        buyer_context: dict[str, Any],
        call_id: str,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        hud = HudStateManager(strategy_card=_strategy_card_from_context(buyer_context))
        if recorder:
            recorder.set_runtime_mode("vertex")
            recorder.record_hud_state(hud.snapshot())
        client = genai.Client(
            vertexai=True,
            project=self.settings.project_id,
            location=self.settings.location,
        )

        async with client.aio.live.connect(
            model=self.settings.live_model_id,
            config=self._build_session_config(),
        ) as session:
            await self._prime_session(session, buyer_context, call_id)
            await websocket.send_json(
                {
                    "type": "session.ready",
                    "call_id": call_id,
                    "artifact_id": recorder.artifact_id if recorder else None,
                    "runtime_mode": "vertex",
                    "hud_state": hud.snapshot(),
                }
            )

            receive_task = asyncio.create_task(self._forward_live_to_frontend(session, websocket, hud, recorder))
            send_task = asyncio.create_task(self._forward_frontend_to_live(session, websocket, recorder))

            done, pending = await asyncio.wait(
                {receive_task, send_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()

            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc

    async def _prime_session(self, session: Any, buyer_context: dict[str, Any], call_id: str) -> None:
        kickoff = (
            "CALL STARTING NOW.\n"
            f"Call ID: {call_id}\n"
            f"Buyer context: {json.dumps(buyer_context)}\n\n"
            "Activate live monitoring mode. Load buyer profile, company intelligence, case studies, "
            "and battle cards silently in the background. Keep whispers short. Return spoken coaching only."
        )
        await session.send_client_content(
            turns=types.Content(
                role="user",
                parts=[types.Part(text=kickoff)],
            ),
            turn_complete=True,
        )

    async def _forward_frontend_to_live(
        self,
        session: Any,
        websocket: WebSocket,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "audio.chunk":
                if recorder:
                    recorder.note_audio_chunk()
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=_decode_media_chunk(message, "data"),
                        mime_type=message.get("mime_type", "audio/pcm;rate=16000"),
                    )
                )
                continue

            if message_type == "video.frame":
                if recorder:
                    recorder.note_video_frame()
                await session.send_realtime_input(
                    video=types.Blob(
                        data=_decode_media_chunk(message, "data"),
                        mime_type=message.get("mime_type", "image/jpeg"),
                    )
                )
                continue

            if message_type == "text.turn":
                if recorder:
                    recorder.note_seller_note(message.get("text", ""))
                await session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=message.get("text", ""))],
                    ),
                    turn_complete=message.get("turn_complete", True),
                )
                continue

            if message_type == "audio.end":
                await session.send_realtime_input(audio_stream_end=True)
                continue

            await websocket.send_json(
                {
                    "type": "session.warning",
                    "message": f"Unsupported message type: {message_type}",
                }
            )
            if recorder:
                recorder.record_warning(f"Unsupported message type: {message_type}")

    async def _forward_live_to_frontend(
        self,
        session: Any,
        websocket: WebSocket,
        hud: HudStateManager,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        async for response in session.receive():
            payload = _model_dump(response)
            tool_call = payload.get("tool_call") or payload.get("toolCall")
            if tool_call:
                await self._handle_tool_calls(session, websocket, hud, tool_call, recorder)

            if getattr(response, "data", None):
                await websocket.send_json(
                    {
                        "type": "live.audio",
                        "mime_type": "audio/pcm;rate=24000",
                        "data": base64.b64encode(response.data).decode("utf-8"),
                    }
                )

            await self._forward_server_content(
                websocket,
                hud,
                payload.get("server_content") or payload.get("serverContent"),
                recorder,
            )

    async def _forward_server_content(
        self,
        websocket: WebSocket,
        hud: HudStateManager,
        server_content: dict[str, Any] | None,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        if not server_content:
            return

        input_text = _extract_text(server_content.get("input_transcription") or server_content.get("inputTranscription"))
        if input_text:
            hud.apply_input_transcript(input_text)
            if recorder:
                recorder.record_transcript(direction="input", speaker_label="Buyer", text=input_text)
                recorder.record_hud_state(hud.snapshot())
            await websocket.send_json({"type": "transcript.input", "text": input_text})
            await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})

        output_text = _extract_text(server_content.get("output_transcription") or server_content.get("outputTranscription"))
        if output_text:
            whisper_payload = hud.apply_whisper(output_text)
            if recorder:
                recorder.record_transcript(direction="output", speaker_label="DealWhisper", text=output_text)
                recorder.record_whisper(whisper_payload)
                recorder.record_hud_state(hud.snapshot())
            await websocket.send_json({"type": "transcript.output", "text": output_text})
            await websocket.send_json({"type": "whisper.payload", "payload": whisper_payload})
            await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})

        model_turn = server_content.get("model_turn") or server_content.get("modelTurn") or {}
        for part in model_turn.get("parts", []):
            inline_data = part.get("inline_data") or part.get("inlineData") or {}
            if inline_data.get("data"):
                await websocket.send_json(
                    {
                        "type": "live.audio",
                        "mime_type": inline_data.get("mime_type") or inline_data.get("mimeType") or "audio/pcm;rate=24000",
                        "data": base64.b64encode(inline_data["data"]).decode("utf-8"),
                    }
                )

    async def _handle_tool_calls(
        self,
        session: Any,
        websocket: WebSocket,
        hud: HudStateManager,
        tool_call: dict[str, Any],
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        function_calls = tool_call.get("function_calls") or tool_call.get("functionCalls") or []
        responses: list[types.FunctionResponse] = []

        for call in function_calls:
            name = call.get("name")
            args = call.get("args") or {}
            call_id = call.get("id")
            handler = self.tool_registry.get(name)

            if handler is None:
                responses.append(
                    types.FunctionResponse(
                        id=call_id,
                        name=name,
                        response={"error": f"Unknown function: {name}"},
                    )
                )
                continue

            try:
                result = await asyncio.to_thread(handler, **args)
                hud.apply_tool_result(name, result)
                if recorder:
                    recorder.record_hud_state(hud.snapshot())
                await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
                response = types.FunctionResponse(
                    id=call_id,
                    name=name,
                    response={"output": result},
                    scheduling="SILENT" if is_non_blocking_tool(name) else None,
                )
            except Exception as exc:
                response = types.FunctionResponse(
                    id=call_id,
                    name=name,
                    response={"error": str(exc)},
                )

            responses.append(response)

        if responses:
            await session.send_tool_response(function_responses=responses)
