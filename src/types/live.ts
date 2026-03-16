export type VisualSource = 'camera' | 'screen' | 'none'

export type LiveSessionStatus = 'idle' | 'connecting' | 'live' | 'ending' | 'ended' | 'error'
export type LiveRuntimeMode = 'unknown' | 'vertex' | 'mock'

export type BuyerContext = {
  name: string
  email: string
  company: string
  title: string
  goal: string
  anchor: string
  floor: string
  watch_for: string
  edge: string
}

export type HudSignal = {
  icon: string
  text: string
  urgency: 'low' | 'medium' | 'high'
}

export type BantTracker = {
  level: number
  label: string
}

export type TalkRatioState = {
  salesperson_pct: number
  buyer_pct: number
  status: 'ok' | 'warning' | 'danger'
  target_pct: number
}

export type DealHudState = {
  deal_temperature: number
  deal_temp_direction: 'rising' | 'falling' | 'stable'
  deal_temp_reason: string
  sentiment: string
  negotiation_stage: string
  time_elapsed_seconds: number
  talk_ratio: TalkRatioState
  bant: {
    budget: BantTracker
    authority: BantTracker
    need: BantTracker
    timeline: BantTracker
  }
  active_signals: HudSignal[]
  buyer_commitments: string[]
  buying_signals_count: {
    tier1: number
    tier2: number
    close_window_open: boolean
  }
  active_battle_card: string | null
  strategy_card: {
    goal: string
    anchor: string
    floor: string
    watch_for: string
    edge: string
  }
  concessions_made: number
  last_concession_got_return: boolean
}

export type WhisperPayload = {
  whisper_type: 'MOVE' | 'HOLD' | 'WARN' | 'REFRAME' | 'CLOSE' | 'BATTLE' | 'ANCHOR'
  urgency: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  audio_text: string
  hud_text: string
  hud_color: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
  display_duration_seconds: number
  confidence: number
  trigger: string
  suggested_exact_words: string | null
  suppress_if_speaking: boolean
}

export type WhisperHistoryItem = WhisperPayload & {
  id: string
  received_at: number
  received_at_label: string
}

export type TranscriptEntry = {
  id: string
  direction: 'input' | 'output' | 'note' | 'system'
  speaker_label: string
  text: string
  received_at: number
  received_at_label: string
}

export type ConnectionStats = {
  audio_chunks_sent: number
  video_frames_sent: number
  notes_sent: number
  backend_ws_base: string
  call_id: string
  visual_source: VisualSource
  runtime_mode: LiveRuntimeMode
}

export type LiveSessionSummary = {
  artifact_id?: string
  buyer_context: BuyerContext
  started_at: number
  ended_at: number
  saved_at?: string
  status?: string
  duration_seconds: number
  whisper_history: WhisperHistoryItem[]
  transcript_feed: TranscriptEntry[]
  final_hud_state: DealHudState
  connection_stats: ConnectionStats
}

export type SavedSessionListItem = {
  artifact_id: string
  call_id: string
  buyer_name: string
  company: string
  started_at: number
  ended_at: number
  duration_seconds: number
  status: string
  runtime_mode: LiveRuntimeMode
  visual_source: VisualSource | 'none'
  deal_temperature: number
  negotiation_stage: string
  sentiment: string
}

export const defaultHudState: DealHudState = {
  deal_temperature: 50,
  deal_temp_direction: 'stable',
  deal_temp_reason: 'Awaiting live signal confluence.',
  sentiment: 'Neutral',
  negotiation_stage: 'Opening',
  time_elapsed_seconds: 0,
  talk_ratio: {
    salesperson_pct: 0,
    buyer_pct: 0,
    status: 'ok',
    target_pct: 40,
  },
  bant: {
    budget: { level: 0, label: 'Unknown' },
    authority: { level: 0, label: 'Unknown' },
    need: { level: 0, label: 'Latent' },
    timeline: { level: 0, label: 'Absent' },
  },
  active_signals: [],
  buyer_commitments: [],
  buying_signals_count: {
    tier1: 0,
    tier2: 0,
    close_window_open: false,
  },
  active_battle_card: null,
  strategy_card: {
    goal: 'Confirm pain, authority, and next step.',
    anchor: 'TBD',
    floor: 'TBD',
    watch_for: 'Hidden objection masked as process.',
    edge: 'Faster path to measurable ROI.',
  },
  concessions_made: 0,
  last_concession_got_return: true,
}
