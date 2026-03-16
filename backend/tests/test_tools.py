"""Tests for dealwhisper_backend.tools — tool functions and registry."""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from dealwhisper_backend.tools import (
    draft_followup_email,
    generate_post_call_debrief,
    get_live_tool_declarations,
    get_product_knowledge,
    get_proven_objection_responses,
    get_tool_registry,
    is_non_blocking_tool,
    load_battle_card,
    log_call_event,
    lookup_buyer_profile,
    search_case_studies,
    search_company_intelligence,
    update_buyer_profile,
    _MOCK_BATTLE_CARDS,
    _MOCK_BUYER_PROFILES,
    _MOCK_CASE_STUDIES,
    _MOCK_COMPANY_INTELLIGENCE,
    _MOCK_OBJECTION_RESPONSES,
    _MOCK_PRODUCT_KNOWLEDGE,
)


def _force_no_db():
    """Patch _get_db to return None so all tools use mock data."""
    return patch("dealwhisper_backend.tools._get_db", return_value=None)


# ── TOOL REGISTRY ──────────────────────────────────────────────────


class TestGetToolRegistry(unittest.TestCase):
    """get_tool_registry() returns all expected tool names."""

    EXPECTED_TOOLS = {
        "lookup_buyer_profile",
        "load_battle_card",
        "search_company_intelligence",
        "get_product_knowledge",
        "log_call_event",
        "update_buyer_profile",
        "get_proven_objection_responses",
        "generate_post_call_debrief",
        "draft_followup_email",
        "search_case_studies",
    }

    def test_registry_has_10_tools(self):
        reg = get_tool_registry()
        self.assertEqual(len(reg), 10)

    def test_registry_contains_all_names(self):
        reg = get_tool_registry()
        self.assertEqual(set(reg.keys()), self.EXPECTED_TOOLS)

    def test_registry_values_are_callable(self):
        reg = get_tool_registry()
        for name, fn in reg.items():
            with self.subTest(tool=name):
                self.assertTrue(callable(fn))

    def test_registry_is_a_copy(self):
        reg1 = get_tool_registry()
        reg2 = get_tool_registry()
        self.assertIsNot(reg1, reg2)
        reg1["injected"] = lambda: None
        self.assertNotIn("injected", get_tool_registry())


# ── LIVE TOOL DECLARATIONS ─────────────────────────────────────────


class TestGetLiveToolDeclarations(unittest.TestCase):
    """get_live_tool_declarations() returns valid tool declaration structures."""

    def test_returns_list(self):
        decls = get_live_tool_declarations()
        self.assertIsInstance(decls, list)

    def test_base_declarations_has_one_group(self):
        decls = get_live_tool_declarations(enable_google_search=False)
        self.assertEqual(len(decls), 1)

    def test_google_search_adds_extra_group(self):
        decls = get_live_tool_declarations(enable_google_search=True)
        self.assertEqual(len(decls), 2)
        self.assertIn("google_search", decls[1])

    def test_function_declarations_key_exists(self):
        decls = get_live_tool_declarations()
        self.assertIn("function_declarations", decls[0])

    def test_all_10_functions_declared(self):
        decls = get_live_tool_declarations()
        funcs = decls[0]["function_declarations"]
        self.assertEqual(len(funcs), 10)

    def test_each_function_has_name_and_description(self):
        decls = get_live_tool_declarations()
        funcs = decls[0]["function_declarations"]
        for func in funcs:
            with self.subTest(func=func.get("name")):
                self.assertIn("name", func)
                self.assertIn("description", func)
                self.assertIsInstance(func["name"], str)
                self.assertIsInstance(func["description"], str)
                self.assertGreater(len(func["description"]), 10)

    def test_each_function_has_parameters_json_schema(self):
        decls = get_live_tool_declarations()
        funcs = decls[0]["function_declarations"]
        for func in funcs:
            with self.subTest(func=func.get("name")):
                self.assertIn("parameters_json_schema", func)
                schema = func["parameters_json_schema"]
                self.assertEqual(schema["type"], "object")
                self.assertIn("properties", schema)
                self.assertIn("required", schema)

    def test_declared_names_match_registry(self):
        decls = get_live_tool_declarations()
        funcs = decls[0]["function_declarations"]
        declared_names = {f["name"] for f in funcs}
        registry_names = set(get_tool_registry().keys())
        self.assertEqual(declared_names, registry_names)


