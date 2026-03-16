from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .hud import build_initial_hud_state


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clock_label(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).strftime("%H:%M:%S UTC")


def _normalize_key(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower())
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized or "call"


def _strategy_card_from_context(buyer_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": buyer_context.get("goal", "Confirm pain, authority, and next step."),
        "anchor": buyer_context.get("anchor", "TBD"),
        "floor": buyer_context.get("floor", "TBD"),
        "watch_for": buyer_context.get("watch_for", "Hidden objection masked as process."),
        "edge": buyer_context.get("edge", "Faster path to measurable ROI."),
    }


def _build_backend_ws_base(raw_url: str) -> str:
    if "/ws/call/" not in raw_url:
        return raw_url.rstrip("/")
    return raw_url.split("/ws/call/", 1)[0].rstrip("/") + "/ws/call"


@dataclass
class SessionArtifactRecorder:
    call_id: str
    buyer_context: dict[str, Any]
    backend_ws_base: str
    visual_source: str
    artifact_id: str
    started_at: int
    runtime_mode: str = "unknown"
    transcript_feed: list[dict[str, Any]] = field(default_factory=list)
    whisper_history: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_hud_state: dict[str, Any] = field(default_factory=dict)
    audio_chunks_sent: int = 0
    video_frames_sent: int = 0
    notes_sent: int = 0

    @classmethod
    def create(
        cls,
        *,
        call_id: str,
        buyer_context: dict[str, Any],
        websocket_url: str,
        visual_source: str,
    ) -> "SessionArtifactRecorder":
        started_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        artifact_id = f"{_normalize_key(call_id)}-{started_at}"
        return cls(
            call_id=call_id,
            buyer_context=buyer_context,
            backend_ws_base=_build_backend_ws_base(websocket_url),
            visual_source=visual_source,
            artifact_id=artifact_id,
            started_at=started_at,
            final_hud_state=build_initial_hud_state(_strategy_card_from_context(buyer_context)),
        )

    def set_runtime_mode(self, runtime_mode: str) -> None:
        self.runtime_mode = runtime_mode

    def note_audio_chunk(self) -> None:
        self.audio_chunks_sent += 1

    def note_video_frame(self) -> None:
        self.video_frames_sent += 1

    def note_seller_note(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.notes_sent += 1
        self.record_transcript(direction="note", speaker_label="Seller note", text=cleaned)

    def record_transcript(self, *, direction: str, speaker_label: str, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.transcript_feed.append(
            {
                "id": f"transcript-{len(self.transcript_feed) + 1}",
                "direction": direction,
                "speaker_label": speaker_label,
                "text": cleaned,
                "received_at": timestamp,
                "received_at_label": _clock_label(timestamp),
            }
        )

    def record_whisper(self, payload: dict[str, Any]) -> None:
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        whisper = {
            **payload,
            "id": f"whisper-{len(self.whisper_history) + 1}",
            "received_at": timestamp,
            "received_at_label": _clock_label(timestamp),
        }
        self.whisper_history.insert(0, whisper)
        self.whisper_history = self.whisper_history[:20]

    def record_hud_state(self, payload: dict[str, Any]) -> None:
        self.final_hud_state = payload

    def record_warning(self, message: str) -> None:
        cleaned = message.strip()
        if not cleaned:
            return
        self.warnings.append(cleaned)
        self.record_transcript(direction="system", speaker_label="System", text=cleaned)

    def record_error(self, message: str) -> None:
        cleaned = message.strip()
        if not cleaned:
            return
        self.errors.append(cleaned)
        self.record_transcript(direction="system", speaker_label="System", text=cleaned)

    def build_summary(self, *, status: str) -> dict[str, Any]:
        ended_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        duration_seconds = max(1, (ended_at - self.started_at) // 1000)
        return {
            "artifact_id": self.artifact_id,
            "call_id": self.call_id,
            "buyer_context": self.buyer_context,
            "started_at": self.started_at,
            "ended_at": ended_at,
            "saved_at": _iso_now(),
            "status": status,
            "duration_seconds": duration_seconds,
            "whisper_history": self.whisper_history,
            "transcript_feed": self.transcript_feed,
            "final_hud_state": self.final_hud_state,
            "warnings": self.warnings,
            "errors": self.errors,
            "connection_stats": {
                "audio_chunks_sent": self.audio_chunks_sent,
                "video_frames_sent": self.video_frames_sent,
                "notes_sent": self.notes_sent,
                "backend_ws_base": self.backend_ws_base,
                "call_id": self.call_id,
                "visual_source": self.visual_source,
                "runtime_mode": self.runtime_mode,
            },
        }


class ArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = Path(settings.artifact_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_summary(self, summary: dict[str, Any]) -> Path:
        target = self.root / f"{summary['artifact_id']}.json"
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        temp.replace(target)
        self._prune()
        return target

    def list_summaries(self, *, limit: int = 20) -> list[dict[str, Any]]:
        summaries = [self._read_json(path) for path in self.root.glob("*.json")]
        summaries = [item for item in summaries if item is not None]
        summaries.sort(key=lambda item: item.get("ended_at", 0), reverse=True)
        return [self._to_list_item(item) for item in summaries[: max(1, min(limit, 100))]]

    def get_summary(self, artifact_id: str) -> dict[str, Any] | None:
        path = self.root / f"{artifact_id}.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def delete_summary(self, artifact_id: str) -> bool:
        path = self.root / f"{artifact_id}.json"
        if not path.exists():
            return False
        path.unlink(missing_ok=True)
        return True

    def _prune(self) -> None:
        paths = sorted(self.root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for path in paths[self.settings.max_saved_artifacts :]:
            path.unlink(missing_ok=True)

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _to_list_item(self, summary: dict[str, Any]) -> dict[str, Any]:
        buyer_context = summary.get("buyer_context", {})
        final_hud = summary.get("final_hud_state", {})
        connection_stats = summary.get("connection_stats", {})
        return {
            "artifact_id": summary.get("artifact_id"),
            "call_id": summary.get("call_id"),
            "buyer_name": buyer_context.get("name", "Unknown buyer"),
            "company": buyer_context.get("company", "Unknown company"),
            "started_at": summary.get("started_at"),
            "ended_at": summary.get("ended_at"),
            "duration_seconds": summary.get("duration_seconds"),
            "status": summary.get("status"),
            "runtime_mode": connection_stats.get("runtime_mode", "unknown"),
            "visual_source": connection_stats.get("visual_source", "none"),
            "deal_temperature": final_hud.get("deal_temperature", 0),
            "negotiation_stage": final_hud.get("negotiation_stage", "Opening"),
            "sentiment": final_hud.get("sentiment", "Neutral"),
        }
