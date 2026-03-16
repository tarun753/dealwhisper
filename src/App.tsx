import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { useDealWhisperSession, type DealWhisperSession } from './hooks/useDealWhisperSession'
import { useVoiceInput } from './hooks/useVoiceInput'
import { buildApiEndpoint, fetchJsonWithAuth } from './lib/backend'
import { deriveLiveDebrief } from './lib/liveDebrief'
import type {
  BuyerContext,
  LiveSessionSummary,
  SavedSessionListItem,
  TranscriptEntry,
  VisualSource,
  WhisperHistoryItem,
} from './types/live'

type PhaseId = 'pre' | 'live' | 'post'
type BriefingMessage = { role: 'user' | 'assistant'; content: string }

type PhaseOption = {
  id: PhaseId
  label: string
  kicker: string
}

const LIVE_PREFS_STORAGE_KEY = 'dealwhisper.livePrefs.v1'

type LivePrefs = {
  backendWsBase: string
  visualSource: VisualSource
  buyerContext: BuyerContext
}

const phases: PhaseOption[] = [
  { id: 'pre', label: 'Pre-Call Setup', kicker: 'Buyer context and strategy' },
  { id: 'live', label: 'Live Session', kicker: 'Real-time AI coaching' },
  { id: 'post', label: 'Post-Call Debrief', kicker: 'Review, follow-up, and insights' },
]

const defaultBuyerContext: BuyerContext = {
  name: '',
  email: '',
  company: '',
  title: '',
  goal: '',
  anchor: '',
  floor: '',
  watch_for: '',
  edge: '',
}

