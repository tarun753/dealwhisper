from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .config import get_settings

try:
    from google.cloud import aiplatform
    from google.cloud import firestore
except ImportError:  # pragma: no cover - optional until backend deps are installed.
    aiplatform = None
    firestore = None


ToolHandler = Callable[..., Any]


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db():
    if firestore is None:
        return None
    try:
        return firestore.Client(project=get_settings().project_id)
    except Exception:
        return None


# ── FURNISHED INLINE DATA ──────────────────────────────────────────
# Rich mock data so tools return real intelligence without Firestore.

_MOCK_BUYER_PROFILES: dict[str, dict[str, Any]] = {
    "maya.chen@northstarhealthsystems.com": {
        "status": "returning_buyer",
        "email": "maya.chen@northstarhealthsystems.com",
        "company": "Northstar Health Systems",
        "name": "Maya Chen",
        "title": "VP Revenue Operations",
        "communication_style": "Analytical, low-ego, prefers proof before enthusiasm.",
        "objection_history": ["price", "authority", "trust"],
        "buying_signals_seen": ["implementation questions", "future-tense language", "term-length inquiry"],
        "past_call_summaries": [
            "Call 1: Discovery. Maya interested but unconvinced on rollout lift. Promised cleaner implementation story.",
            "Call 2: Demo. Healthcare proof point resonated. Budget concern surfaced. CFO influence implied.",
        ],
        "decision_making_pace": "Methodical until business case is quantified, then noticeably faster.",
        "risk_tolerance": "Moderate-low. Wants controlled rollout and peer validation.",
        "preferred_language_patterns": ["time to trust", "board confidence", "forecast accuracy"],
        "what_triggers_resistance": "Abstract ROI claims and implementation answers without specifics.",
    },
}

_MOCK_BATTLE_CARDS: dict[str, dict[str, Any]] = {
    "gong": {
        "competitor": "Gong",
        "status": "loaded",
        "our_advantages": [
            "Faster time to operational trust with less admin lift",
            "Real-time coaching during calls, not just post-call analysis",
            "Lighter implementation burden for RevOps teams",
            "Native audio whisper — no screen overlay the buyer can see",
        ],
        "their_weaknesses": [
            "Heavy implementation: 3-6 month enterprise rollout typical",
            "Post-call only — no real-time intervention capability",
            "Requires dedicated admin for ongoing configuration",
            "High per-seat cost at scale without proportional ROI proof",
        ],
        "win_stories": [
            "MedMetric switched after 4-month Gong implementation stalled. Live in 21 days with us.",
            "Cascade Health chose us over Gong specifically because of real-time coaching vs post-call reports.",
        ],
        "pricing_comparison": "Gong: $100-150/user/mo enterprise. Us: $70-95/user/mo with faster payback.",
        "key_differentiators": "Real-time vs post-call. Invisible overlay vs visible recording indicator.",
        "common_objections_when_they_come_up": "They will say Gong has more integrations. Redirect to time-to-value.",
        "proven_rebuttals": [
            "Gong tells you what went wrong yesterday. We change the outcome today.",
            "The question isn't feature count — it's how fast your team gets measurably better.",
        ],
    },
    "clari": {
        "competitor": "Clari",
        "status": "loaded",
        "our_advantages": [
            "Conversation intelligence plus real-time coaching, not just forecasting",
            "Lower implementation complexity for mid-market teams",
            "Real-time signals during calls, not just pipeline analytics",
        ],
        "their_weaknesses": [
            "Primarily a forecasting tool, conversation intelligence is secondary",
            "Implementation burden worries operations leaders",
            "Less granular call-level coaching — focuses on pipeline roll-up",
        ],
        "win_stories": [
            "Northstar Health was benchmarking Clari for forecasting but chose us because implementation stays inside current bandwidth.",
        ],
        "pricing_comparison": "Clari: $80-120/user/mo. Us: competitive with faster ROI proof cycle.",
        "key_differentiators": "We coach the conversation. Clari forecasts the pipeline. Different jobs.",
        "proven_rebuttals": [
            "Clari shows you the forecast. We change the calls that feed it.",
        ],
    },
    "salesforce": {
        "competitor": "Salesforce",
        "status": "loaded",
        "our_advantages": [
            "Purpose-built for live coaching, not a CRM with bolted-on intelligence",
            "Zero CRM migration required — we sit on top of any CRM",
            "Real-time intervention vs retrospective reporting",
        ],
        "their_weaknesses": [
            "Einstein AI is broad but shallow on conversation intelligence",
            "Massive platform complexity for teams that just need call coaching",
        ],
        "key_differentiators": "We complement Salesforce, we don't replace it.",
        "proven_rebuttals": [
            "We make your Salesforce data more accurate by coaching reps to capture better information live.",
        ],
    },
}