# ── NON-BLOCKING TOOLS ────────────────────────────────────────────


class TestIsNonBlockingTool(unittest.TestCase):
    """is_non_blocking_tool() correctly identifies non-blocking tools."""

    NON_BLOCKING = {
        "lookup_buyer_profile",
        "load_battle_card",
        "search_company_intelligence",
        "get_product_knowledge",
        "log_call_event",
        "update_buyer_profile",
        "search_case_studies",
    }
    BLOCKING = {
        "get_proven_objection_responses",
        "generate_post_call_debrief",
        "draft_followup_email",
    }

    def test_non_blocking_tools(self):
        for name in self.NON_BLOCKING:
            with self.subTest(tool=name):
                self.assertTrue(is_non_blocking_tool(name))

    def test_blocking_tools(self):
        for name in self.BLOCKING:
            with self.subTest(tool=name):
                self.assertFalse(is_non_blocking_tool(name))

    def test_unknown_tool_is_blocking(self):
        self.assertFalse(is_non_blocking_tool("nonexistent_tool"))


# ── INDIVIDUAL TOOL FUNCTIONS WITH MOCK DATA ──────────────────────


class TestLookupBuyerProfile(unittest.TestCase):
    """lookup_buyer_profile returns valid results with mock data."""

    @_force_no_db()
    def test_known_email(self, _mock):
        result = lookup_buyer_profile("maya.chen@northstarhealthsystems.com", "Northstar Health Systems")
        self.assertEqual(result["status"], "returning_buyer")
        self.assertEqual(result["name"], "Maya Chen")
        self.assertIn("communication_style", result)
        self.assertIn("objection_history", result)

    @_force_no_db()
    def test_fuzzy_company_match(self, _mock):
        result = lookup_buyer_profile("unknown@example.com", "Northstar Health")
        self.assertEqual(result["name"], "Maya Chen")

    @_force_no_db()
    def test_unknown_email_returns_new_buyer(self, _mock):
        result = lookup_buyer_profile("nobody@example.com", "Unknown Corp")
        self.assertEqual(result["status"], "new_buyer")
        self.assertEqual(result["email"], "nobody@example.com")
        self.assertEqual(result["company"], "Unknown Corp")

    @_force_no_db()
    def test_case_insensitive_email(self, _mock):
        result = lookup_buyer_profile("MAYA.CHEN@NORTHSTARHEALTHSYSTEMS.COM", "Northstar")
        self.assertEqual(result["name"], "Maya Chen")

    @_force_no_db()
    def test_result_has_past_call_summaries(self, _mock):
        result = lookup_buyer_profile("maya.chen@northstarhealthsystems.com", "Northstar")
        self.assertIsInstance(result["past_call_summaries"], list)
        self.assertGreater(len(result["past_call_summaries"]), 0)


class TestLoadBattleCard(unittest.TestCase):
    """load_battle_card returns valid results with mock data."""

    @_force_no_db()
    def test_gong_battle_card(self, _mock):
        result = load_battle_card("Gong")
        self.assertEqual(result["competitor"], "Gong")
        self.assertEqual(result["status"], "loaded")
        self.assertIn("our_advantages", result)
        self.assertIn("their_weaknesses", result)
        self.assertIn("win_stories", result)
        self.assertIn("proven_rebuttals", result)

    @_force_no_db()
    def test_clari_battle_card(self, _mock):
        result = load_battle_card("Clari")
        self.assertEqual(result["competitor"], "Clari")
        self.assertEqual(result["status"], "loaded")

    @_force_no_db()
    def test_salesforce_battle_card(self, _mock):
        result = load_battle_card("Salesforce")
        self.assertEqual(result["competitor"], "Salesforce")

    @_force_no_db()
    def test_unknown_competitor(self, _mock):
        result = load_battle_card("SomeUnknownVendor")
        self.assertEqual(result["status"], "not_found")
        self.assertIn("fallback", result)

    @_force_no_db()
    def test_case_insensitive(self, _mock):
        result = load_battle_card("GONG")
        self.assertEqual(result["competitor"], "Gong")

    @_force_no_db()
    def test_whitespace_trimmed(self, _mock):
        result = load_battle_card("  gong  ")
        self.assertEqual(result["competitor"], "Gong")


