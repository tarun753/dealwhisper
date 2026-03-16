from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_id: str
    location: str
    live_model_id: str
    voice_name: str
    frontend_origin: str
    enable_google_search: bool
    live_runtime_mode: str
    backend_shared_secret: str
    artifact_dir: str
    max_saved_artifacts: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[1]
    return Settings(
        project_id=os.getenv("PROJECT_ID", "dealwhisper-prod"),
        location=os.getenv("LOCATION", "us-central1"),
        live_model_id=os.getenv("LIVE_MODEL_ID", "gemini-live-2.5-flash-native-audio"),
        voice_name=os.getenv("VOICE_NAME", "Charon"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173"),
        enable_google_search=_read_bool("ENABLE_GOOGLE_SEARCH"),
        live_runtime_mode=os.getenv("LIVE_RUNTIME_MODE", "auto").strip().lower(),
        backend_shared_secret=os.getenv("BACKEND_SHARED_SECRET", "").strip(),
        artifact_dir=os.getenv("ARTIFACT_DIR", str(backend_dir / "artifacts")),
        max_saved_artifacts=max(1, int(os.getenv("MAX_SAVED_ARTIFACTS", "50"))),
    )
