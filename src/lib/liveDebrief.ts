import type { LiveSessionSummary } from '../types/live'

type OutputCardModel = {
  title: string
  body: string
  footer: string
}

type DebriefMetric = {
  label: string
  value: string
  note: string
}

type DebriefItem = {
  label: string
  value: string
}

export type DerivedLiveDebrief = {
  date: string
  duration: string
  outcome: string
  dealTempShift: string
  probabilityShift: string
  lesson: string
  outputs: OutputCardModel[]
  keyMoments: string[]
  whatWorked: string[]
  whatCostYou: string[]
  missedOpportunities: string[]
  coachingMetrics: DebriefMetric[]
  behavioralMemory: DebriefItem[]
  companyIntelligence: DebriefItem[]
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  return `${minutes}m ${remaining.toString().padStart(2, '0')}s`
}

function clampProbability(temperature: number) {
  return Math.max(10, Math.min(95, Math.round(temperature * 0.78)))
}

function pickBuyerCommitments(summary: LiveSessionSummary) {
  const candidateLines = summary.transcript_feed
    .filter((entry) => entry.direction === 'input')
    .map((entry) => entry.text)
    .filter((text) => /will|next|send|review|pilot|term|follow-up|security|budget|scope/i.test(text))

  return candidateLines.slice(-3)
}

function buildFollowUp(summary: LiveSessionSummary, commitments: string[]) {
  const commitmentLine =
    commitments[0] ??
    `the priorities you raised around ${summary.final_hud_state.negotiation_stage.toLowerCase()} and rollout risk`

  return {
    title: 'Follow-up email',
    body: `${summary.buyer_context.name}, thanks again for the conversation today. You highlighted ${commitmentLine}, so I will send the next-step materials that keep the process moving without adding friction. If it still makes sense after that review, we can lock the next decision meeting and confirm the right scope.`,
    footer: 'Generated from the live transcript and final HUD state.',
  }
}

function buildCrmUpdate(summary: LiveSessionSummary, probability: number) {
  const tier1Signals = summary.final_hud_state.buying_signals_count.tier1
  return {
    title: 'CRM update',
    body: `Stage: ${summary.final_hud_state.negotiation_stage}. Probability: ${probability}%. Deal temperature closed at ${summary.final_hud_state.deal_temperature}. Strong buying signals captured: ${tier1Signals}. Active battle card: ${summary.final_hud_state.active_battle_card ?? 'None loaded'}.`,
    footer: 'Review before writing back to Salesforce or HubSpot.',
  }
}

function buildInternalSummary(summary: LiveSessionSummary) {
  const latestWhisper = summary.whisper_history[0]?.audio_text ?? 'No whisper was delivered.'
  const signalCount = summary.final_hud_state.active_signals.length
  return {
    title: 'Internal summary',
    body: `The call finished in ${summary.final_hud_state.negotiation_stage} with ${signalCount} active signals on the HUD. The final live coaching move was "${latestWhisper}". The rep sent ${summary.connection_stats.notes_sent} notes into the model and kept the session running for ${formatDuration(summary.duration_seconds)}.`,
    footer: 'Use this as the manager-ready top line.',
  }
}