class TestSearchCompanyIntelligence(unittest.TestCase):
    """search_company_intelligence returns valid results with mock data."""

    @_force_no_db()
    def test_known_company(self, _mock):
        result = search_company_intelligence("Northstar Health Systems")
        self.assertEqual(result["company"], "Northstar Health Systems")
        self.assertEqual(result["status"], "enriched")
        self.assertIn("recent_news", result)
        self.assertIn("hiring_signals", result)
        self.assertIn("leadership_changes", result)
        self.assertIn("tech_stack", result)

    @_force_no_db()
    def test_unknown_company(self, _mock):
        result = search_company_intelligence("UnknownCorp")
        self.assertEqual(result["status"], "researching")

    @_force_no_db()
    def test_recent_news_is_list(self, _mock):
        result = search_company_intelligence("Northstar Health Systems")
        self.assertIsInstance(result["recent_news"], list)
        self.assertGreater(len(result["recent_news"]), 0)

    @_force_no_db()
    def test_hiring_signals_is_list(self, _mock):
        result = search_company_intelligence("Northstar Health Systems")
        self.assertIsInstance(result["hiring_signals"], list)
        self.assertGreater(len(result["hiring_signals"]), 0)


class TestGetProductKnowledge(unittest.TestCase):
    """get_product_knowledge returns valid results with mock data."""

    @_force_no_db()
    def test_returns_features(self, _mock):
        result = get_product_knowledge("real-time coaching", "demo call")
        self.assertIn("relevant_features", result)
        self.assertIsInstance(result["relevant_features"], list)
        self.assertGreater(len(result["relevant_features"]), 0)

    @_force_no_db()
    def test_returns_roi_data(self, _mock):
        result = get_product_knowledge("ROI", "pricing discussion")
        self.assertIn("roi_data", result)
        self.assertIn("average_close_rate_improvement", result["roi_data"])

    @_force_no_db()
    def test_returns_pricing_options(self, _mock):
        result = get_product_knowledge("pricing", "buyer asked about cost")
        self.assertIn("pricing_options", result)
        self.assertIn("starter", result["pricing_options"])
        self.assertIn("professional", result["pricing_options"])
        self.assertIn("enterprise", result["pricing_options"])

    @_force_no_db()
    def test_passes_query_and_context_through(self, _mock):
        result = get_product_knowledge("my query", "my context")
        self.assertEqual(result["query"], "my query")
        self.assertEqual(result["context"], "my context")

    @_force_no_db()
    def test_status_furnished(self, _mock):
        result = get_product_knowledge("anything", "anything")
        self.assertEqual(result["status"], "furnished")


class TestLogCallEvent(unittest.TestCase):
    """log_call_event returns valid results with mock data."""

    @_force_no_db()
    def test_returns_buffered_status(self, _mock):
        result = log_call_event("call-123", "objection_detected", {"class": "price"}, "2026-01-01T00:00:00Z")
        self.assertEqual(result["status"], "buffered")
        self.assertEqual(result["call_id"], "call-123")

    @_force_no_db()
    def test_event_payload_structure(self, _mock):
        result = log_call_event("call-456", "buying_signal", {"tier": 1}, "2026-01-01T00:00:00Z")
        event = result["event"]
        self.assertEqual(event["type"], "buying_signal")
        self.assertEqual(event["data"]["tier"], 1)
        self.assertEqual(event["timestamp"], "2026-01-01T00:00:00Z")

    @_force_no_db()
    def test_empty_timestamp_uses_fallback(self, _mock):
        result = log_call_event("call-789", "test", {}, "")
        # When timestamp is empty string (falsy), _utc_now_iso is used
        # The falsy empty string is passed directly since `timestamp or _utc_now_iso()` triggers
        event = result["event"]
        # Empty string is falsy, so it should be replaced with a UTC timestamp
        self.assertNotEqual(event["timestamp"], "")
        self.assertIn("T", event["timestamp"])  # ISO format


