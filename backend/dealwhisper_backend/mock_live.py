from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .artifacts import SessionArtifactRecorder
from .hud import HudStateManager


def _strategy_card_from_context(buyer_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": buyer_context.get("goal", "Confirm pain, authority, and next step."),
        "anchor": buyer_context.get("anchor", "TBD"),
        "floor": buyer_context.get("floor", "TBD"),
        "watch_for": buyer_context.get("watch_for", "Hidden objection masked as process."),
        "edge": buyer_context.get("edge", "Faster path to measurable ROI."),
    }


def _send_buyer_line(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "The buyer is weighing rollout risk and budget pressure."
    return cleaned


def _pick_whisper(note: str) -> tuple[str, dict[str, Any]]:
    lower = note.lower()
    metadata: dict[str, Any] = {}

    competitor_match = re.search(r"\b(clari|gong|hubspot|salesforce|outreach)\b", lower)
    if competitor_match:
        competitor = competitor_match.group(1).title()
        metadata["battle_card"] = competitor
        return (f"{competitor} mentioned. Ask their top criterion first.", metadata)

    if any(token in lower for token in ("price", "budget", "expensive", "cost", "discount", "best you can do")):
        return ("Don't discount. Ask ROI or ceiling.", metadata)

    if any(token in lower for token in ("implement", "rollout", "onboarding", "security", "integration")):
        metadata["buying_signal"] = "evaluation"
        return ("They're evaluating. Prove rollout and hold.", metadata)

    if any(token in lower for token in ("next quarter", "later", "not now", "timing", "revisit")):
        return ("Timing objection. Find the cost of waiting.", metadata)

    if any(token in lower for token in ("boss", "cfo", "committee", "approval", "check with")):
        return ("Ask who decides and what they need.", metadata)

    if any(token in lower for token in ("pilot", "term", "contract", "next steps", "move forward", "send proposal")):
        metadata["close_window"] = True
        return ("Close window open. Summarize and secure next step.", metadata)

    if any(token in lower for token in ("concern", "hesitant", "unsure", "risk")):
        return ("Surface the concern. Ask what's still open.", metadata)

    return ("Probe deeper. Ask what matters most.", metadata)


# ── GUIDED DEMO SCENES ───────────────────────────────────────────
# Each scene simulates a call lifecycle stage with buyer lines,
# whispers, HUD state mutations, and tool call results.

_GUIDED_DEMO_SCENES: list[dict[str, Any]] = [
    # ── SCENE 1: OPENING ──────────────────────────────────────────
    {
        "delay": 0.3,
        "stage": "Opening",
        "buyer_line": "{buyer_name}: Thanks for getting on the call. We have a lot to cover and I want to make sure we use the time well.",
        "whisper": "Trust is high. Ask the direct agenda question.",
        "whisper_type": "MOVE",
        "urgency": "MEDIUM",
        "hud_color": "green",
        "hud_mutations": {
            "deal_temperature": 58,
            "deal_temp_direction": "rising",
            "deal_temp_reason": "Buyer is engaged and structured. Good opening energy.",
            "sentiment": "Neutral",
            "negotiation_stage": "Opening",
            "talk_ratio": {"salesperson_pct": 42, "buyer_pct": 58, "status": "ok", "target_pct": 40},
        },
        "signals": [
            {"icon": "🎯", "text": "Open posture, steady eye contact", "urgency": "low"},
            {"icon": "🎧", "text": "Pace matches seller. Rapport building.", "urgency": "low"},
        ],
    },
    # ── SCENE 2: DISCOVERY ────────────────────────────────────────
    {
        "delay": 3.5,
        "stage": "Discovery",
        "buyer_line": "{buyer_name}: Honestly, our forecasting is broken. The board asks for accuracy and we're guessing. It costs us credibility every quarter.",
        "whisper": "Pain quantified. Ask what waiting costs monthly.",
        "whisper_type": "MOVE",
        "urgency": "HIGH",
        "hud_color": "green",
        "hud_mutations": {
            "deal_temperature": 72,
            "deal_temp_direction": "rising",
            "deal_temp_reason": "Buyer quantified pain unprompted. Need is real.",
            "sentiment": "Warm",
            "negotiation_stage": "Discovery",
            "talk_ratio": {"salesperson_pct": 35, "buyer_pct": 65, "status": "ok", "target_pct": 40},
            "bant": {
                "budget": {"level": 45, "label": "Approximate"},
                "authority": {"level": 55, "label": "Influencer"},
                "need": {"level": 88, "label": "Acknowledged"},
                "timeline": {"level": 60, "label": "Defined"},
            },
        },
        "signals": [
            {"icon": "🔥", "text": "Pain quantified without prompting", "urgency": "high"},
            {"icon": "🎧", "text": "Voice dropped. Genuine frustration.", "urgency": "medium"},
            {"icon": "👁️", "text": "Leaning forward. Wants a solution.", "urgency": "medium"},
        ],
        "tool_result": {
            "tool_name": "lookup_buyer_profile",
            "result": {
                "name": "{buyer_name}",
                "communication_style": "Analytical, low-ego, prefers proof before enthusiasm.",
                "risk_tolerance": "Moderate-low. Wants controlled rollout.",
            },
        },
    },
    # ── SCENE 3: DISCOVERY (AUTHORITY) ────────────────────────────
    {
        "delay": 6.0,
        "stage": "Discovery",
        "buyer_line": "{buyer_name}: My CFO, Liam, will need to sign off. He's cautious about new vendor commitments after last year.",
        "whisper": "Authority objection. Ask what Liam will care about most.",
        "whisper_type": "WARN",
        "urgency": "HIGH",
        "hud_color": "yellow",
        "hud_mutations": {
            "deal_temperature": 68,
            "deal_temp_direction": "falling",
            "deal_temp_reason": "Authority gate surfaced. CFO sign-off required.",
            "sentiment": "Neutral",
            "negotiation_stage": "Discovery",
            "bant": {
                "budget": {"level": 50, "label": "Approximate"},
                "authority": {"level": 42, "label": "Influencer"},
                "need": {"level": 90, "label": "Acknowledged"},
                "timeline": {"level": 62, "label": "Defined"},
            },
        },
        "signals": [
            {"icon": "🔴", "text": "Objection: authority", "urgency": "high"},
            {"icon": "👁️", "text": "Gaze break on CFO mention. Genuine.", "urgency": "medium"},
        ],
    },
    # ── SCENE 4: PRESENTATION ─────────────────────────────────────
    {
        "delay": 9.0,
        "stage": "Presentation",
        "buyer_line": "{buyer_name}: When this is live for our team, how long before we see measurable improvement in forecast accuracy?",
        "whisper": "Tier 1 buying signal. Future-tense language.",
        "whisper_type": "MOVE",
        "urgency": "HIGH",
        "hud_color": "green",
        "hud_mutations": {
            "deal_temperature": 79,
            "deal_temp_direction": "rising",
            "deal_temp_reason": "Unprompted future-tense language. They're visualizing implementation.",
            "sentiment": "Warm",
            "negotiation_stage": "Demo",
            "talk_ratio": {"salesperson_pct": 48, "buyer_pct": 52, "status": "ok", "target_pct": 40},
            "bant": {
                "budget": {"level": 55, "label": "Approximate"},
                "authority": {"level": 58, "label": "Influencer"},
                "need": {"level": 92, "label": "Acknowledged"},
                "timeline": {"level": 75, "label": "Defined"},
            },
            "buying_signals_count": {"tier1": 1, "tier2": 1, "close_window_open": False},
        },
        "signals": [
            {"icon": "⚡", "text": "Tier 1 buying signal", "urgency": "high"},
            {"icon": "🧠", "text": "Chin touch. Deep evaluation.", "urgency": "medium"},
            {"icon": "📝", "text": "Visible note-taking started", "urgency": "medium"},
        ],
        "tool_result": {
            "tool_name": "search_case_studies",
            "result": [
                {
                    "company_name": "MedMetric",
                    "result": "42% improvement in forecast accuracy. 28% faster deal velocity.",
                },
            ],
        },
    },
    # ── SCENE 5: PRICE OBJECTION ──────────────────────────────────
    {
        "delay": 12.0,
        "stage": "Objections",
        "buyer_line": "{buyer_name}: I'll be direct. The number feels high. We're under a hiring freeze and I need to justify every dollar to Liam.",
        "whisper": "Don't discount. Ask: ROI or hard ceiling?",
        "whisper_type": "WARN",
        "urgency": "HIGH",
        "hud_color": "red",
        "hud_mutations": {
            "deal_temperature": 65,
            "deal_temp_direction": "falling",
            "deal_temp_reason": "Price objection surfaced. Budget tension is real.",
            "sentiment": "Cool",
            "negotiation_stage": "Objections",
            "bant": {
                "budget": {"level": 78, "label": "Range emerging"},
                "authority": {"level": 65, "label": "Influencer"},
                "need": {"level": 92, "label": "Acknowledged"},
                "timeline": {"level": 78, "label": "Defined"},
            },
            "detected_objection_class": "price",
        },
        "signals": [
            {"icon": "🔴", "text": "Objection: price", "urgency": "high"},
            {"icon": "🎧", "text": "Volume dropped on budget number", "urgency": "high"},
            {"icon": "👁️", "text": "Lip compression. Suppressing concern.", "urgency": "medium"},
        ],
        "tool_result": {
            "tool_name": "get_proven_objection_responses",
            "result": {
                "responses": [
                    {
                        "response": "Is the friction the absolute number, or confidence the return shows up fast enough?",
                        "close_rate": 0.72,
                    },
                ],
            },
        },
    },
    # ── SCENE 6: COMPETITOR MENTION ───────────────────────────────
    {
        "delay": 15.0,
        "stage": "Objections",
        "buyer_line": "{buyer_name}: We've also been talking to Gong. Their team showed us a demo last week.",
        "whisper": "Battle card loaded. Ask their #1 criterion.",
        "whisper_type": "BATTLE",
        "urgency": "HIGH",
        "hud_color": "purple",
        "hud_mutations": {
            "deal_temperature": 62,
            "deal_temp_direction": "stable",
            "deal_temp_reason": "Competitive intelligence engaged. Gong battle card active.",
            "sentiment": "Neutral",
            "negotiation_stage": "Objections",
            "active_battle_card": "Gong",
        },
        "signals": [
            {"icon": "⚔️", "text": "Battle card loaded: Gong", "urgency": "high"},
            {"icon": "🎧", "text": "Tone neutral. Testing, not threatening.", "urgency": "medium"},
        ],
        "tool_result": {
            "tool_name": "load_battle_card",
            "result": {
                "competitor": "Gong",
                "our_advantages": [
                    "Real-time coaching during calls, not just post-call analysis",
                    "Lighter implementation burden for RevOps teams",
                ],
                "proven_rebuttals": [
                    "Gong tells you what went wrong yesterday. We change the outcome today.",
                ],
            },
        },
    },
    # ── SCENE 7: NEGOTIATION / BUYING SIGNALS ─────────────────────
    {
        "delay": 18.5,
        "stage": "Negotiation",
        "buyer_line": "{buyer_name}: What if we started with a phased pilot — one region first? And what are the term options?",
        "whisper": "Close window open. Buying signals converged.",
        "whisper_type": "CLOSE",
        "urgency": "CRITICAL",
        "hud_color": "red",
        "hud_mutations": {
            "deal_temperature": 88,
            "deal_temp_direction": "rising",
            "deal_temp_reason": "Close window OPEN. 3+ Tier 1 buying signals in 5 minutes.",
            "sentiment": "Hot",
            "negotiation_stage": "Bargaining",
            "talk_ratio": {"salesperson_pct": 46, "buyer_pct": 54, "status": "ok", "target_pct": 40},
            "bant": {
                "budget": {"level": 84, "label": "Trade-off path identified"},
                "authority": {"level": 78, "label": "Decision group visible"},
                "need": {"level": 95, "label": "Clear operational consequence"},
                "timeline": {"level": 88, "label": "This week follow-up needed"},
            },
            "buying_signals_count": {"tier1": 4, "tier2": 2, "close_window_open": True},
            "buyer_commitments": ["Phased pilot request", "Term options inquiry"],
        },
        "signals": [
            {"icon": "⚡", "text": "CLOSE WINDOW OPEN", "urgency": "high"},
            {"icon": "⚡", "text": "Tier 1: pilot + term options", "urgency": "high"},
            {"icon": "👁️", "text": "Warm eye contact. Trust recovered.", "urgency": "medium"},
        ],
    },
    # ── SCENE 8: CLOSE ────────────────────────────────────────────
    {
        "delay": 22.0,
        "stage": "Close",
        "buyer_line": "{buyer_name}: I think we can make this work. Can you send the phased option to me and Liam before Thursday?",
        "whisper": "They said yes. STOP SELLING. Lock next steps.",
        "whisper_type": "CLOSE",
        "urgency": "CRITICAL",
        "hud_color": "green",
        "hud_mutations": {
            "deal_temperature": 94,
            "deal_temp_direction": "rising",
            "deal_temp_reason": "Verbal commitment secured. CFO meeting requested.",
            "sentiment": "Hot",
            "negotiation_stage": "Post-Close",
            "bant": {
                "budget": {"level": 88, "label": "Trade-off path identified"},
                "authority": {"level": 86, "label": "Decision group visible"},
                "need": {"level": 96, "label": "Clear operational consequence"},
                "timeline": {"level": 92, "label": "This week follow-up confirmed"},
            },
            "buying_signals_count": {"tier1": 5, "tier2": 3, "close_window_open": True},
            "buyer_commitments": [
                "Phased pilot request",
                "Term options inquiry",
                "CFO follow-up Thursday",
                "Send phased option before Thursday",
            ],
        },
        "signals": [
            {"icon": "🎉", "text": "VERBAL YES. Stop selling.", "urgency": "high"},
            {"icon": "⚡", "text": "Commitment: CFO follow-up Thursday", "urgency": "high"},
            {"icon": "📋", "text": "Next step locked", "urgency": "medium"},
        ],
    },
]


class MockDealWhisperGateway:
    async def serve(
        self,
        websocket: WebSocket,
        buyer_context: dict[str, Any],
        call_id: str,
        *,
        startup_message: str | None = None,
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        hud = HudStateManager(strategy_card=_strategy_card_from_context(buyer_context))
        hud._state["deal_temp_reason"] = "Mock live mode active."
        if recorder:
            recorder.set_runtime_mode("mock")
            recorder.record_hud_state(hud.snapshot())
        await websocket.send_json(
            {
                "type": "session.ready",
                "call_id": call_id,
                "artifact_id": recorder.artifact_id if recorder else None,
                "runtime_mode": "mock",
                "hud_state": hud.snapshot(),
            }
        )

        if recorder:
            recorder.record_warning(
                startup_message
                or "Mock live mode active. Audio/video transport is real, but live coaching is simulated locally."
            )
        await websocket.send_json(
            {
                "type": "session.warning",
                "message": startup_message
                or "Mock live mode active. Audio/video transport is real, but live coaching is simulated locally.",
            }
        )
        if recorder:
            recorder.record_warning(
                "Use the seller note box to feed buyer quotes, objections, competitor mentions, and next-step moments."
            )
        await websocket.send_json(
            {
                "type": "session.warning",
                "message": "Use the seller note box to feed buyer quotes, objections, competitor mentions, and next-step moments.",
            }
        )

        await self._send_opening_sequence(websocket, hud, buyer_context, recorder)

        visual_signal_sent = False
        try:
            while True:
                message = await websocket.receive_json()
                message_type = message.get("type")

                if message_type == "audio.chunk":
                    if recorder:
                        recorder.note_audio_chunk()
                    continue

                if message_type == "video.frame" and not visual_signal_sent:
                    visual_signal_sent = True
                    if recorder:
                        recorder.note_video_frame()
                    hud._state["active_signals"].insert(
                        0,
                        {
                            "icon": "📷",
                            "text": "Visual telemetry active.",
                            "urgency": "low",
                        },
                    )
                    del hud._state["active_signals"][8:]
                    if recorder:
                        recorder.record_hud_state(hud.snapshot())
                    await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
                    continue

                if message_type == "text.turn":
                    if recorder:
                        recorder.note_seller_note(message.get("text", ""))
                    await self._process_note(websocket, hud, message.get("text", ""), buyer_context, recorder)
                    continue

                if message_type == "audio.end":
                    if recorder:
                        recorder.record_warning(
                            "Audio stream ended. Review the Post-Call tab for your session debrief."
                        )
                    await websocket.send_json(
                        {
                            "type": "session.warning",
                            "message": "Audio stream ended. Review the Post-Call tab for your session debrief.",
                        }
                    )
                    continue
        except WebSocketDisconnect:
            return

    async def _send_opening_sequence(
        self,
        websocket: WebSocket,
        hud: HudStateManager,
        buyer_context: dict[str, Any],
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        buyer_name = buyer_context.get("name", "The buyer")
        company = buyer_context.get("company", "their team")
        opening_line = (
            f"{buyer_name}: Before we go further, I need confidence this rolls out fast and survives budget review at {company}."
        )
        await asyncio.sleep(0.25)
        hud.apply_input_transcript(opening_line)
        hud._state["talk_ratio"] = {
            "salesperson_pct": 42,
            "buyer_pct": 58,
            "status": "ok",
            "target_pct": 40,
        }
        if recorder:
            recorder.record_transcript(direction="input", speaker_label="Buyer", text=opening_line)
            recorder.record_hud_state(hud.snapshot())
        await websocket.send_json({"type": "transcript.input", "text": opening_line})
        await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})

        await asyncio.sleep(0.35)
        whisper = hud.apply_whisper("Start with rollout proof. Then quantify cost of waiting.")
        if recorder:
            recorder.record_transcript(direction="output", speaker_label="DealWhisper", text=whisper["audio_text"])
            recorder.record_whisper(whisper)
            recorder.record_hud_state(hud.snapshot())
        await websocket.send_json({"type": "transcript.output", "text": whisper["audio_text"]})
        await websocket.send_json({"type": "whisper.payload", "payload": whisper})
        await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})

    async def _process_note(
        self,
        websocket: WebSocket,
        hud: HudStateManager,
        note: str,
        buyer_context: dict[str, Any],
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        transcript_text = _send_buyer_line(note)
        hud.apply_input_transcript(transcript_text)
        if recorder:
            recorder.record_transcript(direction="input", speaker_label="Buyer", text=transcript_text)
        await websocket.send_json({"type": "transcript.input", "text": transcript_text})

        whisper_text, metadata = _pick_whisper(note)

        if battle_card := metadata.get("battle_card"):
            hud._state["active_battle_card"] = battle_card

        if metadata.get("buying_signal"):
            hud._state["buying_signals_count"]["tier1"] += 1
            hud._state["deal_temperature"] = min(100, hud._state["deal_temperature"] + 6)
            hud._state["deal_temp_direction"] = "rising"
            hud._state["deal_temp_reason"] = "Implementation evaluation turned into buying intent."
            hud._state["sentiment"] = "Warm"

        if metadata.get("close_window"):
            hud._state["buying_signals_count"]["tier1"] += 1
            hud._state["buying_signals_count"]["close_window_open"] = True
            hud._state["deal_temperature"] = min(100, hud._state["deal_temperature"] + 10)
            hud._state["deal_temp_direction"] = "rising"
            hud._state["deal_temp_reason"] = "Mock engine detected explicit next-step language."
            hud._state["sentiment"] = "Hot"
            hud._state["buyer_commitments"].append(transcript_text)
            hud._state["buyer_commitments"] = hud._state["buyer_commitments"][-5:]

        if recorder:
            recorder.record_hud_state(hud.snapshot())
        await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
        await asyncio.sleep(0.15)

        whisper_payload = hud.apply_whisper(whisper_text)
        if recorder:
            recorder.record_transcript(direction="output", speaker_label="DealWhisper", text=whisper_payload["audio_text"])
            recorder.record_whisper(whisper_payload)
            recorder.record_hud_state(hud.snapshot())
        await websocket.send_json({"type": "transcript.output", "text": whisper_payload["audio_text"]})
        await websocket.send_json({"type": "whisper.payload", "payload": whisper_payload})
        await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})

    async def run_guided_demo(
        self,
        websocket: WebSocket,
        hud: HudStateManager,
        buyer_context: dict[str, Any],
        recorder: SessionArtifactRecorder | None = None,
    ) -> None:
        """Run the full guided demo with all 8 scenes. Called via scripted notes."""
        buyer_name = buyer_context.get("name", "The buyer")

        for scene in _GUIDED_DEMO_SCENES:
            await asyncio.sleep(scene["delay"])

            # Apply buyer line
            buyer_line = scene["buyer_line"].format(buyer_name=buyer_name)
            hud.apply_input_transcript(buyer_line)

            # Apply HUD mutations
            mutations = scene.get("hud_mutations", {})
            for key, value in mutations.items():
                if key in hud._state:
                    hud._state[key] = value

            # Apply signals
            signals = scene.get("signals", [])
            for signal in reversed(signals):
                hud._state["active_signals"].insert(0, signal)
            del hud._state["active_signals"][8:]

            if recorder:
                recorder.record_transcript(direction="input", speaker_label="Buyer", text=buyer_line)
                recorder.record_hud_state(hud.snapshot())

            try:
                await websocket.send_json({"type": "transcript.input", "text": buyer_line})
                await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
            except Exception:
                return

            # Apply tool result if present
            tool_result = scene.get("tool_result")
            if tool_result:
                hud.apply_tool_result(tool_result["tool_name"], tool_result["result"])
                if recorder:
                    recorder.record_hud_state(hud.snapshot())
                try:
                    await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
                except Exception:
                    return

            # Short pause before whisper
            await asyncio.sleep(0.4)

            # Build and send whisper
            whisper_text = scene["whisper"]
            whisper_payload = hud.apply_whisper(whisper_text)
            # Override with scene-specific values
            whisper_payload["whisper_type"] = scene.get("whisper_type", whisper_payload["whisper_type"])
            whisper_payload["urgency"] = scene.get("urgency", whisper_payload["urgency"])
            whisper_payload["hud_color"] = scene.get("hud_color", whisper_payload["hud_color"])

            if recorder:
                recorder.record_transcript(
                    direction="output", speaker_label="DealWhisper", text=whisper_payload["audio_text"]
                )
                recorder.record_whisper(whisper_payload)
                recorder.record_hud_state(hud.snapshot())

            try:
                await websocket.send_json({"type": "transcript.output", "text": whisper_payload["audio_text"]})
                await websocket.send_json({"type": "whisper.payload", "payload": whisper_payload})
                await websocket.send_json({"type": "hud.state", "payload": hud.snapshot()})
            except Exception:
                return