_MOCK_COMPANY_INTELLIGENCE: dict[str, dict[str, Any]] = {
    "northstar_health_systems": {
        "company": "Northstar Health Systems",
        "status": "enriched",
        "funding_status": "Series C, $180M raised. Profitable unit economics reported.",
        "recent_news": [
            "Announced ambulatory expansion in January 2026.",
            "Quietly posted finance systems roles last week — board visibility rising.",
            "New CRO hire from Optum suggests revenue acceleration push.",
        ],
        "hiring_signals": [
            "6 open RevOps and enablement roles after platform migration.",
            "Job descriptions reference Salesforce hygiene, forecasting accuracy, lead routing breakdowns.",
            "Finance systems roles suggest internal audit pressure increasing.",
        ],
        "leadership_changes": [
            "Maya Chen: VP RevOps, 14 months in seat. Former MedMetric (5 years).",
            "Liam Ortiz: CFO partner, new to the account. Controls budget sign-off.",
        ],
        "tech_stack": ["Salesforce CRM", "Marketo", "Snowflake", "Tableau"],
        "growth_trajectory": "Expanding. Board visibility rising. Tooling decisions pulled into near-term planning.",
        "glassdoor_sentiment": "Employee reviews mention reporting debt, tooling overlap, and forecasting frustration.",
    },
}

_MOCK_CASE_STUDIES: list[dict[str, Any]] = [
    {
        "industry": "healthcare",
        "company_name": "MedMetric",
        "company_size": "mid-market",
        "problem": "Forecast calls were inconsistent, reps missed competitive pressure live, leadership didn't trust call coaching.",
        "solution": "Deployed DealWhisper across 3 sales pods. Phased 21-day rollout. RevOps owned less than 2 hours/week.",
        "result": "42% improvement in forecast accuracy. 28% faster deal velocity. Rep coaching adoption hit 91% in 60 days.",
        "quote": "We went from guessing to knowing what was happening on every call in real time.",
    },
    {
        "industry": "healthcare",
        "company_name": "Cascade Health",
        "company_size": "enterprise",
        "problem": "Post-call tools created reporting debt. Reps ignored coaching because it came too late to matter.",
        "solution": "Real-time whisper coaching during live calls. Invisible overlay kept buyer experience clean.",
        "result": "34% close rate improvement in first quarter. Sales cycle shortened by 18 days on average.",
        "quote": "The difference between being told what you did wrong and being coached in the moment is everything.",
    },
    {
        "industry": "technology",
        "company_name": "Velocity SaaS",
        "company_size": "mid-market",
        "problem": "New AEs ramped too slowly. Average time to first close was 4.5 months.",
        "solution": "DealWhisper guided new reps through discovery, objection handling, and close techniques live.",
        "result": "Time to first close dropped to 2.8 months. New hire quota attainment up 37%.",
        "quote": "It's like having your best sales manager on every call, but they never take over.",
    },
    {
        "industry": "financial_services",
        "company_name": "Meridian Capital",
        "company_size": "enterprise",
        "problem": "Complex multi-stakeholder deals stalled because reps couldn't read the room across 4-6 buyers.",
        "solution": "Multi-stakeholder intelligence tracked each buyer's signals independently during group calls.",
        "result": "Win rate on 3+ stakeholder deals increased 29%. Average deal size up 22%.",
        "quote": "DealWhisper told our rep who the real decision maker was before the buyer even spoke.",
    },
]