class TestUpdateBuyerProfile(unittest.TestCase):
    """update_buyer_profile returns valid results with mock data."""

    @_force_no_db()
    def test_known_buyer_updates_local(self, _mock):
        result = update_buyer_profile(
            "maya.chen@northstarhealthsystems.com",
            {"new_signal": "responded well to ROI framing"},
        )
        self.assertEqual(result["status"], "updated_local")

    @_force_no_db()
    def test_unknown_buyer_buffers(self, _mock):
        result = update_buyer_profile("unknown@example.com", {"note": "first contact"})
        self.assertEqual(result["status"], "buffered")

    @_force_no_db()
    def test_signals_included_in_buffer(self, _mock):
        signals = {"language_preference": "direct"}
        result = update_buyer_profile("someone@example.com", signals)
        self.assertEqual(result["signals"], signals)


class TestGetProvenObjectionResponses(unittest.TestCase):
    """get_proven_objection_responses returns valid results with mock data."""

    @_force_no_db()
    def test_price_objection_responses(self, _mock):
        result = get_proven_objection_responses("price")
        self.assertIn("responses", result)
        self.assertEqual(len(result["responses"]), 3)
        for resp in result["responses"]:
            self.assertEqual(resp["objection_class"], "price")
            self.assertIn("response", resp)
            self.assertIn("close_rate", resp)

    @_force_no_db()
    def test_authority_objection_responses(self, _mock):
        result = get_proven_objection_responses("authority")
        self.assertEqual(len(result["responses"]), 2)

    @_force_no_db()
    def test_timing_objection_responses(self, _mock):
        result = get_proven_objection_responses("timing")
        self.assertEqual(len(result["responses"]), 2)

    @_force_no_db()
    def test_need_objection_responses(self, _mock):
        result = get_proven_objection_responses("need")
        self.assertEqual(len(result["responses"]), 1)

    @_force_no_db()
    def test_trust_objection_responses(self, _mock):
        result = get_proven_objection_responses("trust")
        self.assertEqual(len(result["responses"]), 1)

    @_force_no_db()
    def test_competitor_objection_responses(self, _mock):
        result = get_proven_objection_responses("competitor")
        self.assertEqual(len(result["responses"]), 1)

    @_force_no_db()
    def test_hidden_objection_responses(self, _mock):
        result = get_proven_objection_responses("hidden")
        self.assertEqual(len(result["responses"]), 1)

    @_force_no_db()
    def test_unknown_class_returns_empty(self, _mock):
        result = get_proven_objection_responses("nonexistent")
        self.assertEqual(result["responses"], [])

    @_force_no_db()
    def test_close_rates_are_floats(self, _mock):
        result = get_proven_objection_responses("price")
        for resp in result["responses"]:
            self.assertIsInstance(resp["close_rate"], float)
            self.assertGreater(resp["close_rate"], 0)
            self.assertLessEqual(resp["close_rate"], 1)

    @_force_no_db()
    def test_objection_class_returned(self, _mock):
        result = get_proven_objection_responses("price")
        self.assertEqual(result["objection_class"], "price")


class TestGeneratePostCallDebrief(unittest.TestCase):
    """generate_post_call_debrief returns valid results with mock data."""

    @_force_no_db()
    def test_returns_call_id(self, _mock):
        result = generate_post_call_debrief("call-123")
        self.assertEqual(result["call_id"], "call-123")

    @_force_no_db()
    def test_returns_empty_events_locally(self, _mock):
        result = generate_post_call_debrief("call-123")
        self.assertEqual(result["events"], [])
        self.assertEqual(result["status"], "local_debrief")


