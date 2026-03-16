"""Tests for dealwhisper_backend.hud — HUD state manager."""

from __future__ import annotations

import time
import unittest
from copy import deepcopy
from unittest.mock import patch

from dealwhisper_backend.hud import (
    CLOSE_WINDOW_SECONDS,
    CLOSE_WINDOW_THRESHOLD,
    HudStateManager,
    build_initial_hud_state,
    _compact_hud_text,
    _detect_buying_signals,
    _detect_objection_class,
    _infer_color,
    _infer_urgency,
    _infer_whisper_type,
    _next_stage,
    _truncate_words,
)


class TestBuildInitialHudState(unittest.TestCase):
    """build_initial_hud_state returns correct defaults."""

    def test_default_temperature(self):
        state = build_initial_hud_state()
        self.assertEqual(state["deal_temperature"], 50)

    def test_default_sentiment(self):
        state = build_initial_hud_state()
        self.assertEqual(state["sentiment"], "Neutral")

    def test_default_stage(self):
        state = build_initial_hud_state()
        self.assertEqual(state["negotiation_stage"], "Opening")

    def test_default_bant_keys(self):
        state = build_initial_hud_state()
        for key in ("budget", "authority", "need", "timeline"):
            self.assertIn(key, state["bant"])

    def test_bant_levels_start_at_zero(self):
        state = build_initial_hud_state()
        for key in ("budget", "authority", "need", "timeline"):
            self.assertEqual(state["bant"][key]["level"], 0)

    def test_default_bant_labels(self):
        state = build_initial_hud_state()
        self.assertEqual(state["bant"]["budget"]["label"], "Unknown")
        self.assertEqual(state["bant"]["authority"]["label"], "Unknown")
        self.assertEqual(state["bant"]["need"]["label"], "Latent")
        self.assertEqual(state["bant"]["timeline"]["label"], "Absent")

    def test_default_buying_signals(self):
        state = build_initial_hud_state()
        self.assertEqual(state["buying_signals_count"]["tier1"], 0)
        self.assertEqual(state["buying_signals_count"]["tier2"], 0)
        self.assertFalse(state["buying_signals_count"]["close_window_open"])

    def test_default_empty_lists(self):
        state = build_initial_hud_state()
        self.assertEqual(state["active_signals"], [])
        self.assertEqual(state["buyer_commitments"], [])

    def test_default_strategy_card(self):
        state = build_initial_hud_state()
        self.assertIn("goal", state["strategy_card"])
        self.assertIn("anchor", state["strategy_card"])
        self.assertIn("floor", state["strategy_card"])
        self.assertIn("watch_for", state["strategy_card"])
        self.assertIn("edge", state["strategy_card"])

    def test_custom_strategy_card(self):
        custom = {
            "goal": "Close deal by EOQ.",
            "anchor": "$80k",
            "floor": "$60k",
            "watch_for": "CFO veto.",
            "edge": "Speed to value.",
        }
        state = build_initial_hud_state(strategy_card=custom)
        self.assertEqual(state["strategy_card"]["goal"], "Close deal by EOQ.")
        self.assertEqual(state["strategy_card"]["anchor"], "$80k")
        self.assertEqual(state["strategy_card"]["floor"], "$60k")

    def test_partial_strategy_card_uses_defaults(self):
        state = build_initial_hud_state(strategy_card={"goal": "Pilot close."})
        self.assertEqual(state["strategy_card"]["goal"], "Pilot close.")
        self.assertEqual(state["strategy_card"]["anchor"], "TBD")

    def test_default_misc_fields(self):
        state = build_initial_hud_state()
        self.assertEqual(state["concessions_made"], 0)
        self.assertTrue(state["last_concession_got_return"])
        self.assertIsNone(state["detected_objection_class"])
        self.assertIsNone(state["active_battle_card"])
        self.assertEqual(state["time_elapsed_seconds"], 0)

    def test_talk_ratio_defaults(self):
        state = build_initial_hud_state()
        self.assertEqual(state["talk_ratio"]["salesperson_pct"], 0)
        self.assertEqual(state["talk_ratio"]["buyer_pct"], 0)
        self.assertEqual(state["talk_ratio"]["status"], "ok")
        self.assertEqual(state["talk_ratio"]["target_pct"], 40)


