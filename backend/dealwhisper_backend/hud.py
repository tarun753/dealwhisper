from __future__ import annotations

import time
from copy import deepcopy
from typing import Any


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]).strip()


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _compact_hud_text(text: str) -> str:
    lower = text.lower()

    if _contains_any(lower, ("rollout", "implementation", "onboarding", "security", "integration")) and _contains_any(
        lower, ("cost of waiting", "waiting", "timing")
    ):
        return "PROVE ROLLOUT THEN COST"
    if _contains_any(lower, ("criterion", "competitor", "battle card", "gong", "clari", "outreach", "salesforce", "hubspot")):
        return "WIN ON CRITERION"
    if _contains_any(lower, ("discount", "roi", "ceiling", "budget", "price")):
        return "PROBE ROI OR CEILING"
    if _contains_any(lower, ("rollout", "implementation", "onboarding", "security", "integration")):
        return "PROVE FAST ROLLOUT"
    if _contains_any(lower, ("cost of waiting", "timing")):
        return "QUANTIFY COST OF WAITING"
    if _contains_any(lower, ("decides", "decision", "approval", "committee", "boss", "cfo")):
        return "MAP THE DECISION"
    if _contains_any(lower, ("close window", "close now", "summary close", "next step")):
        return "⚡ CLOSE NOW"
    if _contains_any(lower, ("anchor", "number first", "set your")):
        return "🎯 ANCHOR FIRST"
    if _contains_any(lower, ("surface", "concern", "what's still open", "what am i missing", "haven't said")):
        return "SURFACE THE CONCERN"
    if _contains_any(lower, ("hold", "wait", "silence", "don't speak", "deciding")):
        return "HOLD THE SILENCE"
    if _contains_any(lower, ("stop selling", "said yes", "congratulate")):
        return "🎉 STOP SELLING"

    cleaned = _truncate_words(text.replace(".", " ").replace(",", " "), 5)
    return cleaned.upper()


def _infer_whisper_type(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("close window", "close now", "summary close", "deal", "stop selling", "said yes")):
        return "CLOSE"
    if any(token in lower for token in ("anchor", "number first", "price first", "set your")):
        return "ANCHOR"
    if any(token in lower for token in ("competitor", "battle card", "criterion", "gong", "clari")):
        return "BATTLE"
    if any(token in lower for token in ("hold", "wait", "silence", "stop", "don't speak", "deciding")):
        return "HOLD"
    if any(token in lower for token in ("reframe", "back to value", "off track", "redirect")):
        return "REFRAME"
    if any(token in lower for token in ("warning", "risk", "concern", "objection", "surface", "contempt",
                                         "anger", "lost them", "disengaging", "cooling")):
        return "WARN"
    return "MOVE"


def _infer_urgency(text: str, whisper_type: str) -> str:
    lower = text.lower()
    if whisper_type in {"CLOSE", "ANCHOR"}:
        return "CRITICAL"
    if any(token in lower for token in ("now", "immediately", "urgent", "fast", "stop", "contempt", "anger")):
        return "HIGH"
    if whisper_type in {"WARN", "HOLD", "BATTLE"}:
        return "HIGH"
    return "MEDIUM"


def _infer_color(whisper_type: str) -> str:
    return {
        "MOVE": "green",
        "HOLD": "yellow",
        "WARN": "red",
        "REFRAME": "blue",
        "CLOSE": "red",
        "BATTLE": "purple",
        "ANCHOR": "purple",
    }.get(whisper_type, "green")


def _next_stage(current_stage: str, text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("stop selling", "said yes", "congratulate", "post-close")):
        return "Post-Close"
    if any(token in lower for token in ("close window", "close now", "summary close")):
        return "Close"
    if any(token in lower for token in ("anchor", "discount", "term", "pilot", "concession", "trade")):
        return "Bargaining"
    if any(token in lower for token in ("objection", "concern", "risk", "budget", "price", "expensive",
                                         "too much", "authority", "timing")):
        return "Objections"
    if any(token in lower for token in ("demo", "show", "feature", "walkthrough", "presentation")):
        return "Demo"
    if any(token in lower for token in ("discovery", "pain", "problem", "timeline", "tell me about",
                                         "what are you using", "how does")):
        return "Discovery"
    return current_stage