class TestDraftFollowupEmail(unittest.TestCase):
    """draft_followup_email returns valid results with mock data."""

    def test_basic_email(self):
        result = draft_followup_email(
            buyer_name="Maya",
            commitments_made=["pilot program"],
            next_steps=["schedule demo"],
            deal_context={"company": "Northstar Health"},
        )
        self.assertIn("Subject:", result)
        self.assertIn("Maya", result)
        self.assertIn("pilot program", result)
        self.assertIn("schedule demo", result)
        self.assertIn("Northstar Health", result)

    def test_email_with_empty_commitments(self):
        result = draft_followup_email(
            buyer_name="Alex",
            commitments_made=[],
            next_steps=[],
        )
        self.assertIn("Alex", result)
        self.assertIn("the priorities we discussed", result)
        self.assertIn("lock the next meeting", result)

    def test_email_without_deal_context(self):
        result = draft_followup_email(
            buyer_name="Sam",
            commitments_made=["review pricing"],
            next_steps=["send proposal"],
        )
        self.assertIn("your team", result)

    def test_email_is_string(self):
        result = draft_followup_email("Test", ["a"], ["b"])
        self.assertIsInstance(result, str)

    def test_email_subject_includes_company(self):
        result = draft_followup_email("Test", ["a"], ["b"], {"company": "ACME"})
        self.assertTrue(result.startswith("Subject: Next steps for ACME"))


class TestSearchCaseStudies(unittest.TestCase):
    """search_case_studies returns valid results with mock data."""

    @_force_no_db()
    def test_healthcare_industry(self, _mock):
        results = search_case_studies("healthcare")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        for cs in results:
            self.assertEqual(cs["industry"], "healthcare")

    @_force_no_db()
    def test_technology_industry(self, _mock):
        results = search_case_studies("technology")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["industry"], "technology")

    @_force_no_db()
    def test_financial_services(self, _mock):
        results = search_case_studies("financial_services")
        self.assertGreater(len(results), 0)

    @_force_no_db()
    def test_unknown_industry_returns_all(self, _mock):
        results = search_case_studies("aerospace")
        # Falls back to returning all case studies
        self.assertGreater(len(results), 0)

    @_force_no_db()
    def test_max_3_results(self, _mock):
        results = search_case_studies("healthcare")
        self.assertLessEqual(len(results), 3)

    @_force_no_db()
    def test_filter_by_company_size(self, _mock):
        results = search_case_studies("healthcare", company_size="mid-market")
        for cs in results:
            self.assertEqual(cs["company_size"], "mid-market")

    @_force_no_db()
    def test_filter_by_pain_point(self, _mock):
        results = search_case_studies("healthcare", pain_point="forecast")
        self.assertGreater(len(results), 0)

    @_force_no_db()
    def test_case_study_has_required_keys(self, _mock):
        results = search_case_studies("healthcare")
        for cs in results:
            self.assertIn("company_name", cs)
            self.assertIn("problem", cs)
            self.assertIn("solution", cs)
            self.assertIn("result", cs)
            self.assertIn("quote", cs)


# ── MOCK DATA INTEGRITY ───────────────────────────────────────────