function inferBackendWsBase(): string {
  if (import.meta.env.VITE_DEALWHISPER_BACKEND_WS_BASE) return import.meta.env.VITE_DEALWHISPER_BACKEND_WS_BASE as string
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws/call`
  }
  return 'ws://127.0.0.1:8080/ws/call'
}
const defaultBackendWsBase = inferBackendWsBase()

function isVisualSource(value: string): value is VisualSource {
  return value === 'camera' || value === 'screen' || value === 'none'
}

function getDefaultLivePrefs(): LivePrefs {
  return {
    backendWsBase: defaultBackendWsBase,
    buyerContext: defaultBuyerContext,
    visualSource: 'camera',
  }
}

function persistLivePrefs(livePrefs: LivePrefs) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(LIVE_PREFS_STORAGE_KEY, JSON.stringify(livePrefs))
}

function loadLivePrefs(): LivePrefs {
  const defaultPrefs = getDefaultLivePrefs()
  if (typeof window === 'undefined') return defaultPrefs

  try {
    const raw = window.localStorage.getItem(LIVE_PREFS_STORAGE_KEY)
    if (!raw) return defaultPrefs

    const parsed = JSON.parse(raw) as {
      backendWsBase?: string
      buyerContext?: Partial<BuyerContext>
      visualSource?: VisualSource
    }

    return {
      backendWsBase: parsed.backendWsBase || defaultPrefs.backendWsBase,
      buyerContext: {
        ...defaultPrefs.buyerContext,
        ...(parsed.buyerContext ?? {}),
      },
      visualSource:
        typeof parsed.visualSource === 'string' && isVisualSource(parsed.visualSource)
          ? parsed.visualSource
          : defaultPrefs.visualSource,
    }
  } catch {
    return defaultPrefs
  }
}

function createCallId(name: string) {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
  return `${slug || 'deal'}-${Date.now()}`
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  return `${minutes}:${remaining.toString().padStart(2, '0')}`
}

function normalizeStageName(stage: string) {
  if (stage === 'Demo') return 'Presentation'
  if (stage === 'Bargaining') return 'Negotiation'
  if (stage === 'Objections') return 'Objection handling'
  if (stage === 'Post-Close') return 'Close'
  return stage
}

// ─── Main App ────────────────────────────────────────────────

function App() {
  const [phase, setPhase] = useState<PhaseId>('pre')
  const [briefingMessages, setBriefingMessages] = useState<BriefingMessage[]>([])
  const liveSession = useDealWhisperSession()

  const openSummaryInLiveCall = (summary: LiveSessionSummary) => {
    persistLivePrefs({
      backendWsBase: summary.connection_stats.backend_ws_base || defaultBackendWsBase,
      visualSource: isVisualSource(summary.connection_stats.visual_source) ? summary.connection_stats.visual_source : 'none',
      buyerContext: { ...defaultBuyerContext, ...summary.buyer_context },
    })
    setPhase('live')
  }

  return (
    <div className="shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="ambient" style={{position:'fixed',top:'30%',left:'40%',width:'30rem',height:'30rem',background:'radial-gradient(circle, rgba(160,131,255,0.1) 0%, transparent 55%)',filter:'blur(70px)',animation:'aurora-drift 30s ease-in-out infinite reverse'}} />

      <header className="app-header">
        <div className="brand-block">
          <div className="brand-mark" style={{transition:'box-shadow var(--transition-slow), border-color var(--transition-slow)',cursor:'default',borderColor:'var(--border-medium)'}}>DW</div>
          <div>
            <p className="eyebrow">DealWhisper</p>
            <h1 style={{background:'linear-gradient(135deg, var(--text-primary) 0%, var(--accent-gold) 50%, var(--accent-teal) 100%)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',backgroundClip:'text'}}>Real-time AI sales coaching</h1>
            <p style={{fontSize:'0.7rem',color:'var(--text-dim)',letterSpacing:'0.06em',marginTop:'0.15rem',animation:'fade-in 1.2s ease-out'}}>Powered by multimodal intelligence ✦ Live whisper engine</p>
          </div>
        </div>
        <div className="header-meta">
          {liveSession.status === 'live' ? (
            <>
              <StatChip label="Status" value="Live" live />
              <StatChip label="Elapsed" value={formatElapsed(liveSession.elapsedSeconds)} />
            </>
          ) : liveSession.status === 'connecting' ? (
            <div style={{display:'flex',alignItems:'center',gap:'0.5rem'}}>
              <div className="shimmer" style={{width:'5rem',height:'1.2rem',borderRadius:'var(--radius-sm)'}} />
              <div className="shimmer" style={{width:'3rem',height:'1.2rem',borderRadius:'var(--radius-sm)'}} />
            </div>
          ) : (
            <StatChip label="Status" value="Ready" />
          )}
        </div>
      </header>

      <main className="dashboard">
        <section className="phase-selector">
          {phases.map((option) => (
            <button
              className={`phase-button ${phase === option.id ? 'phase-button-active' : ''}`}
              key={option.id}
              onClick={() => setPhase(option.id)}
              type="button"
            >
              <span>{option.label}</span>
              <small>{option.kicker}</small>
            </button>
          ))}
        </section>

        {phase === 'pre' ? <PreCall onStartSession={() => setPhase('live')} briefingMessages={briefingMessages} setBriefingMessages={setBriefingMessages} /> : null}
        {phase === 'live' ? <LiveCall session={liveSession} briefingMessages={briefingMessages} /> : null}
        {phase === 'post' ? (
          <PostCall
            backendWsBase={liveSession.sessionMeta?.backendWsBase ?? defaultBackendWsBase}
            lastSummary={liveSession.lastSummary}
            onOpenInLiveCall={openSummaryInLiveCall}
            selectedArtifactId={liveSession.sessionMeta?.artifactId ?? null}
          />
        ) : null}
      </main>

      <footer className="app-footer">
        <div className="footer-inner">
          <p className="footer-brand">DealWhisper</p>
          <p className="footer-tagline">Powered by Gemini 2.5 and Vertex AI.</p>
        </div>
      </footer>
    </div>
  )
}

// ─── Phase 1: Pre-Call Setup ─────────────────────────────────

type PreCallInsight = { title: string; body: string }
function PreCall({ onStartSession, briefingMessages, setBriefingMessages }: { onStartSession: () => void; briefingMessages: BriefingMessage[]; setBriefingMessages: React.Dispatch<React.SetStateAction<BriefingMessage[]>> }) {
  const livePrefs = useMemo(() => loadLivePrefs(), [])
  const [buyerContext, setBuyerContext] = useState(livePrefs.buyerContext)
  const [insights, setInsights] = useState<PreCallInsight[]>([])
  const [researchStatus, setResearchStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [researchError, setResearchError] = useState<string | null>(null)
  const [briefingInput, setBriefingInput] = useState('')
  const [briefingLoading, setBriefingLoading] = useState(false)
  const [briefingStarted, setBriefingStarted] = useState(false)
  const briefingRef = useRef<HTMLDivElement | null>(null)

  const sendVoiceTranscript = useCallback((text: string) => {
    setBriefingInput(text)
    // Auto-send after a tick so React can render the text
    setTimeout(() => {
      const fakeInput = text
      if (!fakeInput.trim() || briefingLoading) return
      const userMsg: BriefingMessage = { role: 'user', content: fakeInput.trim() }
      const updatedMessages = [...briefingMessages, userMsg]
      setBriefingMessages(updatedMessages)
      setBriefingInput('')
      setBriefingLoading(true)
      setTimeout(() => { briefingRef.current?.scrollTo(0, briefingRef.current.scrollHeight) }, 50)
      const apiBase = livePrefs.backendWsBase.replace(/^ws/, 'http').replace(/\/ws\/call$/, '')
      void fetchJsonWithAuth<{ reply: string }>(
        buildApiEndpoint(apiBase, '/api/briefing'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ buyer_context: buyerContext, messages: updatedMessages }),
        },
      ).then((result) => {
        setBriefingMessages((prev) => [...prev, { role: 'assistant', content: result.reply }])
        setTimeout(() => { briefingRef.current?.scrollTo(0, briefingRef.current.scrollHeight) }, 100)
      }).catch(() => {
        setBriefingMessages((prev) => [...prev, { role: 'assistant', content: 'I didn\'t catch that — could you say more about the meeting?' }])
      }).finally(() => {
        setBriefingLoading(false)
      })
    }, 0)
  }, [briefingMessages, briefingLoading, buyerContext, livePrefs.backendWsBase, setBriefingMessages])

  const voiceInput = useVoiceInput(sendVoiceTranscript)

  const startBriefing = async () => {
    setBriefingStarted(true)
    setBriefingLoading(true)
    try {
      const apiBase = livePrefs.backendWsBase.replace(/^ws/, 'http').replace(/\/ws\/call$/, '')
      const result = await fetchJsonWithAuth<{ reply: string }>(
        buildApiEndpoint(apiBase, '/api/briefing'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ buyer_context: buyerContext, messages: [] }),
        },
      )
      setBriefingMessages([{ role: 'assistant', content: result.reply }])
    } catch {
      setBriefingMessages([{ role: 'assistant', content: 'Tell me about this upcoming meeting. What\'s the context and what are you trying to achieve?' }])
    }
    setBriefingLoading(false)
  }

  const sendBriefingMessage = async () => {
    if (!briefingInput.trim() || briefingLoading) return
    const userMsg: BriefingMessage = { role: 'user', content: briefingInput.trim() }
    const updatedMessages = [...briefingMessages, userMsg]
    setBriefingMessages(updatedMessages)
    setBriefingInput('')
    setBriefingLoading(true)
    setTimeout(() => { briefingRef.current?.scrollTo(0, briefingRef.current.scrollHeight) }, 50)

    try {
      const apiBase = livePrefs.backendWsBase.replace(/^ws/, 'http').replace(/\/ws\/call$/, '')
      const result = await fetchJsonWithAuth<{ reply: string }>(
        buildApiEndpoint(apiBase, '/api/briefing'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ buyer_context: buyerContext, messages: updatedMessages }),
        },
      )
      setBriefingMessages([...updatedMessages, { role: 'assistant', content: result.reply }])
    } catch {
      setBriefingMessages([...updatedMessages, { role: 'assistant', content: 'I understand. Tell me more — what else should I know before the call?' }])
    }
    setBriefingLoading(false)
    setTimeout(() => { briefingRef.current?.scrollTo(0, briefingRef.current.scrollHeight) }, 100)
  }

  const handleChange = (field: keyof BuyerContext, value: string) => {
    setBuyerContext((prev) => ({ ...prev, [field]: value }))
  }

  const handleResearch = async () => {
    if (!buyerContext.company.trim()) return
    setResearchStatus('loading')
    setResearchError(null)
    try {
      const apiBase = livePrefs.backendWsBase.replace(/^ws/, 'http').replace(/\/ws\/call$/, '')
      const result = await fetchJsonWithAuth<{ insights: PreCallInsight[] }>(
        buildApiEndpoint(apiBase, '/api/research'),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: buyerContext.name,
            email: buyerContext.email,
            company: buyerContext.company,
          }),
        },
      )
      setInsights(result.insights)
      setResearchStatus('ready')
    } catch (err) {
      setResearchError(err instanceof Error ? err.message : 'Research failed.')
      setResearchStatus('error')
    }
  }

  const handleStart = () => {
    persistLivePrefs({
      backendWsBase: livePrefs.backendWsBase,
      visualSource: livePrefs.visualSource,
      buyerContext,
    })
    onStartSession()
  }

  const isReady = buyerContext.name.trim() && buyerContext.company.trim()
  const canResearch = buyerContext.company.trim().length > 0

  return (
    <section className="phase-layout">
      <div className="main-column">
        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Buyer context</p>
              <h3>Who are you meeting with?</h3>
            </div>
            <div className="control-actions">
              <button
                className="action-button"
                style={canResearch && researchStatus !== 'loading' ? {background:'linear-gradient(135deg, var(--accent-gold) 0%, #ff8a3d 100%)',color:'#000',fontWeight:600} : undefined}
                disabled={!canResearch || researchStatus === 'loading'}
                onClick={() => void handleResearch()}
                type="button"
              >
                {researchStatus === 'loading' ? (
                  <span style={{display:'flex',alignItems:'center',gap:'0.4rem'}}>
                    <span className="shimmer" style={{width:'0.8rem',height:'0.8rem',borderRadius:'50%',display:'inline-block'}} />
                    Researching...
                  </span>
                ) : (
                  <span>◎ Research buyer</span>
                )}
              </button>
            </div>
          </div>

          <p className="section-description">
            Enter the buyer details before your call. DealWhisper uses this context to deliver
            real-time coaching whispers tailored to your specific deal.
          </p>

          <div className="field-grid">
            <label className="live-field">
              <span className="mini-label">Buyer name</span>
              <input onChange={(e) => handleChange('name', e.target.value)} type="text" value={buyerContext.name} placeholder="Maya Chen" />
            </label>

            <label className="live-field">
              <span className="mini-label">Company</span>
              <input onChange={(e) => handleChange('company', e.target.value)} type="text" value={buyerContext.company} placeholder="Northstar Health" />
            </label>

            <label className="live-field">
              <span className="mini-label">Title</span>
              <input onChange={(e) => handleChange('title', e.target.value)} type="text" value={buyerContext.title} placeholder="VP of Operations" />
            </label>

            <label className="live-field">
              <span className="mini-label">Email</span>
              <input onChange={(e) => handleChange('email', e.target.value)} type="email" value={buyerContext.email} placeholder="maya@northstar.com" />
            </label>

            <label className="live-field live-field-wide">
              <span className="mini-label">Goal for this call</span>
              <textarea onChange={(e) => handleChange('goal', e.target.value)} rows={2} value={buyerContext.goal} placeholder="Close the renewal and expand into Q3 implementation" />
            </label>
          </div>
        </article>

        {/* Shimmer loading placeholders while research is in progress */}
        {researchStatus === 'loading' ? (
          <article className="surface">
            <div className="card-header">
              <div>
                <p className="eyebrow">Pre-call intelligence</p>
                <h3>Researching {buyerContext.company || 'buyer'}...</h3>
              </div>
              <span className="pill pill-soft" style={{animation:'pulse 1.5s ease-in-out infinite'}}>Loading</span>
            </div>
            <div className="brief-grid">
              {[1, 2, 3].map((i) => (
                <article className="insight-card" key={i} style={{borderTop:'2px solid var(--border-subtle)'}}>
                  <ShimmerBlock lines={3} />
                </article>
              ))}
            </div>
          </article>
        ) : null}

        {/* Pre-call intelligence — populated by Research Buyer */}
        {insights.length > 0 && researchStatus === 'ready' ? (
          <article className="surface" style={{animation:'fade-in 0.5s ease-out'}}>
            <div className="card-header">
              <div>
                <p className="eyebrow">Pre-call intelligence</p>
                <h3>AI-generated insights for {buyerContext.company || 'this buyer'}</h3>
              </div>
              <span className="pill" style={{background:'rgba(31,179,165,0.15)',color:'var(--accent-teal)'}}>✦ {insights.length} insights</span>
            </div>
            <div className="brief-grid">
              {insights.map((insight) => (
                <InsightCard key={insight.title} title={insight.title} body={insight.body} />
              ))}
            </div>
          </article>
        ) : researchError ? (
          <article className="surface">
            <div className="session-alert">{researchError}</div>
          </article>
        ) : null}

        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Negotiation strategy</p>
              <h3>Set your position before you go live</h3>
            </div>
          </div>

          <div className="field-grid">
            <label className="live-field">
              <span className="mini-label">Anchor (opening position)</span>
              <input onChange={(e) => handleChange('anchor', e.target.value)} type="text" value={buyerContext.anchor} placeholder="$420K / year" />
            </label>

            <label className="live-field">
              <span className="mini-label">Floor (walk-away point)</span>
              <input onChange={(e) => handleChange('floor', e.target.value)} type="text" value={buyerContext.floor} placeholder="$340K / year" />
            </label>

            <label className="live-field live-field-wide">
              <span className="mini-label">Watch for</span>
              <textarea onChange={(e) => handleChange('watch_for', e.target.value)} rows={2} value={buyerContext.watch_for} placeholder="Budget objection, timeline delays, competitor mentions" />
            </label>

            <label className="live-field live-field-wide">
              <span className="mini-label">Your edge</span>
              <textarea onChange={(e) => handleChange('edge', e.target.value)} rows={2} value={buyerContext.edge} placeholder="Only vendor with HIPAA-certified real-time pipeline" />
            </label>
          </div>
        </article>

        {/* Pre-call briefing chat */}
        <article className="surface" style={{borderTop: briefingStarted ? '2px solid var(--accent-purple)' : undefined}}>
          <div className="card-header">
            <div>
              <p className="eyebrow">Pre-call briefing</p>
              <h3>{briefingStarted ? 'Brief the AI on your meeting' : 'Prepare DealWhisper for your call'}</h3>
            </div>
            {!briefingStarted ? (
              <button
                className="action-button"
                onClick={() => void startBriefing()}
                disabled={!buyerContext.name.trim() || briefingLoading}
                type="button"
                style={{background:'linear-gradient(135deg, var(--accent-purple) 0%, #c08aff 100%)',color:'#000',fontWeight:600}}
              >
                ✦ Start briefing
              </button>
            ) : null}
          </div>

          {!briefingStarted ? (
            <p className="section-description">
              Chat with DealWhisper's AI before your call. It will ask smart questions about the deal,
              remember everything you share, and use that context to give you better live coaching whispers.
            </p>
          ) : (
            <>
              <div
                ref={briefingRef}
                style={{
                  maxHeight: '20rem',
                  overflow: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.6rem',
                  marginTop: '0.75rem',
                  paddingRight: '0.2rem',
                  scrollbarWidth: 'thin' as const,
                  scrollbarColor: 'rgba(255,255,255,0.08) transparent',
                }}
              >
                {briefingMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      padding: '0.7rem 0.9rem',
                      borderRadius: msg.role === 'user' ? 'var(--radius-md) var(--radius-md) 4px var(--radius-md)' : 'var(--radius-md) var(--radius-md) var(--radius-md) 4px',
                      background: msg.role === 'user'
                        ? 'linear-gradient(135deg, rgba(160,131,255,0.2), rgba(160,131,255,0.08))'
                        : 'var(--bg-inset)',
                      border: `1px solid ${msg.role === 'user' ? 'rgba(160,131,255,0.25)' : 'var(--border-subtle)'}`,
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem',
                      lineHeight: '1.55',
                      animation: 'fade-up 0.3s ease-out',
                    }}
                  >
                    {msg.role === 'assistant' ? (
                      <span style={{display:'inline-block',fontSize:'0.6rem',color:'var(--accent-purple)',textTransform:'uppercase',letterSpacing:'0.1em',marginBottom:'0.25rem'}}>DealWhisper AI</span>
                    ) : null}
                    <p style={{margin:0}}>{msg.content}</p>
                  </div>
                ))}
                {briefingLoading ? (
                  <div style={{alignSelf:'flex-start',display:'flex',gap:'0.3rem',padding:'0.7rem 0.9rem'}}>
                    <span className="shimmer" style={{width:'0.5rem',height:'0.5rem',borderRadius:'50%',display:'inline-block'}} />
                    <span className="shimmer" style={{width:'0.5rem',height:'0.5rem',borderRadius:'50%',display:'inline-block',animationDelay:'0.15s'}} />
                    <span className="shimmer" style={{width:'0.5rem',height:'0.5rem',borderRadius:'50%',display:'inline-block',animationDelay:'0.3s'}} />
                  </div>
                ) : null}
              </div>
              <div style={{display:'flex',gap:'0.5rem',marginTop:'0.75rem'}}>
                <input
                  type="text"
                  value={briefingInput}
                  onChange={(e) => setBriefingInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendBriefingMessage() } }}
                  placeholder={voiceInput.state === 'listening' ? 'Listening...' : 'Type or tap mic to speak...'}
                  disabled={briefingLoading || voiceInput.state === 'listening'}
                  style={{
                    flex: 1,
                    padding: '0.7rem 0.9rem',
                    border: `1px solid ${voiceInput.state === 'listening' ? 'rgba(255,95,95,0.5)' : 'rgba(160,131,255,0.2)'}`,
                    borderRadius: 'var(--radius-md)',
                    background: voiceInput.state === 'listening' ? 'rgba(255,95,95,0.05)' : 'rgba(255,255,255,0.03)',
                    color: 'var(--text-primary)',
                    fontSize: '0.88rem',
                    outline: 'none',
                    transition: 'border-color var(--transition-base), box-shadow var(--transition-base)',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(160,131,255,0.5)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(160,131,255,0.12)' }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(160,131,255,0.2)'; e.currentTarget.style.boxShadow = 'none' }}
                />
                {voiceInput.isSupported ? (
                  <button
                    className="action-button"
                    onClick={voiceInput.toggle}
                    disabled={briefingLoading}
                    type="button"
                    style={{
                      padding:'0.7rem 0.8rem',
                      background: voiceInput.state === 'listening' ? 'rgba(255,95,95,0.2)' : 'rgba(160,131,255,0.1)',
                      border: `1px solid ${voiceInput.state === 'listening' ? 'rgba(255,95,95,0.4)' : 'rgba(160,131,255,0.3)'}`,
                      color: voiceInput.state === 'listening' ? '#ff5f5f' : 'var(--accent-purple)',
                      fontWeight:600,
                      flexShrink:0,
                      fontSize:'1.1rem',
                      lineHeight:1,
                      animation: voiceInput.state === 'listening' ? 'pulse 1s ease-in-out infinite' : 'none',
                    }}
                    title={voiceInput.state === 'listening' ? 'Stop listening' : 'Speak your briefing'}
                  >
                    {voiceInput.state === 'listening' ? '◉' : '🎤'}
                  </button>
                ) : null}
                <button
                  className="action-button"
                  onClick={() => void sendBriefingMessage()}
                  disabled={!briefingInput.trim() || briefingLoading}
                  type="button"
                  style={{padding:'0.7rem 1rem',background:'linear-gradient(135deg, var(--accent-purple) 0%, #c08aff 100%)',color:'#000',fontWeight:600,flexShrink:0}}
                >
                  Send
                </button>
              </div>
              {briefingMessages.filter(m => m.role === 'user').length > 0 ? (
                <p style={{fontSize:'0.68rem',color:'var(--text-dim)',marginTop:'0.5rem',letterSpacing:'0.04em'}}>
                  ✦ {briefingMessages.filter(m => m.role === 'user').length} briefing notes captured — these will inform your live coaching session
                </p>
              ) : null}
            </>
          )}
        </article>

        <div className="control-actions" style={{justifyContent:'stretch'}}>
          <button
            className="action-button"
            disabled={!isReady}
            onClick={handleStart}
            type="button"
            style={{width:'100%',display:'flex',alignItems:'center',justifyContent:'center',gap:'0.5rem',background: isReady ? 'linear-gradient(135deg, var(--accent-teal) 0%, #17d4c1 100%)' : undefined, color: isReady ? '#000' : undefined, fontWeight: 600}}
          >
            Go to live session <span style={{fontSize:'1.1rem'}}>→</span>
          </button>
        </div>
        {!isReady ? (
          <p className="section-description">Enter at least a buyer name and company to continue.</p>
        ) : null}
      </div>

      <aside className="side-column">
        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">How it works</p>
              <h3>Three phases</h3>
            </div>
          </div>
          <ul className="stack-list">
            <li style={{display:'flex',gap:'0.75rem',alignItems:'flex-start'}}>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:'1.6rem',height:'1.6rem',borderRadius:'50%',background:'linear-gradient(135deg, var(--accent-gold) 0%, #ff8a3d 100%)',color:'#000',fontWeight:700,fontSize:'0.75rem',flexShrink:0}}>1</span>
              <div>
                <strong>Pre-call setup</strong>
                <p>Enter buyer context and hit "Research buyer" to generate AI intelligence. Set your negotiation strategy.</p>
              </div>
            </li>
            <li style={{display:'flex',gap:'0.75rem',alignItems:'flex-start'}}>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:'1.6rem',height:'1.6rem',borderRadius:'50%',background:'linear-gradient(135deg, var(--accent-teal) 0%, #17d4c1 100%)',color:'#000',fontWeight:700,fontSize:'0.75rem',flexShrink:0}}>2</span>
              <div>
                <strong>Live session</strong>
                <p>Connect your mic and camera. DealWhisper listens to the conversation and delivers real-time coaching whispers.</p>
              </div>
            </li>
            <li style={{display:'flex',gap:'0.75rem',alignItems:'flex-start'}}>
              <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:'1.6rem',height:'1.6rem',borderRadius:'50%',background:'linear-gradient(135deg, var(--accent-purple) 0%, #c08aff 100%)',color:'#000',fontWeight:700,fontSize:'0.75rem',flexShrink:0}}>3</span>
              <div>
                <strong>Post-call debrief</strong>
                <p>Review AI-generated follow-up emails, CRM updates, and coaching insights from the call.</p>
              </div>
            </li>
          </ul>
        </article>

        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">AI capabilities</p>
              <h3>What DealWhisper detects</h3>
            </div>
          </div>
          <ul className="stack-list">
            <li>
              <strong><span style={{color:'var(--accent-gold)',marginRight:'0.4rem'}}>⚡</span>Buying signals</strong>
              <p>Budget readiness, authority confirmation, timeline urgency, competitive mentions.</p>
            </li>
            <li>
              <strong><span style={{color:'var(--accent-red)',marginRight:'0.4rem'}}>◆</span>Objection patterns</strong>
              <p>Price resistance, timeline stalls, competitor pivots, scope creep.</p>
            </li>
            <li>
              <strong><span style={{color:'var(--accent-teal)',marginRight:'0.4rem'}}>◉</span>Coaching moments</strong>
              <p>Talk ratio alerts, close window detection, sentiment shifts, negotiation stage transitions.</p>
            </li>
          </ul>
        </article>
      </aside>
    </section>
  )
}

// ─── Phase 2: Live Call ──────────────────────────────────────

function LiveCall({ session, briefingMessages }: { session: DealWhisperSession; briefingMessages: BriefingMessage[] }) {
  const livePrefs = useMemo(() => loadLivePrefs(), [])
  const [backendWsBase, setBackendWsBase] = useState(livePrefs.backendWsBase)
  const [buyerContext, setBuyerContext] = useState(livePrefs.buyerContext)
  const [callId, setCallId] = useState(createCallId(livePrefs.buyerContext.name))
  const [visualSource] = useState<VisualSource>('screen')
  const [noteDraft, setNoteDraft] = useState('')
  const [overlayVisible, setOverlayVisible] = useState(true)
  const [overlayOpacity, setOverlayOpacity] = useState(0.85)
  const popoutRef = useRef<Window | null>(null)
  const stageLabel = normalizeStageName(session.hudState.negotiation_stage)

  const talkRatioStyle = {
    background: `linear-gradient(90deg, var(--accent-gold) 0%, var(--accent-gold) ${session.hudState.talk_ratio.salesperson_pct}%, rgba(255,255,255,0.12) ${session.hudState.talk_ratio.salesperson_pct}%, rgba(255,255,255,0.12) 100%)`,
  }

  const liveSignals = session.hudState.active_signals
  const isLive = session.status === 'live'
  const isBusy = session.status === 'connecting' || session.status === 'ending'
  const latestWhisper = session.latestWhisper

  const handleContextChange = (field: keyof BuyerContext, value: string) => {
    setBuyerContext((prev) => ({ ...prev, [field]: value }))
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    persistLivePrefs({ backendWsBase, buyerContext, visualSource })
  }, [backendWsBase, buyerContext, visualSource])

  const handleConnect = async () => {
    const resolvedCallId = callId.trim() || createCallId(buyerContext.name)
    setCallId(resolvedCallId)
    await session.connect({
      backendWsBase,
      buyerContext,
      callId: resolvedCallId,
      initialNotes: briefingMessages.filter(m => m.role === 'user').map(m => m.content),
      visualSource,
    })
  }


  const handleSendNote = async () => {
    if (!noteDraft.trim()) return
    await session.sendNote(noteDraft)
    setNoteDraft('')
  }

  // Pop-out whisper window — opens a minimal window the user can place off shared screen
  const openPopout = () => {
    if (popoutRef.current && !popoutRef.current.closed) {
      popoutRef.current.focus()
      return
    }
    const w = window.open('', 'dw-whisper', 'width=380,height=260,top=60,left=60,toolbar=no,menubar=no,scrollbars=no,resizable=yes')
    if (!w) return
    popoutRef.current = w
    w.document.title = 'DW Whisper'
    w.document.body.style.cssText = 'margin:0;padding:12px;background:#0a0a0f;color:#e0ddd8;font-family:system-ui,sans-serif;overflow:hidden;'
    w.document.body.innerHTML = '<div id="dw-root" style="display:flex;flex-direction:column;height:100%;gap:6px"><p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#8a877f">Live whisper</p><h3 id="dw-text" style="margin:0;font-size:15px;line-height:1.4;flex:1">Waiting...</h3><p id="dw-meta" style="margin:0;font-size:11px;color:#8a877f"></p></div>'
  }

  // Sync latest whisper into the pop-out window
  useEffect(() => {
    const w = popoutRef.current
    if (!w || w.closed) return
    const textEl = w.document.getElementById('dw-text')
    const metaEl = w.document.getElementById('dw-meta')
    if (textEl) textEl.textContent = latestWhisper?.audio_text ?? 'Waiting for coaching moment...'
    if (metaEl) metaEl.textContent = latestWhisper ? `${latestWhisper.whisper_type} / ${latestWhisper.urgency} / ${Math.round(latestWhisper.confidence * 100)}%` : ''
  }, [latestWhisper])

  // Clean up pop-out on unmount
  useEffect(() => {
    return () => {
      if (popoutRef.current && !popoutRef.current.closed) popoutRef.current.close()
    }
  }, [])

  const dealTempPct = Math.min(100, Math.max(0, session.hudState.deal_temperature))
  const dealTempColor = dealTempPct > 70 ? 'var(--accent-teal)' : dealTempPct > 40 ? 'var(--accent-yellow)' : 'var(--accent-red)'

  return (
    <section className="phase-layout">
      {/* Floating whisper overlay — visible during live sessions */}
      {isLive && overlayVisible ? (
        <WhisperOverlay
          latestWhisper={latestWhisper}
          dealTemp={session.hudState.deal_temperature}
          stage={stageLabel}
          opacity={overlayOpacity}
          onClose={() => setOverlayVisible(false)}
          onOpacityChange={setOverlayOpacity}
          onPopout={openPopout}
        />
      ) : null}
      <div className="main-column">
        {/* Connection controls — collapse when live */}
        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Session controls</p>
              <h3 style={{display:'flex',alignItems:'center',gap:'0.5rem'}}>
                {isLive ? (
                  <>
                    <span style={{display:'inline-block',width:'0.5rem',height:'0.5rem',borderRadius:'50%',background:'var(--accent-teal)',boxShadow:'0 0 8px var(--accent-teal-glow)',animation:'pulse 1.5s ease-in-out infinite'}} />
                    Live with {buyerContext.name || 'buyer'}
                  </>
                ) : 'Configure and connect'}
              </h3>
            </div>
            <div className="event-badges">
              <span className={`pill ${statusPillClass(session.status)}`}>{statusLabel(session.status)}</span>
              {isLive ? (
                <>
                  <button className="action-button action-button-secondary" onClick={openPopout} type="button">
                    Pop-out whisper
                  </button>
                  {!overlayVisible ? (
                    <button className="action-button action-button-secondary" onClick={() => setOverlayVisible(true)} type="button">
                      Show overlay
                    </button>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>

          {!isLive && !isBusy ? (
            <div className="live-control-grid">
              <div className="field-grid">
                <label className="live-field">
                  <span className="mini-label">Buyer name</span>
                  <input onChange={(e) => handleContextChange('name', e.target.value)} type="text" value={buyerContext.name} />
                </label>

                <label className="live-field">
                  <span className="mini-label">Company</span>
                  <input onChange={(e) => handleContextChange('company', e.target.value)} type="text" value={buyerContext.company} />
                </label>

                <label className="live-field live-field-wide">
                  <span className="mini-label">Goal</span>
                  <textarea onChange={(e) => handleContextChange('goal', e.target.value)} rows={2} value={buyerContext.goal} />
                </label>

                <label className="live-field live-field-wide">
                  <span className="mini-label">Backend endpoint</span>
                  <input onChange={(e) => setBackendWsBase(e.target.value)} type="text" value={backendWsBase} />
                </label>
              </div>

              <div className="preview-stack">
                <MediaPreview
                  detail="Will share your screen + microphone with the AI coach."
                  stream={session.previewStream}
                  title="Visual preview"
                />
              </div>
            </div>
          ) : null}

          <div className="control-actions">
            <button
              className="action-button"
              disabled={isBusy || isLive}
              onClick={() => void handleConnect()}
              type="button"
              style={!isBusy && !isLive ? {display:'flex',alignItems:'center',gap:'0.5rem'} : undefined}
            >
              {session.status === 'connecting' ? (
                <span style={{display:'flex',alignItems:'center',gap:'0.4rem'}}>
                  <span style={{display:'inline-block',width:'0.5rem',height:'0.5rem',borderRadius:'50%',background:'var(--accent-gold)',animation:'pulse 1s ease-in-out infinite'}} />
                  Connecting...
                </span>
              ) : (
                <><span style={{color:'var(--accent-red)'}}>●</span> Start session (mic + screen)</>
              )}
            </button>
            <button className="action-button action-button-secondary" disabled={!isLive && !isBusy} onClick={() => void session.disconnect()} type="button">
              End session
            </button>
            <button className="action-button action-button-secondary" onClick={() => void session.clearSession()} type="button">
              Reset
            </button>
          </div>

          {session.status === 'connecting' ? (
            <div className="session-note connecting-pulse" style={{display:'flex',flexDirection:'column',gap:'0.5rem'}}>
              <span>Connecting to backend and initializing AI coaching session...</span>
              <div style={{display:'flex',gap:'0.5rem'}}>
                <div className="shimmer" style={{flex:1,height:'0.25rem',borderRadius:'2px'}} />
                <div className="shimmer" style={{flex:0.6,height:'0.25rem',borderRadius:'2px',animationDelay:'0.2s'}} />
              </div>
            </div>
          ) : null}

          {session.error ? (
            <div className="session-alert">
              <p>{session.error}</p>
              {session.status === 'error' ? (
                <div className="control-actions" style={{ marginTop: '0.6rem' }}>
                  <button className="action-button action-button-secondary" onClick={() => void session.clearSession()} type="button">
                    Reset session
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </article>

        {/* Live HUD — always visible */}
        <article className="surface live-surface">
          <div className="hud-top">
            <div className="hud-metric">
              <span>Deal temp</span>
              <div className="deal-temp-gauge" style={{position:'relative',width:'100%',height:'0.35rem',borderRadius:'2px',background:'var(--bg-inset)',overflow:'hidden',marginTop:'0.3rem',marginBottom:'0.15rem'}}>
                <div style={{position:'absolute',top:0,left:0,height:'100%',width:`${dealTempPct}%`,background:`linear-gradient(90deg, ${dealTempColor}, ${dealTempColor})`,borderRadius:'2px',transition:'width 0.6s ease-out'}} />
              </div>
              <strong style={{fontFamily:'var(--font-mono)',fontSize:'1.2rem',color: dealTempColor}}>{session.hudState.deal_temperature}°</strong>
              <small>{session.hudState.deal_temp_direction}</small>
            </div>
            <HudMetric label="Sentiment" value={session.hudState.sentiment} detail={stageLabel} />
            <div className="hud-metric">
              <span>Elapsed</span>
              <strong style={{fontFamily:'var(--font-mono)',fontSize:'1.2rem',letterSpacing:'0.05em'}}>{formatElapsed(session.elapsedSeconds)}</strong>
              <small>{session.status}</small>
            </div>
            <HudMetric
              label="Whispers"
              value={String(session.whisperHistory.length)}
              detail={session.hudState.buying_signals_count.close_window_open ? 'Close window open' : 'Monitoring signals'}
            />
          </div>

          <div
            className={`live-focus live-focus-${latestWhisper?.hud_color ?? 'blue'}`}
            style={{borderLeft: `3px solid ${latestWhisper?.hud_color === 'red' ? 'var(--accent-red)' : latestWhisper?.hud_color === 'green' ? 'var(--accent-teal)' : latestWhisper?.hud_color === 'yellow' ? 'var(--accent-yellow)' : 'var(--accent-blue)'}`,boxShadow: latestWhisper ? `inset 4px 0 20px -8px ${latestWhisper.hud_color === 'red' ? 'rgba(255,123,123,0.2)' : latestWhisper.hud_color === 'green' ? 'rgba(31,179,165,0.2)' : latestWhisper.hud_color === 'yellow' ? 'rgba(255,212,107,0.2)' : 'rgba(94,162,255,0.2)'}` : undefined}}
          >
            <div>
              <p className="eyebrow">Live coaching whisper</p>
              <h3>{latestWhisper?.audio_text ?? 'Waiting for the first coaching moment...'}</h3>
              <p>
                {latestWhisper
                  ? `${latestWhisper.whisper_type} / ${latestWhisper.urgency} / confidence ${Math.round(latestWhisper.confidence * 100)}%`
                  : session.hudState.deal_temp_reason}
              </p>
            </div>
            <div className="event-badges">
              <span className="pill pill-live">HUD {latestWhisper?.hud_text ?? 'STANDBY'}</span>
              <span className="pill">{session.hudState.negotiation_stage}</span>
              {session.hudState.active_battle_card ? <span className="pill">{session.hudState.active_battle_card}</span> : null}
            </div>
          </div>

          <div className="live-session-grid">
            <div className="surface surface-nested">
              <div className="card-header">
                <div>
                  <p className="eyebrow">Transcript</p>
                  <h4>Live conversation feed</h4>
                </div>
              </div>
              <TranscriptFeed entries={session.transcriptFeed} />
            </div>

            <div className="surface surface-nested">
              <div className="card-header">
                <div>
                  <p className="eyebrow">Whisper history</p>
                  <h4>AI coaching moves this session</h4>
                </div>
              </div>
              <WhisperHistory items={session.whisperHistory} />
            </div>
          </div>

          {isLive ? (
            <div className="note-composer">
              <label className="live-field live-field-wide">
                <span className="mini-label">Send a note to the AI</span>
                <textarea
                  onChange={(e) => setNoteDraft(e.target.value)}
                  placeholder="Example: Buyer just opened CRM and is looking at Q2 forecast."
                  rows={2}
                  value={noteDraft}
                />
              </label>
              <button className="action-button" disabled={!noteDraft.trim()} onClick={() => void handleSendNote()} type="button">
                Send note
              </button>
            </div>
          ) : null}
        </article>

        {/* Signals — only show when there are active signals */}
        {liveSignals.length > 0 ? (
          <article className="surface">
            <div className="card-header">
              <div>
                <p className="eyebrow">Active signals</p>
                <h3>Buying signals and engagement cues</h3>
              </div>
            </div>
            <div className="signal-grid">
              {liveSignals.map((signal, index) => (
                <div className="signal-card" key={`${signal.icon}-${signal.text}-${index}`}>
                  <span className="mini-label">{signal.icon} / {signal.urgency}</span>
                  <h4>{signal.text}</h4>
                  <p>{session.hudState.deal_temp_reason}</p>
                </div>
              ))}
            </div>
          </article>
        ) : null}
      </div>

      <aside className="side-column">
        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">BANT tracker</p>
              <h3>Confidence by pillar</h3>
            </div>
          </div>
          <div className="bant-grid" style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'0.75rem'}}>
            {[
              { label: 'Budget', value: session.hudState.bant.budget, color: 'var(--accent-gold)' },
              { label: 'Authority', value: session.hudState.bant.authority, color: 'var(--accent-blue)' },
              { label: 'Need', value: session.hudState.bant.need, color: 'var(--accent-teal)' },
              { label: 'Timeline', value: session.hudState.bant.timeline, color: 'var(--accent-purple)' },
            ].map((item) => (
              <div key={item.label} style={{background:'var(--bg-inset)',borderRadius:'var(--radius-sm)',padding:'0.75rem',borderTop:`2px solid ${item.color}`}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:'0.4rem'}}>
                  <strong style={{fontSize:'0.75rem',color:'var(--text-primary)'}}>{item.label}</strong>
                  <span style={{fontSize:'0.65rem',color:'var(--text-secondary)',fontFamily:'var(--font-mono)'}}>{item.value.level}%</span>
                </div>
                <div style={{width:'100%',height:'0.25rem',borderRadius:'2px',background:'rgba(255,255,255,0.06)',overflow:'hidden'}}>
                  <div style={{height:'100%',width:`${item.value.level}%`,background:item.color,borderRadius:'2px',transition:'width 0.5s ease-out'}} />
                </div>
                <span style={{fontSize:'0.6rem',color:'var(--text-dim)',marginTop:'0.25rem',display:'block'}}>{item.value.label}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Talk ratio</p>
              <h3>Stay under the noise threshold</h3>
            </div>
          </div>
          <div className="talk-ratio">
            <div className="talk-bar" style={talkRatioStyle} />
            <div className="talk-copy">
              <span>You {session.hudState.talk_ratio.salesperson_pct}%</span>
              <span>Buyer {session.hudState.talk_ratio.buyer_pct}%</span>
            </div>
            <p>Target: {session.hudState.talk_ratio.target_pct}%. Status: {session.hudState.talk_ratio.status}.</p>
          </div>
        </article>

        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Strategy</p>
              <h3>Your position</h3>
            </div>
          </div>
          <ul className="stack-list">
            <li>
              <strong>Goal</strong>
              <p>{session.hudState.strategy_card.goal || 'Not set'}</p>
            </li>
            <li>
              <strong>Anchor / Floor</strong>
              <p>{session.hudState.strategy_card.anchor || '—'} / {session.hudState.strategy_card.floor || '—'}</p>
            </li>
            <li>
              <strong>Watch for</strong>
              <p>{session.hudState.strategy_card.watch_for || 'Not set'}</p>
            </li>
            <li>
              <strong>Your edge</strong>
              <p>{session.hudState.strategy_card.edge || 'Not set'}</p>
            </li>
          </ul>
        </article>

        {isLive ? (
          <article className="surface side-card">
            <div className="card-header">
              <div>
                <p className="eyebrow">Connection</p>
                <h3>Session stats</h3>
              </div>
            </div>
            <div className="metrics-inline">
              <StatChip label="Audio" value={String(session.connectionStats?.audio_chunks_sent ?? 0)} />
              <StatChip label="Video" value={String(session.connectionStats?.video_frames_sent ?? 0)} />
              <StatChip label="Notes" value={String(session.connectionStats?.notes_sent ?? 0)} />
              <StatChip label="Runtime" value={session.runtimeMode} />
            </div>
          </article>
        ) : null}
      </aside>
    </section>
  )
}

// ─── Phase 3: Post-Call Debrief ──────────────────────────────

function PostCall({
  backendWsBase,
  lastSummary,
  onOpenInLiveCall,
  selectedArtifactId,
}: {
  backendWsBase: string
  lastSummary: LiveSessionSummary | null
  onOpenInLiveCall: (summary: LiveSessionSummary) => void
  selectedArtifactId: string | null
}) {
  const [savedSessions, setSavedSessions] = useState<SavedSessionListItem[]>([])
  const [selectedSummary, setSelectedSummary] = useState<LiveSessionSummary | null>(null)
  const [libraryError, setLibraryError] = useState<string | null>(null)
  const [libraryVersion, setLibraryVersion] = useState(0)

  useEffect(() => {
    let isCancelled = false
    const loadSessions = async () => {
      try {
        setLibraryError(null)
        const response = await fetchJsonWithAuth<{ sessions: SavedSessionListItem[] }>(
          buildApiEndpoint(backendWsBase, '/api/sessions?limit=8'),
        )
        if (!isCancelled) setSavedSessions(response.sessions)
      } catch (error) {
        if (!isCancelled) {
          setLibraryError(error instanceof Error ? error.message : 'Unable to load saved sessions.')
        }
      }
    }
    void loadSessions()
    return () => { isCancelled = true }
  }, [backendWsBase, libraryVersion, selectedArtifactId])

  useEffect(() => {
    let isCancelled = false
    if (selectedArtifactId && selectedArtifactId !== lastSummary?.artifact_id) {
      const load = async () => {
        try {
          const summary = await fetchJsonWithAuth<LiveSessionSummary>(buildApiEndpoint(backendWsBase, `/api/sessions/${selectedArtifactId}`))
          if (!isCancelled) setSelectedSummary(summary)
        } catch {
          if (!isCancelled) setSelectedSummary(null)
        }
      }
      void load()
    }
    return () => { isCancelled = true }
  }, [backendWsBase, lastSummary?.artifact_id, selectedArtifactId])

  useEffect(() => {
    let isCancelled = false
    if (!lastSummary && !selectedSummary && savedSessions.length > 0) {
      const load = async () => {
        try {
          const summary = await fetchJsonWithAuth<LiveSessionSummary>(buildApiEndpoint(backendWsBase, `/api/sessions/${savedSessions[0].artifact_id}`))
          if (!isCancelled) setSelectedSummary(summary)
        } catch { /* ignore */ }
      }
      void load()
    }
    return () => { isCancelled = true }
  }, [backendWsBase, lastSummary, savedSessions, selectedSummary])

  const activeSummary = selectedSummary ?? lastSummary

  if (!activeSummary) {
    return (
      <section className="phase-layout">
        <div className="main-column">
          <article className="surface">
            <div className="card-header">
              <div>
                <p className="eyebrow">Post-call debrief</p>
                <h3>No sessions yet</h3>
              </div>
            </div>
            <p className="section-description">
              Complete a live session to see your AI-generated debrief here. DealWhisper produces
              a follow-up email, CRM update, coaching metrics, and behavioral insights from every call.
            </p>
          </article>
        </div>
      </section>
    )
  }

  const liveDebrief = deriveLiveDebrief(activeSummary)

  const loadSavedSession = async (artifactId: string) => {
    try {
      setLibraryError(null)
      const summary = activeSummary.artifact_id === artifactId
        ? activeSummary
        : await fetchJsonWithAuth<LiveSessionSummary>(buildApiEndpoint(backendWsBase, `/api/sessions/${artifactId}`))
      setSelectedSummary(summary)
    } catch (error) {
      setLibraryError(error instanceof Error ? error.message : 'Unable to open saved session.')
    }
  }

  const downloadActiveSummary = () => {
    const blob = new Blob([JSON.stringify(activeSummary, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${activeSummary.artifact_id ?? activeSummary.connection_stats.call_id}-summary.json`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <section className="phase-layout">
      <div className="main-column">
        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Immediate outputs</p>
              <h3>Generated from your session</h3>
            </div>
            <div className="event-badges">
              <span className="pill pill-live">Review before sending</span>
              <button className="action-button action-button-secondary" onClick={() => onOpenInLiveCall(activeSummary)} type="button">
                New session with this buyer
              </button>
              <button className="action-button action-button-secondary" onClick={downloadActiveSummary} type="button">
                Download JSON
              </button>
            </div>
          </div>

          <div className="output-grid">
            {liveDebrief.outputs.map((output, idx) => (
              <OutputCard body={output.body} footer={output.footer} key={output.title} title={output.title} icon={outputIcon(idx)} />
            ))}
          </div>
        </article>

        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Call debrief</p>
              <h3>{activeSummary.buyer_context.name} - {liveDebrief.date} - {liveDebrief.duration}</h3>
            </div>
            {activeSummary.artifact_id ? <span className="pill">Artifact {activeSummary.artifact_id}</span> : null}
          </div>

          <div className="debrief-summary">
            <InsightCard title="Outcome" body={liveDebrief.outcome} />
            <ScoreRingCard title="Deal temp" value={liveDebrief.dealTempShift} />
            <ScoreRingCard title="Probability" value={liveDebrief.probabilityShift} />
            <InsightCard title="Biggest lesson" body={liveDebrief.lesson} />
          </div>

          <div className="debrief-columns">
            <DebriefList items={liveDebrief.keyMoments} title="Key moments" />
            <DebriefList items={liveDebrief.whatWorked} title="What worked" />
            <DebriefList items={liveDebrief.whatCostYou} title="What cost you" />
            <DebriefList items={liveDebrief.missedOpportunities} title="Missed opportunities" />
          </div>
        </article>

        <article className="surface">
          <div className="card-header">
            <div>
              <p className="eyebrow">Coaching metrics</p>
              <h3>Performance from this session</h3>
            </div>
          </div>
          <div className="metrics-board">
            {liveDebrief.coachingMetrics.map((metric) => (
              <div className="metric-card metric-card-wide" key={metric.label}>
                <span>{metric.label}</span>
                <strong style={{fontFamily:'var(--font-mono)'}}>{metric.value}</strong>
                <p>{metric.note}</p>
              </div>
            ))}
          </div>
        </article>
      </div>

      <aside className="side-column">
        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Past sessions</p>
              <h3>Saved debriefs</h3>
            </div>
            <button className="action-button action-button-secondary" onClick={() => setLibraryVersion((v) => v + 1)} type="button">
              Refresh
            </button>
          </div>

          {savedSessions.length > 0 ? (
            <div className="artifact-list">
              {savedSessions.map((item) => (
                <article
                  className={`artifact-card ${activeSummary.artifact_id === item.artifact_id ? 'artifact-card-active' : ''}`}
                  key={item.artifact_id}
                >
                  <button className="artifact-button" onClick={() => void loadSavedSession(item.artifact_id)} type="button">
                    <strong>{item.buyer_name}</strong>
                    <span>{item.company} / {item.negotiation_stage}</span>
                    <small>{item.runtime_mode} / {item.sentiment} / {item.deal_temperature} deg</small>
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No saved sessions yet.</p>
            </div>
          )}
          {libraryError ? <p className="session-alert">{libraryError}</p> : null}
        </article>

        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Buyer memory</p>
              <h3>Signals from this debrief</h3>
            </div>
          </div>
          <ul className="stack-list">
            {liveDebrief.behavioralMemory.map((item) => (
              <li key={item.label}>
                <strong>{item.label}</strong>
                <p>{item.value}</p>
              </li>
            ))}
          </ul>
        </article>

        <article className="surface side-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Learning engine</p>
              <h3>Session intelligence</h3>
            </div>
          </div>
          <ul className="stack-list">
            {liveDebrief.companyIntelligence.map((item) => (
              <li key={item.label}>
                <strong>{item.label}</strong>
                <p>{item.value}</p>
              </li>
            ))}
          </ul>
        </article>
      </aside>
    </section>
  )
}

// ─── Floating Whisper Overlay ─────────────────────────────────

function WhisperOverlay({
  latestWhisper,
  dealTemp,
  stage,
  opacity,
  onClose,
  onOpacityChange,
  onPopout,
}: {
  latestWhisper: WhisperHistoryItem | null
  dealTemp: number
  stage: string
  opacity: number
  onClose: () => void
  onOpacityChange: (v: number) => void
  onPopout: () => void
}) {
  const [pos, setPos] = useState({ x: 20, y: 80 })
  const [dragging, setDragging] = useState(false)
  const dragOffset = useRef({ x: 0, y: 0 })

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'BUTTON' || (e.target as HTMLElement).tagName === 'INPUT') return
    setDragging(true)
    dragOffset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
  }

  useEffect(() => {
    if (!dragging) return
    const handleMove = (e: MouseEvent) => {
      setPos({ x: e.clientX - dragOffset.current.x, y: e.clientY - dragOffset.current.y })
    }
    const handleUp = () => setDragging(false)
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
  }, [dragging])

  const hudColor = latestWhisper?.hud_color ?? 'blue'

  return (
    <div
      className={`whisper-overlay whisper-overlay-${hudColor}`}
      style={{ left: pos.x, top: pos.y, opacity, cursor: dragging ? 'grabbing' : 'grab' }}
      onMouseDown={handleMouseDown}
    >
      <div className="whisper-overlay-header">
        <span className="whisper-overlay-badge">{dealTemp} deg / {stage}</span>
        <div className="whisper-overlay-controls">
          <input
            type="range"
            min="0.15"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => onOpacityChange(Number(e.target.value))}
            className="whisper-overlay-slider"
            title="Overlay opacity"
          />
          <button className="whisper-overlay-btn" onClick={onPopout} type="button" title="Pop out to separate window">
            POP
          </button>
          <button className="whisper-overlay-btn" onClick={onClose} type="button" title="Hide overlay">
            X
          </button>
        </div>
      </div>
      <p className="whisper-overlay-text">
        {latestWhisper?.audio_text ?? 'Waiting for coaching whisper...'}
      </p>
      {latestWhisper ? (
        <span className="whisper-overlay-meta">
          {latestWhisper.whisper_type} / {latestWhisper.urgency} / {Math.round(latestWhisper.confidence * 100)}%
        </span>
      ) : null}
    </div>
  )
}

