from __future__ import annotations

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool

from .config import get_settings
from .system_instruction import PRODUCTION_SYSTEM_INSTRUCTION
from .tools import (
    draft_followup_email,
    generate_post_call_debrief,
    get_product_knowledge,
    get_proven_objection_responses,
    load_battle_card,
    log_call_event,
    lookup_buyer_profile,
    search_case_studies,
    search_company_intelligence,
    update_buyer_profile,
)


def build_agent(system_instruction: str = PRODUCTION_SYSTEM_INSTRUCTION) -> Agent:
    settings = get_settings()
    return Agent(
        name="DealWhisper",
        model=settings.live_model_id,
        description="Real-time sales negotiation co-pilot for live deal execution.",
        instruction=system_instruction,
        tools=[
            FunctionTool(lookup_buyer_profile),
            FunctionTool(load_battle_card),
            FunctionTool(search_company_intelligence),
            FunctionTool(get_product_knowledge),
            FunctionTool(log_call_event),
            FunctionTool(update_buyer_profile),
            FunctionTool(get_proven_objection_responses),
            FunctionTool(generate_post_call_debrief),
            FunctionTool(draft_followup_email),
            FunctionTool(search_case_studies),
        ],
    )


def build_runner(system_instruction: str = PRODUCTION_SYSTEM_INSTRUCTION) -> Runner:
    return Runner(
        agent=build_agent(system_instruction),
        app_name="DealWhisper",
        session_service=InMemorySessionService(),
    )