# ── BUYING SIGNAL DETECTION ────────────────────────────────────────

_TIER1_PATTERNS = (
    "when we implement", "once we roll out", "when this is live",
    "what would it take", "contract length", "term options",
    "how long is the agreement", "onboarding timeline",
    "how does your team handle", "success team", "support team",
    "can we start with", "pilot", "phased", "what if we did",
    "send the proposal", "send a proposal", "move forward",
    "next steps", "how do we get started",
)

_TIER2_PATTERNS = (
    "taking notes", "can you repeat", "say that again",
    "what does pricing look like", "how much for",
    "interesting", "that makes sense",
)


def _detect_buying_signals(text: str) -> tuple[int, int]:
    """Returns (tier1_count, tier2_count) of buying signals detected."""
    lower = text.lower()
    tier1 = sum(1 for pattern in _TIER1_PATTERNS if pattern in lower)
    tier2 = sum(1 for pattern in _TIER2_PATTERNS if pattern in lower)
    return tier1, tier2


# ── OBJECTION DETECTION ────────────────────────────────────────────

_OBJECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "price": ("too expensive", "over budget", "more than we planned", "can't justify",
              "best you can do", "is that negotiable", "that's a lot",
              "were thinking more like", "can you do better", "discount"),
    "authority": ("need to check with", "my boss decides", "committee",
                  "not the only one", "loop in", "board approval", "above my pay grade",
                  "need buy-in"),
    "timing": ("not the right time", "next quarter", "budget freeze",
               "come back in", "let's revisit", "too much going on", "stabilize first"),
    "need": ("already have something", "don't think we need", "handle that internally",
             "not a priority", "fine with what we have"),
    "trust": ("how do I know", "been burned before", "what if it doesn't",
              "prove it", "need more than your word", "track record", "references"),
    "competitor": ("gong", "clari", "salesforce einstein", "outreach",
                   "also talking to", "does this for less", "already does that"),
}


def _detect_objection_class(text: str) -> str | None:
    lower = text.lower()
    for cls, patterns in _OBJECTION_PATTERNS.items():
        if any(p in lower for p in patterns):
            return cls
    return None


# ── HUD STATE ──────────────────────────────────────────────────────

CLOSE_WINDOW_THRESHOLD = 3
CLOSE_WINDOW_SECONDS = 300  # 5 minutes