_MOCK_OBJECTION_RESPONSES: dict[str, list[dict[str, Any]]] = {
    "price": [
        {
            "objection_class": "price",
            "response": "I hear you — budget is always real. Is the friction the absolute number, or confidence the return shows up fast enough?",
            "close_rate": 0.72,
            "context_notes": "Works best with analytical buyers. Diagnoses before discounting.",
        },
        {
            "objection_class": "price",
            "response": "What's the cost of NOT solving this over the next 12 months? Let's pressure-test payback together.",
            "close_rate": 0.68,
            "context_notes": "Effective when pain is already quantified in discovery.",
        },
        {
            "objection_class": "price",
            "response": "What would we need to prove in 30 days to unlock the budget?",
            "close_rate": 0.61,
            "context_notes": "Last resort. Use only after ROI reframe has been attempted.",
        },
    ],
    "authority": [
        {
            "objection_class": "authority",
            "response": "Of course. When you bring this to them, what's the one question they're most likely to ask?",
            "close_rate": 0.74,
            "context_notes": "Surfaces the hidden objection behind the authority deflection.",
        },
        {
            "objection_class": "authority",
            "response": "Who else needs to be involved? Can we get them on the next call together?",
            "close_rate": 0.66,
            "context_notes": "Direct path to the economic buyer. Use when genuine org process.",
        },
    ],
    "timing": [
        {
            "objection_class": "timing",
            "response": "Timing always matters. What does staying with your current solution cost per month while you wait?",
            "close_rate": 0.69,
            "context_notes": "Quantifies cost of inaction. Best when pain is already acknowledged.",
        },
        {
            "objection_class": "timing",
            "response": "Is there a version that fits current constraints? A phased start can prove value without the full commitment.",
            "close_rate": 0.63,
            "context_notes": "For genuine budget freezes. Offers structure, not reduction.",
        },
    ],
    "need": [
        {
            "objection_class": "need",
            "response": "What are you using now? What does it do well? I want to understand before I suggest anything.",
            "close_rate": 0.58,
            "context_notes": "Gets beneath the surface. Listen for the gap — it always exists.",
        },
    ],
    "trust": [
        {
            "objection_class": "trust",
            "response": "That's exactly the right question. Would it help to speak with our customer at MedMetric who was in exactly your position 12 months ago?",
            "close_rate": 0.71,
            "context_notes": "Social proof from similar company. Removes fear of being wrong.",
        },
    ],
    "competitor": [
        {
            "objection_class": "competitor",
            "response": "I'd expect you to look at everyone. What matters most in this decision? Let's make sure we're solving for that.",
            "close_rate": 0.67,
            "context_notes": "Shifts from feature comparison to decision criteria ownership.",
        },
    ],
    "hidden": [
        {
            "objection_class": "hidden",
            "response": "I want to make sure we address everything. What's the part you haven't said yet?",
            "close_rate": 0.64,
            "context_notes": "Direct surfacing. Use when body language contradicts words.",
        },
    ],
}