// ─── Shared Components ───────────────────────────────────────

function InsightCard({ body, title }: { body: string; title: string }) {
  return (
    <article className="insight-card" style={{borderTop:'2px solid var(--accent-gold)',position:'relative'}}>
      <span className="mini-label">{title}</span>
      <p>{body}</p>
    </article>
  )
}

function ScoreRingCard({ title, value }: { title: string; value: string }) {
  const numMatch = value.match(/(\d+)/)
  const numVal = numMatch ? parseInt(numMatch[1], 10) : 0
  const pct = Math.min(100, Math.max(0, numVal))
  const circumference = 2 * Math.PI * 18
  const offset = circumference - (pct / 100) * circumference

  return (
    <article className="insight-card" style={{borderTop:'2px solid var(--accent-teal)',display:'flex',alignItems:'center',gap:'0.75rem'}}>
      <svg width="48" height="48" viewBox="0 0 48 48" style={{flexShrink:0}}>
        <circle cx="24" cy="24" r="18" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
        <circle cx="24" cy="24" r="18" fill="none" stroke="var(--accent-teal)" strokeWidth="3" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" transform="rotate(-90 24 24)" style={{transition:'stroke-dashoffset 0.8s ease-out'}} />
        <text x="24" y="26" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontFamily="var(--font-mono)">{pct}</text>
      </svg>
      <div>
        <span className="mini-label">{title}</span>
        <p>{value}</p>
      </div>
    </article>
  )
}