def build_initial_hud_state(strategy_card: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy = strategy_card or {}
    return {
        "deal_temperature": 50,
        "deal_temp_direction": "stable",
        "deal_temp_reason": "Awaiting live signal confluence.",
        "sentiment": "Neutral",
        "negotiation_stage": "Opening",
        "time_elapsed_seconds": 0,
        "talk_ratio": {
            "salesperson_pct": 0,
            "buyer_pct": 0,
            "status": "ok",
            "target_pct": 40,
        },
        "bant": {
            "budget": {"level": 0, "label": "Unknown"},
            "authority": {"level": 0, "label": "Unknown"},
            "need": {"level": 0, "label": "Latent"},
            "timeline": {"level": 0, "label": "Absent"},
        },
        "active_signals": [],
        "buyer_commitments": [],
        "buying_signals_count": {
            "tier1": 0,
            "tier2": 0,
            "close_window_open": False,
        },
        "active_battle_card": None,
        "strategy_card": {
            "goal": strategy.get("goal", "Confirm pain, authority, and next step."),
            "anchor": strategy.get("anchor", "TBD"),
            "floor": strategy.get("floor", "TBD"),
            "watch_for": strategy.get("watch_for", "Hidden objection masked as process."),
            "edge": strategy.get("edge", "Faster path to measurable ROI."),
        },
        "concessions_made": 0,
        "last_concession_got_return": True,
        "detected_objection_class": None,
    }


class HudStateManager:
    def __init__(self, strategy_card: dict[str, Any] | None = None) -> None:
        self._state = build_initial_hud_state(strategy_card)
        self._tier1_timestamps: list[float] = []

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def apply_tool_result(self, tool_name: str, result: Any) -> None:
        if not isinstance(result, dict):
            return

        if tool_name == "load_battle_card":
            self._state["active_battle_card"] = result.get("competitor") or result.get("name")
            self._push_signal("⚔️ Battle card loaded", "high", "⚔️")

        if tool_name == "lookup_buyer_profile":
            style = result.get("communication_style")
            if style:
                self._push_signal(f"Buyer: {_truncate_words(style, 6)}", "medium", "🧠")
            risk_tolerance = result.get("risk_tolerance")
            if risk_tolerance:
                self._push_signal(f"Risk: {_truncate_words(risk_tolerance, 5)}", "low", "⚠️")

        if tool_name == "search_company_intelligence":
            news = result.get("recent_news", [])
            hiring = result.get("hiring_signals", [])
            if news:
                self._push_signal(f"{len(news)} company signals", "medium", "📰")
            if hiring:
                self._push_signal(f"{len(hiring)} hiring signals", "medium", "👥")

        if tool_name == "search_case_studies":
            if isinstance(result, list) and result:
                self._push_signal(f"{len(result)} case studies ready", "medium", "📋")

        if tool_name == "get_proven_objection_responses":
            responses = result.get("responses", [])
            if responses:
                top = responses[0]
                rate = top.get("close_rate", 0)
                self._push_signal(f"Top response: {int(rate * 100)}% close rate", "high", "🎯")

        if tool_name == "log_call_event":
            event_type = result.get("event", {}).get("type", "")
            if event_type:
                self._push_signal(f"Event: {event_type}", "low", "•")

    def apply_input_transcript(self, text: str) -> None:
        lower = text.lower()
        self._state["negotiation_stage"] = _next_stage(self._state["negotiation_stage"], text)

        # BANT tracking
        if "need to check with" in lower or "loop in" in lower or _contains_any(
            lower, ("boss", "cfo", "committee", "approval", "decision team")
        ):
            self._state["bant"]["authority"] = {"level": 45, "label": "Influencer"}
        if _contains_any(lower, ("budget", "price", "expensive", "cost", "afford")):
            current = self._state["bant"]["budget"]["level"]
            self._state["bant"]["budget"] = {"level": max(current, 55), "label": "Approximate"}
        if any(token in lower for token in ("this quarter", "next quarter", "month end", "deadline", "30 day", "pilot", "before q")):
            self._state["bant"]["timeline"] = {"level": 60, "label": "Defined"}
        if any(token in lower for token in ("need", "pain", "problem", "struggling", "frustrated", "broken")):
            current = self._state["bant"]["need"]["level"]
            self._state["bant"]["need"] = {"level": max(current, 70), "label": "Acknowledged"}

        # Buying signal detection
        tier1, tier2 = _detect_buying_signals(text)
        now = time.monotonic()

        if tier1 > 0:
            self._state["buying_signals_count"]["tier1"] += tier1
            self._tier1_timestamps.extend([now] * tier1)
            self._state["deal_temperature"] = min(100, self._state["deal_temperature"] + 5 * tier1)
            self._state["deal_temp_direction"] = "rising"
            self._state["deal_temp_reason"] = "Buying signal detected in buyer language."
            self._push_signal("⚡ Tier 1 buying signal", "high", "⚡")

        if tier2 > 0:
            self._state["buying_signals_count"]["tier2"] += tier2
            self._state["deal_temperature"] = min(100, self._state["deal_temperature"] + 2 * tier2)

        # Close window: 3+ Tier 1 in last 5 minutes
        cutoff = now - CLOSE_WINDOW_SECONDS
        self._tier1_timestamps = [ts for ts in self._tier1_timestamps if ts >= cutoff]
        if len(self._tier1_timestamps) >= CLOSE_WINDOW_THRESHOLD:
            if not self._state["buying_signals_count"]["close_window_open"]:
                self._state["buying_signals_count"]["close_window_open"] = True
                self._state["deal_temperature"] = min(100, self._state["deal_temperature"] + 10)
                self._state["deal_temp_direction"] = "rising"
                self._state["deal_temp_reason"] = "⚡ Close window OPEN. Buying signals converged."
                self._state["sentiment"] = "Hot"
                self._push_signal("⚡ CLOSE WINDOW OPEN", "high", "⚡")

        # Objection detection
        objection = _detect_objection_class(text)
        if objection:
            self._state["detected_objection_class"] = objection
            self._state["deal_temperature"] = max(0, self._state["deal_temperature"] - 5)
            self._state["deal_temp_direction"] = "falling"
            self._state["deal_temp_reason"] = f"{objection.title()} objection detected."
            self._push_signal(f"🔴 Objection: {objection}", "high", "🔴")

        # Commitment tracking
        if any(token in lower for token in ("i agree", "let's do", "we can do", "send it",
                                             "sounds good", "i'm in", "let's proceed")):
            commitment = _truncate_words(text, 15)
            self._state["buyer_commitments"].append(commitment)
            self._state["buyer_commitments"] = self._state["buyer_commitments"][-5:]

        # Sentiment from temperature
        temp = self._state["deal_temperature"]
        if temp >= 85:
            self._state["sentiment"] = "Hot"
        elif temp >= 70:
            self._state["sentiment"] = "Warm"
        elif temp >= 50:
            self._state["sentiment"] = "Neutral"
        elif temp >= 30:
            self._state["sentiment"] = "Cool"
        else:
            self._state["sentiment"] = "Cold"

    def apply_whisper(self, text: str) -> dict[str, Any]:
        whisper_type = _infer_whisper_type(text)
        urgency = _infer_urgency(text, whisper_type)
        color = _infer_color(whisper_type)
        self._state["negotiation_stage"] = _next_stage(self._state["negotiation_stage"], text)

        if whisper_type == "CLOSE":
            self._state["buying_signals_count"]["tier1"] += 1
            self._state["buying_signals_count"]["close_window_open"] = True
            self._state["deal_temperature"] = min(100, self._state["deal_temperature"] + 8)
            self._state["deal_temp_direction"] = "rising"
            self._state["deal_temp_reason"] = "Close window detected from live signal stack."
            self._state["sentiment"] = "Hot"
        elif whisper_type in {"WARN", "HOLD"}:
            self._state["deal_temperature"] = max(0, self._state["deal_temperature"] - 4)
            self._state["deal_temp_direction"] = "falling"
            self._state["deal_temp_reason"] = "Risk or hesitation detected."
            if self._state["deal_temperature"] < 40:
                self._state["sentiment"] = "Cool"
        elif whisper_type == "BATTLE":
            self._state["deal_temp_direction"] = "stable"
            self._state["deal_temp_reason"] = "Competitive intelligence engaged."
        elif whisper_type == "ANCHOR":
            self._state["deal_temp_direction"] = "stable"
            self._state["deal_temp_reason"] = "Anchoring position."
        else:
            self._state["deal_temp_direction"] = "stable"
            self._state["deal_temp_reason"] = "Actionable coaching delivered."

        self._push_signal(text, "high" if urgency in {"HIGH", "CRITICAL"} else "medium", "🎧")

        return {
            "whisper_type": whisper_type,
            "urgency": urgency,
            "audio_text": _truncate_words(text, 12),
            "hud_text": _compact_hud_text(text),
            "hud_color": color,
            "display_duration_seconds": 4,
            "confidence": 0.92 if urgency == "CRITICAL" else 0.82 if urgency == "HIGH" else 0.74,
            "trigger": "live_model_output",
            "suggested_exact_words": None,
            "suppress_if_speaking": True,
        }

    def _push_signal(self, text: str, urgency: str, icon: str) -> None:
        signals = self._state["active_signals"]
        signals.insert(
            0,
            {
                "icon": icon,
                "text": text,
                "urgency": urgency,
            },
        )
        del signals[8:]