_MOCK_PRODUCT_KNOWLEDGE: dict[str, Any] = {
    "status": "ready",
    "relevant_features": [
        {"name": "Real-Time Audio Whisper", "description": "Native audio coaching delivered directly to salesperson's ear during live calls. Sub-800ms latency."},
        {"name": "Invisible HUD Overlay", "description": "Screen overlay with deal temperature, BANT tracker, and signal feed. Hidden from screen share via content protection."},
        {"name": "Body Language Engine", "description": "Micro-expression and posture analysis from buyer webcam. Detects contempt, fear, genuine interest, and suppressed emotion."},
        {"name": "Objection Classification", "description": "7-class real-time objection detection with proven response suggestions ranked by historical close rate."},
        {"name": "Multi-Stakeholder Intelligence", "description": "Tracks each buyer independently in group calls. Identifies economic buyer, champion, and blocker."},
        {"name": "Post-Call Debrief", "description": "Auto-generated follow-up email, CRM update, and coaching scorecard within 60 seconds of call end."},
    ],
    "roi_data": {
        "average_close_rate_improvement": "34%",
        "average_deal_velocity_improvement": "22%",
        "average_new_hire_ramp_reduction": "38%",
        "average_forecast_accuracy_improvement": "42%",
    },
    "pricing_options": {
        "starter": {"price": "$70/user/mo", "includes": "Real-time whispers, basic HUD, post-call debrief"},
        "professional": {"price": "$95/user/mo", "includes": "Full signal engine, battle cards, multi-stakeholder"},
        "enterprise": {"price": "Custom", "includes": "Firestore persistence, CRM integration, team analytics, SSO"},
    },
}


# ── TOOL IMPLEMENTATIONS ──────────────────────────────────────────

def lookup_buyer_profile(buyer_email: str, company_name: str) -> dict[str, Any]:
    db = _get_db()
    if db is not None:
        doc = db.collection("buyer_profiles").document(buyer_email).get()
        if doc.exists:
            return doc.to_dict()

    # Fall back to furnished mock data
    mock = _MOCK_BUYER_PROFILES.get(buyer_email.strip().lower())
    if mock:
        return mock

    # Fuzzy match on company name
    company_lower = company_name.strip().lower()
    for profile in _MOCK_BUYER_PROFILES.values():
        if company_lower in profile.get("company", "").lower():
            return profile

    return {"status": "new_buyer", "email": buyer_email, "company": company_name}


def load_battle_card(competitor_name: str) -> dict[str, Any]:
    db = _get_db()
    key = _normalize_key(competitor_name)
    if db is not None:
        doc = db.collection("battle_cards").document(key).get()
        if doc.exists:
            return doc.to_dict()

    mock = _MOCK_BATTLE_CARDS.get(key)
    if mock:
        return mock

    return {
        "competitor": competitor_name,
        "status": "not_found",
        "fallback": "Focus on your unique value. Ask the buyer's top decision criterion first.",
    }


def search_company_intelligence(company_name: str) -> dict[str, Any]:
    db = _get_db()
    key = _normalize_key(company_name)
    if db is not None:
        doc = db.collection("company_intelligence").document(key).get()
        if doc.exists:
            return doc.to_dict()

    mock = _MOCK_COMPANY_INTELLIGENCE.get(key)
    if mock:
        return mock

    return {"company": company_name, "status": "researching"}


def get_product_knowledge(query: str, context: str) -> dict[str, Any]:
    settings = get_settings()
    if aiplatform is not None:
        try:
            aiplatform.init(project=settings.project_id, location=settings.location)
        except Exception:
            pass

    # Always return furnished product knowledge
    return {
        **_MOCK_PRODUCT_KNOWLEDGE,
        "query": query,
        "context": context,
    }


def log_call_event(call_id: str, event_type: str, event_data: dict[str, Any], timestamp: str) -> dict[str, Any]:
    db = _get_db()
    payload = {
        "type": event_type,
        "data": event_data,
        "timestamp": timestamp or _utc_now_iso(),
    }

    if db is not None:
        try:
            db.collection("call_events").document(call_id).collection("events").add(payload)
            return {"status": "logged"}
        except Exception:
            pass

    return {"status": "buffered", "call_id": call_id, "event": payload}