class TestMockDataIntegrity(unittest.TestCase):
    """Mock data fallbacks are well-structured and non-empty."""

    def test_buyer_profiles_not_empty(self):
        self.assertGreater(len(_MOCK_BUYER_PROFILES), 0)

    def test_buyer_profile_has_required_fields(self):
        for email, profile in _MOCK_BUYER_PROFILES.items():
            with self.subTest(email=email):
                self.assertIn("name", profile)
                self.assertIn("email", profile)
                self.assertIn("company", profile)
                self.assertIn("communication_style", profile)
                self.assertIn("objection_history", profile)

    def test_battle_cards_not_empty(self):
        self.assertGreater(len(_MOCK_BATTLE_CARDS), 0)

    def test_battle_card_has_required_fields(self):
        for key, card in _MOCK_BATTLE_CARDS.items():
            with self.subTest(competitor=key):
                self.assertIn("competitor", card)
                self.assertIn("status", card)
                self.assertEqual(card["status"], "loaded")

    def test_company_intelligence_not_empty(self):
        self.assertGreater(len(_MOCK_COMPANY_INTELLIGENCE), 0)

    def test_company_intelligence_has_required_fields(self):
        for key, intel in _MOCK_COMPANY_INTELLIGENCE.items():
            with self.subTest(company=key):
                self.assertIn("company", intel)
                self.assertIn("status", intel)
                self.assertIn("recent_news", intel)
                self.assertIn("hiring_signals", intel)

    def test_case_studies_not_empty(self):
        self.assertGreater(len(_MOCK_CASE_STUDIES), 0)

    def test_case_study_has_required_fields(self):
        for cs in _MOCK_CASE_STUDIES:
            with self.subTest(company=cs.get("company_name")):
                self.assertIn("industry", cs)
                self.assertIn("company_name", cs)
                self.assertIn("problem", cs)
                self.assertIn("solution", cs)
                self.assertIn("result", cs)
                self.assertIn("quote", cs)

    def test_objection_responses_not_empty(self):
        self.assertGreater(len(_MOCK_OBJECTION_RESPONSES), 0)

    def test_objection_responses_cover_all_classes(self):
        expected = {"price", "authority", "timing", "need", "trust", "competitor", "hidden"}
        self.assertEqual(set(_MOCK_OBJECTION_RESPONSES.keys()), expected)

    def test_objection_response_has_required_fields(self):
        for cls, responses in _MOCK_OBJECTION_RESPONSES.items():
            for resp in responses:
                with self.subTest(cls=cls):
                    self.assertIn("objection_class", resp)
                    self.assertIn("response", resp)
                    self.assertIn("close_rate", resp)

    def test_product_knowledge_not_empty(self):
        self.assertIn("relevant_features", _MOCK_PRODUCT_KNOWLEDGE)
        self.assertIn("roi_data", _MOCK_PRODUCT_KNOWLEDGE)
        self.assertIn("pricing_options", _MOCK_PRODUCT_KNOWLEDGE)

    def test_product_knowledge_features_have_name_and_description(self):
        for feature in _MOCK_PRODUCT_KNOWLEDGE["relevant_features"]:
            self.assertIn("name", feature)
            self.assertIn("description", feature)


# ── ALL 10 TOOLS RETURN VALID RESULTS ─────────────────────────────


class TestAll10ToolsReturnValidResults(unittest.TestCase):
    """All 10 tool functions return valid results with mock data."""

    @_force_no_db()
    def test_lookup_buyer_profile(self, _mock):
        result = lookup_buyer_profile("maya.chen@northstarhealthsystems.com", "Northstar")
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)

    @_force_no_db()
    def test_load_battle_card(self, _mock):
        result = load_battle_card("Gong")
        self.assertIsInstance(result, dict)
        self.assertIn("competitor", result)

    @_force_no_db()
    def test_search_company_intelligence(self, _mock):
        result = search_company_intelligence("Northstar Health Systems")
        self.assertIsInstance(result, dict)
        self.assertIn("company", result)

    @_force_no_db()
    def test_get_product_knowledge(self, _mock):
        result = get_product_knowledge("features", "demo")
        self.assertIsInstance(result, dict)
        self.assertIn("relevant_features", result)

    @_force_no_db()
    def test_log_call_event(self, _mock):
        result = log_call_event("call-1", "test_event", {"key": "val"}, "2026-01-01T00:00:00Z")
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)

    @_force_no_db()
    def test_update_buyer_profile(self, _mock):
        result = update_buyer_profile("maya.chen@northstarhealthsystems.com", {"new": "data"})
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)

    @_force_no_db()
    def test_get_proven_objection_responses(self, _mock):
        result = get_proven_objection_responses("price")
        self.assertIsInstance(result, dict)
        self.assertIn("responses", result)

    @_force_no_db()
    def test_generate_post_call_debrief(self, _mock):
        result = generate_post_call_debrief("call-1")
        self.assertIsInstance(result, dict)
        self.assertIn("call_id", result)

    def test_draft_followup_email(self):
        result = draft_followup_email("Maya", ["pilot"], ["demo"])
        self.assertIsInstance(result, str)
        self.assertIn("Subject:", result)

    @_force_no_db()
    def test_search_case_studies(self, _mock):
        result = search_case_studies("healthcare")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