export function deriveLiveDebrief(summary: LiveSessionSummary): DerivedLiveDebrief {
  const closedProbability = clampProbability(summary.final_hud_state.deal_temperature)
  const commitments = pickBuyerCommitments(summary)
  const startedAt = new Date(summary.started_at)

  const latestWhispers = summary.whisper_history.slice(0, 4).map((item) => `${item.received_at_label} - ${item.audio_text}`)
  const latestTranscriptMoments = summary.transcript_feed
    .slice(-4)
    .map((item) => `${item.received_at_label} - ${item.speaker_label}: ${item.text}`)

  const talkRatio = summary.final_hud_state.talk_ratio
  const talkRatioNote =
    talkRatio.salesperson_pct > talkRatio.target_pct
      ? 'Seller talked above target in the final state.'
      : 'Seller stayed at or below the target talk ratio.'

  return {
    date: startedAt.toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
    duration: formatDuration(summary.duration_seconds),
    outcome: summary.final_hud_state.buying_signals_count.close_window_open
      ? `Close window opened with the deal ending ${summary.final_hud_state.sentiment.toLowerCase()}.`
      : `Call ended in ${summary.final_hud_state.negotiation_stage.toLowerCase()} without an explicit close window.`,
    dealTempShift: `Closed at ${summary.final_hud_state.deal_temperature} with direction ${summary.final_hud_state.deal_temp_direction}. ${summary.final_hud_state.deal_temp_reason}`,
    probabilityShift: `Live estimate now ${closedProbability}% based on HUD temperature, active buying signals, and final stage.`,
    lesson:
      summary.final_hud_state.talk_ratio.salesperson_pct > summary.final_hud_state.talk_ratio.target_pct
        ? 'The next improvement is reducing seller airtime once the objection or close window appears.'
        : 'The strongest behavior to preserve is letting the buyer’s own language carry the decision point.',
    outputs: [buildFollowUp(summary, commitments), buildCrmUpdate(summary, closedProbability), buildInternalSummary(summary)],
    keyMoments: latestWhispers.length > 0 ? latestWhispers : latestTranscriptMoments,
    whatWorked: [
      `Final sentiment landed ${summary.final_hud_state.sentiment.toLowerCase()} with ${summary.final_hud_state.buying_signals_count.tier1} Tier 1 buying signals detected.`,
      `Visual source used: ${summary.connection_stats.visual_source}. Video frames sent: ${summary.connection_stats.video_frames_sent}.`,
      `Runtime mode: ${summary.connection_stats.runtime_mode}.`,
      `DealWhisper delivered ${summary.whisper_history.length} whispers across ${formatDuration(summary.duration_seconds)}.`,
    ],
    whatCostYou: [
      talkRatioNote,
      summary.final_hud_state.buying_signals_count.close_window_open
        ? 'A close window appeared. Review whether the rep converted it fast enough.'
        : 'No close window opened. Review where the conversation stalled before commitment.',
    ],
    missedOpportunities: [
      summary.final_hud_state.active_battle_card
        ? `A competitor card for ${summary.final_hud_state.active_battle_card} was active. Confirm the rep won on buyer criteria instead of reacting on price.`
        : 'No competitor card was loaded. If a rival surfaced verbally, capture it in the next run.',
      commitments.length > 0
        ? `Buyer commitment extraction is heuristic right now. Confirm these manually: ${commitments.join(' | ')}`
        : 'No clear commitment line was auto-detected from the buyer transcript. Check the raw transcript before sending follow-up.',
    ],
    coachingMetrics: [
      {
        label: 'Talk ratio',
        value: `${talkRatio.salesperson_pct} / ${talkRatio.buyer_pct}`,
        note: `Target seller share: ${talkRatio.target_pct}%.`,
      },
      {
        label: 'Whispers delivered',
        value: String(summary.whisper_history.length),
        note: 'Counted from live whisper payloads received by the frontend.',
      },
      {
        label: 'Audio stream',
        value: String(summary.connection_stats.audio_chunks_sent),
        note: 'Microphone PCM chunks sent to the backend.',
      },
      {
        label: 'Video frames',
        value: String(summary.connection_stats.video_frames_sent),
        note: 'JPEG frames streamed to the backend.',
      },
      {
        label: 'Tier 1 signals',
        value: String(summary.final_hud_state.buying_signals_count.tier1),
        note: 'Captured from the final live HUD snapshot.',
      },
      {
        label: 'Final probability',
        value: `${closedProbability}%`,
        note: 'Heuristic estimate derived from the final deal temperature.',
      },
      {
        label: 'Runtime mode',
        value: summary.connection_stats.runtime_mode,
        note: 'Vertex AI powers live coaching in production.',
      },
    ],
    behavioralMemory: [
      {
        label: 'Final stage',
        value: summary.final_hud_state.negotiation_stage,
      },
      {
        label: 'Risk watch',
        value: summary.final_hud_state.strategy_card.watch_for,
      },
      {
        label: 'Open commitments',
        value:
          summary.final_hud_state.buyer_commitments.length > 0
            ? summary.final_hud_state.buyer_commitments.join(' | ')
            : 'No explicit commitments were logged into HUD state.',
      },
      {
        label: 'Live concern pattern',
        value: summary.final_hud_state.active_signals.map((signal) => signal.text).join(' | ') || 'No persistent signals remained active.',
      },
    ],
    companyIntelligence: [
      {
        label: 'Visual telemetry',
        value: `${summary.connection_stats.visual_source} source with ${summary.connection_stats.video_frames_sent} frames captured.`,
      },
      {
        label: 'Manual notes',
        value: `${summary.connection_stats.notes_sent} seller note(s) were injected into the live model context.`,
      },
      {
        label: 'Runtime mode',
        value: summary.connection_stats.runtime_mode,
      },
      {
        label: 'Strongest close clue',
        value: summary.final_hud_state.buying_signals_count.close_window_open
          ? 'A close window did open during the session.'
          : 'No close window appeared in the final HUD state.',
      },
      {
        label: 'Anchor posture',
        value: `Anchor: ${summary.final_hud_state.strategy_card.anchor} | Floor: ${summary.final_hud_state.strategy_card.floor}`,
      },
    ],
  }
}