def update_buyer_profile(buyer_email: str, new_signals: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    if db is not None:
        try:
            db.collection("buyer_profiles").document(buyer_email).set(new_signals, merge=True)
            return {"status": "updated"}
        except Exception:
            pass

    # Update in-memory mock if it exists
    key = buyer_email.strip().lower()
    if key in _MOCK_BUYER_PROFILES:
        _MOCK_BUYER_PROFILES[key].update(new_signals)
        return {"status": "updated_local"}

    return {"status": "buffered", "email": buyer_email, "signals": new_signals}


def get_proven_objection_responses(
    objection_class: str,
    buyer_profile: dict[str, Any] | None = None,
    deal_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db = _get_db()
    if db is not None and firestore is not None:
        try:
            docs = (
                db.collection("objection_responses")
                .where("objection_class", "==", objection_class)
                .order_by("close_rate", direction=firestore.Query.DESCENDING)
                .limit(3)
                .stream()
            )
            results = [doc.to_dict() for doc in docs]
            if results:
                return {"responses": results}
        except Exception:
            pass

    # Fall back to furnished mock data
    mock = _MOCK_OBJECTION_RESPONSES.get(objection_class.strip().lower(), [])
    return {
        "responses": mock,
        "objection_class": objection_class,
    }


def generate_post_call_debrief(call_id: str) -> dict[str, Any]:
    db = _get_db()
    if db is not None:
        try:
            events = (
                db.collection("call_events")
                .document(call_id)
                .collection("events")
                .order_by("timestamp")
                .stream()
            )
            event_list = [event.to_dict() for event in events]
            if event_list:
                return {"call_id": call_id, "events": event_list}
        except Exception:
            pass

    return {"call_id": call_id, "events": [], "status": "local_debrief"}


def draft_followup_email(
    buyer_name: str,
    commitments_made: list[str],
    next_steps: list[str],
    deal_context: dict[str, Any] | None = None,
) -> str:
    first_commitment = commitments_made[0] if commitments_made else "the priorities we discussed"
    first_step = next_steps[0] if next_steps else "lock the next meeting"
    company = (deal_context or {}).get("company", "your team")
    return (
        f"Subject: Next steps for {company}\n\n"
        f"{buyer_name}, thanks again for the conversation today. "
        f"You highlighted {first_commitment}, so I will follow up with the details needed to move that forward. "
        f"Our immediate next step is to {first_step}."
    )


def search_case_studies(industry: str, company_size: str | None = None, pain_point: str | None = None) -> list[dict[str, Any]]:
    db = _get_db()
    if db is not None:
        try:
            query = db.collection("case_studies").where("industry", "==", industry).limit(3)
            docs = query.stream()
            results = [doc.to_dict() for doc in docs]
            if results:
                if company_size:
                    results = [r for r in results if r.get("company_size") in {None, company_size}]
                return results[:3]
        except Exception:
            pass

    # Fall back to furnished mock data
    industry_lower = industry.strip().lower()
    results = [cs for cs in _MOCK_CASE_STUDIES if cs["industry"].lower() == industry_lower]

    if not results:
        # Fuzzy: return all case studies if no industry match
        results = list(_MOCK_CASE_STUDIES)

    if company_size:
        filtered = [r for r in results if r.get("company_size") in {None, company_size}]
        if filtered:
            results = filtered

    if pain_point:
        lowered = pain_point.lower()
        filtered = [
            r for r in results
            if lowered in str(r.get("problem", "")).lower() or lowered in str(r.get("solution", "")).lower()
        ]
        if filtered:
            results = filtered

    return results[:3]


# ── REGISTRY ──────────────────────────────────────────────────────

_TOOL_REGISTRY: dict[str, ToolHandler] = {
    "lookup_buyer_profile": lookup_buyer_profile,
    "load_battle_card": load_battle_card,
    "search_company_intelligence": search_company_intelligence,
    "get_product_knowledge": get_product_knowledge,
    "log_call_event": log_call_event,
    "update_buyer_profile": update_buyer_profile,
    "get_proven_objection_responses": get_proven_objection_responses,
    "generate_post_call_debrief": generate_post_call_debrief,
    "draft_followup_email": draft_followup_email,
    "search_case_studies": search_case_studies,
}

_NON_BLOCKING_TOOLS = {
    "lookup_buyer_profile",
    "load_battle_card",
    "search_company_intelligence",
    "get_product_knowledge",
    "log_call_event",
    "update_buyer_profile",
    "search_case_studies",
}


def get_tool_registry() -> dict[str, ToolHandler]:
    return _TOOL_REGISTRY.copy()


def is_non_blocking_tool(name: str) -> bool:
    return name in _NON_BLOCKING_TOOLS


def get_live_tool_declarations(enable_google_search: bool = False) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = [
        {
            "function_declarations": [
                {
                    "name": "lookup_buyer_profile",
                    "description": "Retrieve buyer behavioral profile including communication style, objection history, buying signals seen, decision-making pace, risk tolerance, and preferred language patterns.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "buyer_email": {"type": "string"},
                            "company_name": {"type": "string"},
                        },
                        "required": ["buyer_email", "company_name"],
                    },
                },
                {
                    "name": "load_battle_card",
                    "description": "Load competitive battle card with advantages, weaknesses, win stories, pricing comparison, key differentiators, and proven rebuttals.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "competitor_name": {"type": "string"},
                        },
                        "required": ["competitor_name"],
                    },
                },
                {
                    "name": "search_company_intelligence",
                    "description": "Get latest company intelligence: funding, news, hiring signals, leadership changes, tech stack, growth trajectory, and glassdoor sentiment.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "company_name": {"type": "string"},
                        },
                        "required": ["company_name"],
                    },
                },
                {
                    "name": "get_product_knowledge",
                    "description": "Search product knowledge for relevant features, case studies, ROI data, and pricing options matching the current conversation context.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "context": {"type": "string"},
                        },
                        "required": ["query", "context"],
                    },
                },
                {
                    "name": "log_call_event",
                    "description": "Log a real-time call event: objection_detected, buying_signal, whisper_delivered, deal_temp_change, close_window, competitor_mentioned, body_language_signal, commitment_made.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "call_id": {"type": "string"},
                            "event_type": {"type": "string"},
                            "event_data": {"type": "object"},
                            "timestamp": {"type": "string"},
                        },
                        "required": ["call_id", "event_type", "event_data", "timestamp"],
                    },
                },
                {
                    "name": "update_buyer_profile",
                    "description": "Update buyer behavioral profile with new signals discovered during this call: communication style, objection patterns, language that worked, resistance triggers.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "buyer_email": {"type": "string"},
                            "new_signals": {"type": "object"},
                        },
                        "required": ["buyer_email", "new_signals"],
                    },
                },
                {
                    "name": "get_proven_objection_responses",
                    "description": "Get top 3 highest-converting objection responses ranked by close rate for: price, authority, timing, need, trust, competitor, or hidden objection class.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "objection_class": {
                                "type": "string",
                                "enum": ["price", "authority", "timing", "need", "trust", "competitor", "hidden"],
                            },
                            "buyer_profile": {"type": "object"},
                            "deal_context": {"type": "object"},
                        },
                        "required": ["objection_class"],
                    },
                },
                {
                    "name": "generate_post_call_debrief",
                    "description": "Compile the full post-call debrief from stored event timeline: deal temperature changes, key moments, objection analysis, coaching metrics.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "call_id": {"type": "string"},
                        },
                        "required": ["call_id"],
                    },
                },
                {
                    "name": "draft_followup_email",
                    "description": "Generate personalized follow-up email based on call commitments. 3 sentences max, personal, reference exact buyer words, include specific next steps.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "buyer_name": {"type": "string"},
                            "commitments_made": {"type": "array", "items": {"type": "string"}},
                            "next_steps": {"type": "array", "items": {"type": "string"}},
                            "deal_context": {"type": "object"},
                        },
                        "required": ["buyer_name", "commitments_made", "next_steps"],
                    },
                },
                {
                    "name": "search_case_studies",
                    "description": "Find matching customer case studies for social proof with company name, problem, solution, result, and customer quote.",
                    "parameters_json_schema": {
                        "type": "object",
                        "properties": {
                            "industry": {"type": "string"},
                            "company_size": {"type": "string"},
                            "pain_point": {"type": "string"},
                        },
                        "required": ["industry"],
                    },
                },
            ]
        }
    ]

    if enable_google_search:
        tools.append({"google_search": {}})

    return tools