function DebriefList({ items, title }: { items: string[]; title: string }) {
  return (
    <div className="surface surface-nested">
      <p className="eyebrow">{title}</p>
      <ul className="stack-list stack-list-compact">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

function HudMetric({ detail, label, value }: { detail: string; label: string; value: string }) {
  return (
    <div className="hud-metric" style={{borderBottom:'2px solid transparent',borderImage:'linear-gradient(90deg, var(--accent-gold), transparent) 1',paddingBottom:'0.5rem'}}>
      <span>{label}</span>
      <strong style={{fontFamily:'var(--font-mono)'}}>{value}</strong>
      <small>{detail}</small>
    </div>
  )
}

function OutputCard({ body, footer, title, icon }: { body: string; footer: string; title: string; icon?: string }) {
  return (
    <article className="surface surface-nested">
      <p className="eyebrow" style={{display:'flex',alignItems:'center',gap:'0.35rem'}}>
        {icon ? <span>{icon}</span> : null}
        {title}
      </p>
      <p>{body}</p>
      <small>{footer}</small>
    </article>
  )
}

function StatChip({ label, value, live }: { label: string; value: string; live?: boolean }) {
  return (
    <div className="stat-chip" style={{transition:'box-shadow var(--transition-base)',cursor:'default'}}>
      <span>{label}</span>
      <strong style={{display:'flex',alignItems:'center',gap:'0.35rem'}}>
        {live ? (
          <span style={{display:'inline-block',width:'0.4rem',height:'0.4rem',borderRadius:'50%',background:'var(--accent-teal)',boxShadow:'0 0 6px var(--accent-teal-glow)',animation:'pulse 1.5s ease-in-out infinite'}} />
        ) : null}
        {value}
      </strong>
    </div>
  )
}

function TranscriptFeed({ entries }: { entries: TranscriptEntry[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.scrollTop = container.scrollHeight
  }, [entries])

  if (entries.length === 0) {
    return (
      <div className="transcript-empty">
        <p>Transcripts will stream here once the session begins.</p>
      </div>
    )
  }

  return (
    <div className="transcript transcript-live" ref={containerRef}>
      {entries.map((entry, idx) => (
        <div className={`turn ${transcriptClass(entry.direction)}`} key={entry.id} style={{opacity: idx % 2 === 0 ? 1 : 0.88}}>
          <div className="turn-head">
            <strong>{entry.speaker_label}</strong>
            <span className="mini-label">{entry.received_at_label}</span>
          </div>
          <p>{entry.text}</p>
        </div>
      ))}
    </div>
  )
}

function WhisperHistory({ items }: { items: WhisperHistoryItem[] }) {
  if (items.length === 0) {
    return (
      <div className="transcript-empty">
        <p>Coaching whispers will appear here as the AI detects key moments.</p>
      </div>
    )
  }

  return (
    <div className="whisper-list">
      {items.map((item) => (
        <article className={`whisper-item whisper-${item.hud_color}`} key={item.id}>
          <div className="turn-head">
            <strong style={{display:'flex',alignItems:'center',gap:'0.35rem'}}>
              <span style={{display:'inline-block',width:'0.4rem',height:'0.4rem',borderRadius:'50%',background: whisperDotColor(item.whisper_type)}} />
              {item.whisper_type}
            </strong>
            <span className="mini-label">{item.received_at_label}</span>
          </div>
          <p>{item.audio_text}</p>
          <small>
            {item.hud_text} / {item.urgency} / {Math.round(item.confidence * 100)}%
          </small>
        </article>
      ))}
    </div>
  )
}

function MediaPreview({ detail, stream, title }: { detail: string; stream: MediaStream | null; title: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null)

  useEffect(() => {
    if (!videoRef.current) return
    videoRef.current.srcObject = stream
  }, [stream])

  return (
    <div className="preview-shell">
      <div className="card-header">
        <div>
          <p className="eyebrow">Camera</p>
          <h4>{title}</h4>
        </div>
      </div>
      {stream ? <video autoPlay className="preview-video" muted playsInline ref={videoRef} /> : <div className="preview-empty">No camera or screen stream attached.</div>}
      <p className="preview-detail">{detail}</p>
    </div>
  )
}

function ShimmerBlock({ lines = 3 }: { lines?: number }) {
  return (
    <div className="shimmer-block" style={{display:'flex',flexDirection:'column',gap:'0.5rem'}}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="shimmer shimmer-line" style={i === lines - 1 ? { width: '65%' } : undefined} />
      ))}
    </div>
  )
}

// ─── Utility Functions ───────────────────────────────────────

function transcriptClass(direction: TranscriptEntry['direction']) {
  if (direction === 'input') return 'turn-buyer'
  if (direction === 'output') return 'turn-agent'
  if (direction === 'note') return 'turn-note'
  return 'turn-system'
}

function statusLabel(status: DealWhisperSession['status']) {
  return status.replace('-', ' ')
}

function statusPillClass(status: DealWhisperSession['status']) {
  if (status === 'live') return 'pill-live'
  if (status === 'error') return 'pill-warn'
  if (status === 'connecting' || status === 'ending') return 'pill-soft'
  return ''
}

function whisperDotColor(whisperType: string): string {
  const t = whisperType.toLowerCase()
  if (t.includes('objection') || t.includes('risk')) return 'var(--accent-red)'
  if (t.includes('close') || t.includes('signal')) return 'var(--accent-teal)'
  if (t.includes('coach') || t.includes('ratio')) return 'var(--accent-yellow)'
  return 'var(--accent-blue)'
}

function outputIcon(index: number): string {
  const icons = ['▸', '◆', '◉', '↗', '📊', '✦']
  return icons[index % icons.length]
}

export default App