class TestHudStateManagerSnapshot(unittest.TestCase):
    """HudStateManager.snapshot() returns a deep copy."""

    def test_snapshot_returns_dict(self):
        mgr = HudStateManager()
        snap = mgr.snapshot()
        self.assertIsInstance(snap, dict)

    def test_snapshot_is_deep_copy(self):
        mgr = HudStateManager()
        snap1 = mgr.snapshot()
        snap1["deal_temperature"] = 999
        snap1["active_signals"].append({"text": "injected"})
        snap2 = mgr.snapshot()
        self.assertEqual(snap2["deal_temperature"], 50)
        self.assertEqual(len(snap2["active_signals"]), 0)

    def test_snapshot_matches_initial_state(self):
        mgr = HudStateManager()
        snap = mgr.snapshot()
        expected = build_initial_hud_state()
        self.assertEqual(snap, expected)


class TestApplyInputTranscriptBANT(unittest.TestCase):
    """apply_input_transcript detects BANT keywords."""

    def test_budget_keyword(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("What is the budget for this project?")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["bant"]["budget"]["level"], 55)
        self.assertEqual(snap["bant"]["budget"]["label"], "Approximate")

    def test_budget_keyword_expensive(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("That seems really expensive for our team.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["bant"]["budget"]["level"], 55)

    def test_budget_keyword_cost(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We need to understand the cost first.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["bant"]["budget"]["level"], 55)

    def test_authority_boss(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("I need to check with my boss on this.")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["authority"]["level"], 45)
        self.assertEqual(snap["bant"]["authority"]["label"], "Influencer")

    def test_authority_committee(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("The committee will need to review this.")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["authority"]["level"], 45)

    def test_authority_loop_in(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Let me loop in our CFO next week.")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["authority"]["level"], 45)

    def test_need_keywords(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We have a real need for better forecasting.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["bant"]["need"]["level"], 70)
        self.assertEqual(snap["bant"]["need"]["label"], "Acknowledged")

    def test_need_pain(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("The pain is that reps are not hitting quota.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["bant"]["need"]["level"], 70)

    def test_timeline_this_quarter(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We want to deploy something this quarter.")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["timeline"]["level"], 60)
        self.assertEqual(snap["bant"]["timeline"]["label"], "Defined")

    def test_timeline_pilot(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Can we start with a pilot?")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["timeline"]["level"], 60)

    def test_budget_level_only_increases(self):
        mgr = HudStateManager()
        # Set budget to a high level manually
        mgr._state["bant"]["budget"] = {"level": 90, "label": "Confirmed"}
        mgr.apply_input_transcript("What does price look like?")
        snap = mgr.snapshot()
        self.assertEqual(snap["bant"]["budget"]["level"], 90)


class TestApplyInputTranscriptBuyingSignals(unittest.TestCase):
    """apply_input_transcript detects buying signals (tier1 and tier2)."""

    def test_tier1_signal_move_forward(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("I think we should move forward with this.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier1"], 1)

    def test_tier1_signal_next_steps(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("What are the next steps from here?")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier1"], 1)

    def test_tier1_signal_send_proposal(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Can you send the proposal over?")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier1"], 1)

    def test_tier1_raises_temperature(self):
        mgr = HudStateManager()
        initial_temp = mgr.snapshot()["deal_temperature"]
        mgr.apply_input_transcript("When we implement this, what does onboarding look like?")
        snap = mgr.snapshot()
        self.assertGreater(snap["deal_temperature"], initial_temp)

    def test_tier1_direction_rising(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        snap = mgr.snapshot()
        self.assertEqual(snap["deal_temp_direction"], "rising")

    def test_tier2_signal_pricing_question(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("What does pricing look like for your plans?")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier2"], 1)

    def test_tier2_signal_interesting(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("That's interesting, tell me more.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier2"], 1)

    def test_tier2_raises_temperature_less(self):
        mgr = HudStateManager()
        initial_temp = mgr.snapshot()["deal_temperature"]
        mgr.apply_input_transcript("That's interesting.")
        snap = mgr.snapshot()
        self.assertGreater(snap["deal_temperature"], initial_temp)
        # Tier2 adds +2, tier1 adds +5 per signal
        self.assertLessEqual(snap["deal_temperature"], initial_temp + 2)

    def test_multiple_tier1_in_one_transcript(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Send the proposal and let's discuss next steps and how do we get started.")
        snap = mgr.snapshot()
        self.assertGreaterEqual(snap["buying_signals_count"]["tier1"], 2)

    def test_no_signal_for_plain_text(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("The weather is nice today.")
        snap = mgr.snapshot()
        self.assertEqual(snap["buying_signals_count"]["tier1"], 0)
        self.assertEqual(snap["buying_signals_count"]["tier2"], 0)

    def test_signal_pushes_active_signal(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        snap = mgr.snapshot()
        signal_texts = [s["text"] for s in snap["active_signals"]]
        self.assertTrue(any("Tier 1" in t for t in signal_texts))


class TestCloseWindow(unittest.TestCase):
    """Close window opens after 3+ Tier 1 signals."""

    def test_close_window_opens_after_threshold(self):
        mgr = HudStateManager()
        # Feed 3 separate Tier 1 signals
        mgr.apply_input_transcript("How do we get started?")
        mgr.apply_input_transcript("Can you send the proposal?")
        mgr.apply_input_transcript("What are the next steps?")
        snap = mgr.snapshot()
        self.assertTrue(snap["buying_signals_count"]["close_window_open"])

    def test_close_window_not_open_under_threshold(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        mgr.apply_input_transcript("Can you send the proposal?")
        snap = mgr.snapshot()
        self.assertFalse(snap["buying_signals_count"]["close_window_open"])

    def test_close_window_sets_sentiment_warm_or_hot(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        mgr.apply_input_transcript("Send the proposal please.")
        mgr.apply_input_transcript("What are the next steps?")
        snap = mgr.snapshot()
        self.assertIn(snap["sentiment"], ("Warm", "Hot"))

    def test_close_window_boosts_temperature(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Move forward with this.")
        mgr.apply_input_transcript("Send a proposal over.")
        temp_before_third = mgr.snapshot()["deal_temperature"]
        mgr.apply_input_transcript("What are the next steps?")
        snap = mgr.snapshot()
        # Should get +5 for the tier1 signal AND +10 for close window opening
        self.assertGreater(snap["deal_temperature"], temp_before_third)

    def test_close_window_pushes_signal(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        mgr.apply_input_transcript("Send the proposal.")
        mgr.apply_input_transcript("Next steps please.")
        snap = mgr.snapshot()
        signal_texts = [s["text"] for s in snap["active_signals"]]
        self.assertTrue(any("CLOSE WINDOW OPEN" in t for t in signal_texts))

    def test_close_window_only_triggers_once(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("How do we get started?")
        mgr.apply_input_transcript("Send the proposal.")
        mgr.apply_input_transcript("Next steps please.")
        temp_after_open = mgr.snapshot()["deal_temperature"]
        # Fourth Tier 1 signal should NOT re-trigger the +10 close window bonus
        mgr.apply_input_transcript("Move forward now.")
        snap = mgr.snapshot()
        # Only +5 for the new tier1 signal, no additional +10
        self.assertLessEqual(snap["deal_temperature"], min(100, temp_after_open + 5))


class TestObjectionDetection(unittest.TestCase):
    """Objection detection for each class."""

    def test_price_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("That is too expensive for us.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "price")

    def test_price_discount(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Can you give us a discount?")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "price")

    def test_authority_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("I need to check with my team before we decide.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "authority")

    def test_authority_board_approval(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("This will require board approval.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "authority")

    def test_timing_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("It's not the right time for us right now.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "timing")

    def test_timing_next_quarter(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Can you come back in next quarter?")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "timing")

    def test_need_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We already have something that does this.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "need")

    def test_need_not_priority(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("This is not a priority for us right now.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "need")

    def test_trust_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We have been burned before by vendors.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "trust")

    def test_trust_prove_it(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("You'll need to prove it works first.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "trust")

    def test_competitor_objection(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We are also talking to Gong about this.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "competitor")

    def test_competitor_clari(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Clari already does that for us.")
        snap = mgr.snapshot()
        self.assertEqual(snap["detected_objection_class"], "competitor")

    def test_objection_lowers_temperature(self):
        mgr = HudStateManager()
        initial_temp = mgr.snapshot()["deal_temperature"]
        mgr.apply_input_transcript("That is too expensive.")
        snap = mgr.snapshot()
        self.assertLess(snap["deal_temperature"], initial_temp)

    def test_objection_sets_falling_direction(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("We have been burned before.")
        snap = mgr.snapshot()
        self.assertEqual(snap["deal_temp_direction"], "falling")

    def test_objection_pushes_signal(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("That is too expensive.")
        snap = mgr.snapshot()
        signal_texts = [s["text"] for s in snap["active_signals"]]
        self.assertTrue(any("Objection" in t for t in signal_texts))

    def test_no_objection_for_plain_text(self):
        result = _detect_objection_class("The weather is great today.")
        self.assertIsNone(result)


class TestApplyWhisper(unittest.TestCase):
    """apply_whisper infers correct whisper_type, urgency, and color."""

    def test_close_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Close now! Summary close.")
        self.assertEqual(result["whisper_type"], "CLOSE")

    def test_close_urgency_critical(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Close window is open.")
        self.assertEqual(result["urgency"], "CRITICAL")

    def test_close_color_red(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Close now!")
        self.assertEqual(result["hud_color"], "red")

    def test_anchor_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Anchor your number first.")
        self.assertEqual(result["whisper_type"], "ANCHOR")

    def test_anchor_urgency_critical(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Set your anchor now.")
        self.assertEqual(result["urgency"], "CRITICAL")

    def test_anchor_color_purple(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Anchor the number first.")
        self.assertEqual(result["hud_color"], "purple")

    def test_battle_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Use the battle card for Gong now.")
        self.assertEqual(result["whisper_type"], "BATTLE")

    def test_battle_urgency_high(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Competitor mentioned. Load battle card.")
        self.assertEqual(result["urgency"], "HIGH")

    def test_battle_color_purple(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Clari criterion comparison needed.")
        self.assertEqual(result["hud_color"], "purple")

    def test_hold_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Hold the silence. They are deciding.")
        self.assertEqual(result["whisper_type"], "HOLD")

    def test_hold_urgency_high(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Wait. Don't speak yet.")
        self.assertEqual(result["urgency"], "HIGH")

    def test_hold_color_yellow(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Hold. They are thinking.")
        self.assertEqual(result["hud_color"], "yellow")

    def test_warn_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Warning: risk of losing them. Surface the concern.")
        self.assertEqual(result["whisper_type"], "WARN")

    def test_warn_color_red(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Warning detected. Objection incoming.")
        self.assertEqual(result["hud_color"], "red")

    def test_reframe_whisper_type(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Reframe back to value proposition.")
        self.assertEqual(result["whisper_type"], "REFRAME")

    def test_reframe_color_blue(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Redirect the conversation back to value.")
        self.assertEqual(result["hud_color"], "blue")

    def test_move_whisper_type_default(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Ask about their team structure.")
        self.assertEqual(result["whisper_type"], "MOVE")

    def test_move_color_green(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Ask about their quarterly goals.")
        self.assertEqual(result["hud_color"], "green")

    def test_move_urgency_medium(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Ask about their current process.")
        self.assertEqual(result["urgency"], "MEDIUM")

    def test_whisper_result_has_all_keys(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Some coaching whisper.")
        expected_keys = {
            "whisper_type", "urgency", "audio_text", "hud_text",
            "hud_color", "display_duration_seconds", "confidence",
            "trigger", "suggested_exact_words", "suppress_if_speaking",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_close_whisper_raises_temperature(self):
        mgr = HudStateManager()
        initial_temp = mgr.snapshot()["deal_temperature"]
        mgr.apply_whisper("Close now! The deal is ready.")
        snap = mgr.snapshot()
        self.assertGreater(snap["deal_temperature"], initial_temp)

    def test_close_whisper_sets_hot_sentiment(self):
        mgr = HudStateManager()
        mgr.apply_whisper("Close now!")
        snap = mgr.snapshot()
        self.assertEqual(snap["sentiment"], "Hot")

    def test_warn_whisper_lowers_temperature(self):
        mgr = HudStateManager()
        initial_temp = mgr.snapshot()["deal_temperature"]
        mgr.apply_whisper("Warning: they are disengaging.")
        snap = mgr.snapshot()
        self.assertLess(snap["deal_temperature"], initial_temp)

    def test_confidence_critical(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Close now!")
        self.assertEqual(result["confidence"], 0.92)

    def test_confidence_high(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Warning: objection detected.")
        self.assertEqual(result["confidence"], 0.82)

    def test_confidence_medium(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Ask about their roadmap.")
        self.assertEqual(result["confidence"], 0.74)

    def test_display_duration_always_4(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Whatever you want to say.")
        self.assertEqual(result["display_duration_seconds"], 4)

    def test_trigger_is_live_model_output(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Test whisper.")
        self.assertEqual(result["trigger"], "live_model_output")

    def test_suppress_if_speaking_true(self):
        mgr = HudStateManager()
        result = mgr.apply_whisper("Test.")
        self.assertTrue(result["suppress_if_speaking"])


class TestCommitmentTracking(unittest.TestCase):
    """Commitment tracking works."""

    def test_i_agree_adds_commitment(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("I agree, let's go with the professional plan.")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["buyer_commitments"]), 1)

    def test_lets_do_adds_commitment(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Let's do the pilot first.")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["buyer_commitments"]), 1)

    def test_sounds_good_adds_commitment(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Sounds good, that works for us.")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["buyer_commitments"]), 1)

    def test_commitment_truncated_to_15_words(self):
        mgr = HudStateManager()
        long_text = "I agree " + " ".join(["word"] * 20)
        mgr.apply_input_transcript(long_text)
        snap = mgr.snapshot()
        self.assertLessEqual(len(snap["buyer_commitments"][0].split()), 15)

    def test_max_5_commitments_kept(self):
        mgr = HudStateManager()
        for i in range(7):
            mgr.apply_input_transcript(f"I agree to point number {i}.")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["buyer_commitments"]), 5)

    def test_plain_text_no_commitment(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Tell me more about your product.")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["buyer_commitments"]), 0)


class TestSentimentFromTemperature(unittest.TestCase):
    """Sentiment derivation from temperature."""

    def test_hot_at_85(self):
        mgr = HudStateManager()
        mgr._state["deal_temperature"] = 84
        # One tier1 adds +5 => 89 => Hot
        mgr.apply_input_transcript("How do we get started?")
        snap = mgr.snapshot()
        self.assertEqual(snap["sentiment"], "Hot")

    def test_warm_range(self):
        mgr = HudStateManager()
        mgr._state["deal_temperature"] = 72
        # Trigger the sentiment recalc with a neutral transcript
        mgr.apply_input_transcript("We have a need for this.")
        snap = mgr.snapshot()
        # Temperature is 72, need detection does not move temperature
        # But need keyword triggers bant, not temp. 72 >= 70 => Warm
        self.assertEqual(snap["sentiment"], "Warm")

    def test_neutral_at_50(self):
        mgr = HudStateManager()
        mgr.apply_input_transcript("Tell me about your company history.")
        snap = mgr.snapshot()
        # No signals detected, temp stays at 50 => Neutral
        self.assertEqual(snap["sentiment"], "Neutral")

    def test_cool_range(self):
        mgr = HudStateManager()
        mgr._state["deal_temperature"] = 35
        mgr.apply_input_transcript("The weather is fine.")
        snap = mgr.snapshot()
        self.assertEqual(snap["sentiment"], "Cool")

    def test_cold_under_30(self):
        mgr = HudStateManager()
        mgr._state["deal_temperature"] = 25
        mgr.apply_input_transcript("Nothing relevant here.")
        snap = mgr.snapshot()
        self.assertEqual(snap["sentiment"], "Cold")

    def test_objection_can_push_to_cool(self):
        mgr = HudStateManager()
        mgr._state["deal_temperature"] = 33
        mgr.apply_input_transcript("That is too expensive for us.")
        snap = mgr.snapshot()
        # 33 - 5 = 28 < 30 => Cold
        self.assertEqual(snap["sentiment"], "Cold")


class TestCompactHudText(unittest.TestCase):
    """_compact_hud_text returns expected summaries."""

    def test_rollout_and_cost_of_waiting(self):
        result = _compact_hud_text("Prove rollout then address cost of waiting.")
        self.assertEqual(result, "PROVE ROLLOUT THEN COST")

    def test_competitor_criterion(self):
        result = _compact_hud_text("Win on this criterion vs competitor.")
        self.assertEqual(result, "WIN ON CRITERION")

    def test_discount_probe(self):
        result = _compact_hud_text("Probe the discount question and ROI.")
        self.assertEqual(result, "PROBE ROI OR CEILING")

    def test_close_now(self):
        result = _compact_hud_text("Close now and get next step.")
        self.assertIn("CLOSE NOW", result)

    def test_anchor_first(self):
        result = _compact_hud_text("Set your anchor number first.")
        self.assertIn("ANCHOR FIRST", result)

    def test_hold_silence(self):
        result = _compact_hud_text("Hold the silence. They are deciding.")
        self.assertEqual(result, "HOLD THE SILENCE")

    def test_stop_selling(self):
        result = _compact_hud_text("They said yes. Stop selling now.")
        self.assertIn("STOP SELLING", result)

    def test_surface_concern(self):
        result = _compact_hud_text("Surface the concern. What's still open?")
        self.assertEqual(result, "SURFACE THE CONCERN")

    def test_fallback_truncates_to_uppercase(self):
        result = _compact_hud_text("Ask about their org chart and team dynamics today")
        # Falls through all checks, truncates to 5 words, uppercased
        words = result.split()
        self.assertLessEqual(len(words), 5)
        self.assertEqual(result, result.upper())


class TestInferWhisperType(unittest.TestCase):
    """_infer_whisper_type correctly classifies text."""

    def test_close(self):
        self.assertEqual(_infer_whisper_type("Close now"), "CLOSE")

    def test_anchor(self):
        self.assertEqual(_infer_whisper_type("Anchor price first"), "ANCHOR")

    def test_battle(self):
        self.assertEqual(_infer_whisper_type("Load the battle card"), "BATTLE")

    def test_hold(self):
        self.assertEqual(_infer_whisper_type("Hold the silence"), "HOLD")

    def test_reframe(self):
        self.assertEqual(_infer_whisper_type("Reframe back to value"), "REFRAME")

    def test_warn(self):
        self.assertEqual(_infer_whisper_type("Warning about risk"), "WARN")

    def test_default_move(self):
        self.assertEqual(_infer_whisper_type("Ask about their goals"), "MOVE")


class TestInferUrgency(unittest.TestCase):
    """_infer_urgency correctly classifies urgency."""

    def test_close_is_critical(self):
        self.assertEqual(_infer_urgency("Close the deal", "CLOSE"), "CRITICAL")

    def test_anchor_is_critical(self):
        self.assertEqual(_infer_urgency("Set anchor", "ANCHOR"), "CRITICAL")

    def test_now_keyword_is_high(self):
        self.assertEqual(_infer_urgency("Do it now", "MOVE"), "HIGH")

    def test_warn_type_is_high(self):
        self.assertEqual(_infer_urgency("Something", "WARN"), "HIGH")

    def test_hold_type_is_high(self):
        self.assertEqual(_infer_urgency("Something", "HOLD"), "HIGH")

    def test_battle_type_is_high(self):
        self.assertEqual(_infer_urgency("Something", "BATTLE"), "HIGH")

    def test_default_is_medium(self):
        self.assertEqual(_infer_urgency("Generic advice", "MOVE"), "MEDIUM")


class TestInferColor(unittest.TestCase):
    """_infer_color maps whisper types to colors."""

    def test_move_green(self):
        self.assertEqual(_infer_color("MOVE"), "green")

    def test_hold_yellow(self):
        self.assertEqual(_infer_color("HOLD"), "yellow")

    def test_warn_red(self):
        self.assertEqual(_infer_color("WARN"), "red")

    def test_close_red(self):
        self.assertEqual(_infer_color("CLOSE"), "red")

    def test_reframe_blue(self):
        self.assertEqual(_infer_color("REFRAME"), "blue")

    def test_battle_purple(self):
        self.assertEqual(_infer_color("BATTLE"), "purple")

    def test_anchor_purple(self):
        self.assertEqual(_infer_color("ANCHOR"), "purple")

    def test_unknown_defaults_green(self):
        self.assertEqual(_infer_color("UNKNOWN"), "green")


class TestNextStage(unittest.TestCase):
    """_next_stage transitions correctly."""

    def test_post_close(self):
        self.assertEqual(_next_stage("Close", "Stop selling. They said yes."), "Post-Close")

    def test_close_stage(self):
        self.assertEqual(_next_stage("Bargaining", "Close now."), "Close")

    def test_bargaining(self):
        self.assertEqual(_next_stage("Demo", "Let's talk about discount options."), "Bargaining")

    def test_objections(self):
        self.assertEqual(_next_stage("Demo", "I have a concern about the price."), "Objections")

    def test_demo(self):
        self.assertEqual(_next_stage("Discovery", "Can you show me a demo?"), "Demo")

    def test_discovery(self):
        self.assertEqual(_next_stage("Opening", "Tell me about your pain points."), "Discovery")

    def test_no_match_keeps_current(self):
        self.assertEqual(_next_stage("Opening", "Hello there."), "Opening")


class TestDetectBuyingSignals(unittest.TestCase):
    """_detect_buying_signals returns correct tier counts."""

    def test_no_signals(self):
        self.assertEqual(_detect_buying_signals("The weather is nice."), (0, 0))

    def test_single_tier1(self):
        t1, t2 = _detect_buying_signals("Can you send the proposal?")
        self.assertEqual(t1, 1)
        self.assertEqual(t2, 0)

    def test_single_tier2(self):
        t1, t2 = _detect_buying_signals("That's interesting.")
        self.assertEqual(t1, 0)
        self.assertEqual(t2, 1)

    def test_mixed_signals(self):
        t1, t2 = _detect_buying_signals("What are the next steps? That makes sense.")
        self.assertGreaterEqual(t1, 1)
        self.assertGreaterEqual(t2, 1)


class TestDetectObjectionClass(unittest.TestCase):
    """_detect_objection_class returns correct class."""

    def test_all_classes(self):
        cases = {
            "price": "That is too expensive",
            "authority": "I need to check with my boss",
            "timing": "It's not the right time",
            "need": "We already have something for this",
            "trust": "We have been burned before",
            "competitor": "Gong does this already",
        }
        for expected_class, text in cases.items():
            with self.subTest(cls=expected_class):
                self.assertEqual(_detect_objection_class(text), expected_class)


class TestTruncateWords(unittest.TestCase):
    """_truncate_words helper."""

    def test_under_limit(self):
        self.assertEqual(_truncate_words("one two three", 5), "one two three")

    def test_at_limit(self):
        self.assertEqual(_truncate_words("a b c d e", 5), "a b c d e")

    def test_over_limit(self):
        self.assertEqual(_truncate_words("a b c d e f g", 5), "a b c d e")


class TestApplyToolResult(unittest.TestCase):
    """apply_tool_result updates HUD state correctly."""

    def test_battle_card_sets_active(self):
        mgr = HudStateManager()
        mgr.apply_tool_result("load_battle_card", {"competitor": "Gong"})
        snap = mgr.snapshot()
        self.assertEqual(snap["active_battle_card"], "Gong")

    def test_battle_card_pushes_signal(self):
        mgr = HudStateManager()
        mgr.apply_tool_result("load_battle_card", {"competitor": "Clari"})
        snap = mgr.snapshot()
        self.assertTrue(len(snap["active_signals"]) > 0)

    def test_buyer_profile_pushes_style_signal(self):
        mgr = HudStateManager()
        mgr.apply_tool_result("lookup_buyer_profile", {"communication_style": "Analytical, prefers proof."})
        snap = mgr.snapshot()
        signal_texts = [s["text"] for s in snap["active_signals"]]
        self.assertTrue(any("Buyer" in t for t in signal_texts))

    def test_non_dict_result_is_ignored(self):
        mgr = HudStateManager()
        mgr.apply_tool_result("some_tool", "string result")
        snap = mgr.snapshot()
        self.assertEqual(len(snap["active_signals"]), 0)

    def test_signals_capped_at_8(self):
        mgr = HudStateManager()
        for i in range(10):
            mgr.apply_tool_result("load_battle_card", {"competitor": f"Competitor{i}"})
        snap = mgr.snapshot()
        self.assertLessEqual(len(snap["active_signals"]), 8)


if __name__ == "__main__":
    unittest.main()
