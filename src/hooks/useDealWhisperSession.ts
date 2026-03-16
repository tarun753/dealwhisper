import { useCallback, useEffect, useRef, useState } from 'react'
import { buildApiEndpoint, buildWsEndpoint, fetchJsonWithAuth } from '../lib/backend'
import {
  defaultHudState,
  type BuyerContext,
  type ConnectionStats,
  type DealHudState,
  type LiveRuntimeMode,
  type LiveSessionStatus,
  type LiveSessionSummary,
  type TranscriptEntry,
  type VisualSource,
  type WhisperHistoryItem,
  type WhisperPayload,
} from '../types/live'

function inferBackendWsBase(): string {
  if (import.meta.env.VITE_DEALWHISPER_BACKEND_WS_BASE) return import.meta.env.VITE_DEALWHISPER_BACKEND_WS_BASE as string
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws/call`
  }
  return 'ws://127.0.0.1:8080/ws/call'
}
const DEFAULT_BACKEND_WS_BASE = inferBackendWsBase()
const INPUT_SAMPLE_RATE = 16000
const OUTPUT_SAMPLE_RATE = 24000
const MAX_TRANSCRIPT_ITEMS = 60
const MAX_WHISPERS = 20

type ConnectOptions = {
  backendWsBase?: string
  buyerContext: BuyerContext
  callId: string
  captureAudio?: boolean
  initialNotes?: string[]
  scriptedNotes?: Array<{
    delayMs: number
    text: string
  }>
  visualSource: VisualSource
}

type SessionMeta = {
  artifactId: string | null
  backendWsBase: string
  buyerContext: BuyerContext
  callId: string
}

type ServerMessage =
  | {
      type: 'session.ready'
      artifact_id?: string
      artifactId?: string
      call_id?: string
      callId?: string
      hud_state?: DealHudState
      hudState?: DealHudState
      runtime_mode?: LiveRuntimeMode
      runtimeMode?: LiveRuntimeMode
    }
  | { type: 'hud.state'; payload: DealHudState }
  | { type: 'whisper.payload'; payload: WhisperPayload }
  | { type: 'transcript.input'; text: string }
  | { type: 'transcript.output'; text: string }
  | { type: 'session.warning'; message: string }
  | { type: 'session.error'; message: string }
  | { type: 'live.audio'; data: string; mime_type?: string; mimeType?: string }

export type DealWhisperSession = {
  status: LiveSessionStatus
  error: string | null
  hudState: DealHudState
  latestWhisper: WhisperHistoryItem | null
  whisperHistory: WhisperHistoryItem[]
  transcriptFeed: TranscriptEntry[]
  previewStream: MediaStream | null
  currentVisualSource: VisualSource
  runtimeMode: LiveRuntimeMode
  elapsedSeconds: number
  sessionMeta: SessionMeta | null
  lastSummary: LiveSessionSummary | null
  connectionStats: ConnectionStats | null
  connect: (options: ConnectOptions) => Promise<void>
  disconnect: () => Promise<void>
  sendNote: (text: string) => Promise<void>
  switchVisualSource: (source: VisualSource) => Promise<void>
  clearSession: () => Promise<void>
}

function createId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

function formatClock(timestamp: number) {
  return new Intl.DateTimeFormat([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(timestamp)
}

function arrayBufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''

  for (let index = 0; index < bytes.length; index += 1) {
    binary += String.fromCharCode(bytes[index])
  }

  return btoa(binary)
}

function base64ToUint8Array(base64: string) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }

  return bytes
}

function floatToInt16(samples: Float32Array, sourceSampleRate: number, targetSampleRate = INPUT_SAMPLE_RATE) {
  if (samples.length === 0) {
    return new Int16Array()
  }

  if (sourceSampleRate === targetSampleRate) {
    const pcm = new Int16Array(samples.length)

    for (let index = 0; index < samples.length; index += 1) {
      const clamped = Math.max(-1, Math.min(1, samples[index]))
      pcm[index] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
    }

    return pcm
  }

  const sampleRateRatio = sourceSampleRate / targetSampleRate
  const resultLength = Math.round(samples.length / sampleRateRatio)
  const result = new Int16Array(resultLength)
  let offsetResult = 0
  let offsetBuffer = 0

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio)
    let accumulated = 0
    let count = 0

    for (let index = offsetBuffer; index < nextOffsetBuffer && index < samples.length; index += 1) {
      accumulated += samples[index]
      count += 1
    }

    const sample = count > 0 ? accumulated / count : samples[offsetBuffer] ?? 0
    const clamped = Math.max(-1, Math.min(1, sample))
    result[offsetResult] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff

    offsetResult += 1
    offsetBuffer = nextOffsetBuffer
  }

  return result
}

function int16ToFloat32(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const float32 = new Float32Array(bytes.byteLength / 2)

  for (let index = 0; index < float32.length; index += 1) {
    const int16 = view.getInt16(index * 2, true)
    float32[index] = int16 / 0x8000
  }

  return float32
}

function parseSampleRate(mimeType: string | undefined) {
  const matched = mimeType?.match(/rate=(\d+)/)
  if (matched) {
    return Number(matched[1])
  }
  return OUTPUT_SAMPLE_RATE
}

async function createVisualStream(source: VisualSource) {
  if (!navigator.mediaDevices) {
    throw new Error('Media devices are not available in this browser.')
  }

  if (source === 'camera') {
    return navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user',
      },
      audio: false,
    })
  }

  if (source === 'screen') {
    if (!('getDisplayMedia' in navigator.mediaDevices)) {
      throw new Error('Screen capture is not supported in this browser.')
    }

    return navigator.mediaDevices.getDisplayMedia({
      video: {
        frameRate: { ideal: 1, max: 2 },
      },
      audio: false,
    })
  }

  return null
}

async function blobToBase64(blob: Blob) {
  const buffer = await blob.arrayBuffer()
  return arrayBufferToBase64(buffer)
}

export function useDealWhisperSession(): DealWhisperSession {
  const [status, setStatus] = useState<LiveSessionStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [hudState, setHudState] = useState<DealHudState>(defaultHudState)
  const [latestWhisper, setLatestWhisper] = useState<WhisperHistoryItem | null>(null)
  const [whisperHistory, setWhisperHistory] = useState<WhisperHistoryItem[]>([])
  const [transcriptFeed, setTranscriptFeed] = useState<TranscriptEntry[]>([])
  const [previewStream, setPreviewStream] = useState<MediaStream | null>(null)
  const [currentVisualSource, setCurrentVisualSource] = useState<VisualSource>('camera')
  const [runtimeMode, setRuntimeMode] = useState<LiveRuntimeMode>('unknown')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [sessionMeta, setSessionMeta] = useState<SessionMeta | null>(null)
  const [lastSummary, setLastSummary] = useState<LiveSessionSummary | null>(null)
  const [connectionStats, setConnectionStats] = useState<ConnectionStats | null>(null)

  const websocketRef = useRef<WebSocket | null>(null)
  const microphoneStreamRef = useRef<MediaStream | null>(null)
  const visualStreamRef = useRef<MediaStream | null>(null)
  const inputAudioContextRef = useRef<AudioContext | null>(null)
  const outputAudioContextRef = useRef<AudioContext | null>(null)
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null)
  const captureIntervalRef = useRef<number | null>(null)
  const demoTimeoutsRef = useRef<number[]>([])
  const captureVideoElementRef = useRef<HTMLVideoElement | null>(null)
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const nextPlaybackTimeRef = useRef(0)
  const intentionalCloseRef = useRef(false)
  const summaryBuiltRef = useRef(false)
  const startedAtRef = useRef<number | null>(null)
  const sessionMetaRef = useRef<SessionMeta | null>(null)
  const hudStateRef = useRef(hudState)
  const transcriptFeedRef = useRef(transcriptFeed)
  const whisperHistoryRef = useRef(whisperHistory)
  const connectionStatsRef = useRef(connectionStats)
  const runtimeModeRef = useRef(runtimeMode)

  useEffect(() => {
    hudStateRef.current = hudState
  }, [hudState])

  useEffect(() => {
    transcriptFeedRef.current = transcriptFeed
  }, [transcriptFeed])

  useEffect(() => {
    whisperHistoryRef.current = whisperHistory
  }, [whisperHistory])

  useEffect(() => {
    connectionStatsRef.current = connectionStats
  }, [connectionStats])

  useEffect(() => {
    runtimeModeRef.current = runtimeMode
  }, [runtimeMode])

  useEffect(() => {
    sessionMetaRef.current = sessionMeta
  }, [sessionMeta])

  useEffect(() => {
    if (status !== 'live') {
      setElapsedSeconds(0)
      return
    }

    const interval = window.setInterval(() => {
      if (startedAtRef.current) {
        setElapsedSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000))
      }
    }, 1000)

    return () => {
      window.clearInterval(interval)
    }
  }, [status])

  const pushTranscript = (entry: Omit<TranscriptEntry, 'id' | 'received_at' | 'received_at_label'>) => {
    const timestamp = Date.now()
    const enriched: TranscriptEntry = {
      ...entry,
      id: createId('transcript'),
      received_at: timestamp,
      received_at_label: formatClock(timestamp),
    }

    setTranscriptFeed((previous) => [...previous.slice(-(MAX_TRANSCRIPT_ITEMS - 1)), enriched])
  }

  const pushWhisper = (payload: WhisperPayload) => {
    const timestamp = Date.now()
    const enriched: WhisperHistoryItem = {
      ...payload,
      id: createId('whisper'),
      received_at: timestamp,
      received_at_label: formatClock(timestamp),
    }

    setLatestWhisper(enriched)
    setWhisperHistory((previous) => [enriched, ...previous].slice(0, MAX_WHISPERS))
  }

  const sendTextTurn = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || websocketRef.current?.readyState !== WebSocket.OPEN) {
      return
    }

    websocketRef.current.send(
      JSON.stringify({
        type: 'text.turn',
        text: trimmed,
        turn_complete: true,
      }),
    )

    setConnectionStats((previous) =>
      previous
        ? {
            ...previous,
            notes_sent: previous.notes_sent + 1,
          }
        : previous,
    )

    pushTranscript({
      direction: 'note',
      speaker_label: 'Seller note',
      text: trimmed,
    })
  }

  const resetLiveState = () => {
    setError(null)
    setHudState(defaultHudState)
    setLatestWhisper(null)
    setWhisperHistory([])
    setTranscriptFeed([])
    setPreviewStream(null)
    setRuntimeMode('unknown')
    setElapsedSeconds(0)
    setConnectionStats(null)
    startedAtRef.current = null
  }

  const stopVisualCapture = useCallback(async () => {
    if (captureIntervalRef.current !== null) {
      window.clearInterval(captureIntervalRef.current)
      captureIntervalRef.current = null
    }

    const videoElement = captureVideoElementRef.current
    if (videoElement) {
      videoElement.pause()
      videoElement.srcObject = null
    }
    captureVideoElementRef.current = null
    captureCanvasRef.current = null

    visualStreamRef.current?.getTracks().forEach((track) => track.stop())
    visualStreamRef.current = null
    setPreviewStream(null)
  }, [])

  const stopAudioCapture = useCallback(async () => {
    scriptProcessorRef.current?.disconnect()
    scriptProcessorRef.current = null

    if (inputAudioContextRef.current && inputAudioContextRef.current.state !== 'closed') {
      await inputAudioContextRef.current.close()
    }
    inputAudioContextRef.current = null

    microphoneStreamRef.current?.getTracks().forEach((track) => track.stop())
    microphoneStreamRef.current = null
  }, [])

  useEffect(() => {
    return () => {
      // cleanup
      websocketRef.current?.close()
      void stopVisualCapture()
      void stopAudioCapture()
    }
  }, [stopAudioCapture, stopVisualCapture])

  const clearDemoTimeouts = () => {
    demoTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
    demoTimeoutsRef.current = []
  }

  const playIncomingAudio = async (base64: string, mimeType?: string) => {
    const bytes = base64ToUint8Array(base64)
    const samples = int16ToFloat32(bytes)

    if (!outputAudioContextRef.current) {
      outputAudioContextRef.current = new AudioContext()
    }

    if (outputAudioContextRef.current.state === 'suspended') {
      await outputAudioContextRef.current.resume()
    }

    const sampleRate = parseSampleRate(mimeType)
    const audioBuffer = outputAudioContextRef.current.createBuffer(1, samples.length, sampleRate)
    audioBuffer.copyToChannel(samples, 0)

    const source = outputAudioContextRef.current.createBufferSource()
    source.buffer = audioBuffer
    source.connect(outputAudioContextRef.current.destination)

    const startAt = Math.max(outputAudioContextRef.current.currentTime, nextPlaybackTimeRef.current)
    source.start(startAt)
    nextPlaybackTimeRef.current = startAt + audioBuffer.duration
  }

  const finalizeSummary = (overrideStatus?: LiveSessionStatus, overrideError?: string | null) => {
    if (summaryBuiltRef.current) {
      return
    }

    const meta = sessionMetaRef.current
    const startedAt = startedAtRef.current
    if (!meta || !startedAt) {
      return
    }

    summaryBuiltRef.current = true
    const endedAt = Date.now()

    const localSummary: LiveSessionSummary = {
      artifact_id: meta.artifactId ?? undefined,
      status: overrideError ? 'error' : 'completed',
      saved_at: undefined,
      buyer_context: meta.buyerContext,
      started_at: startedAt,
      ended_at: endedAt,
      duration_seconds: Math.max(1, Math.floor((endedAt - startedAt) / 1000)),
      whisper_history: whisperHistoryRef.current,
      transcript_feed: transcriptFeedRef.current,
      final_hud_state: hudStateRef.current,
      connection_stats:
        connectionStatsRef.current ??
        ({
          audio_chunks_sent: 0,
          video_frames_sent: 0,
          notes_sent: 0,
          backend_ws_base: meta.backendWsBase,
          call_id: meta.callId,
          visual_source: currentVisualSource,
          runtime_mode: runtimeModeRef.current,
        } as ConnectionStats),
    }

    setLastSummary(localSummary)
    if (meta.artifactId) {
      void (async () => {
        for (let attempt = 0; attempt < 5; attempt += 1) {
          try {
            const persisted = await fetchJsonWithAuth<LiveSessionSummary>(
              buildApiEndpoint(meta.backendWsBase, `/api/sessions/${meta.artifactId}`),
            )
            setLastSummary(persisted)
            return
          } catch {
            await new Promise((resolve) => window.setTimeout(resolve, 250))
          }
        }
      })()
    }

    setStatus(overrideStatus ?? (overrideError ? 'error' : 'ended'))
    if (overrideError) {
      setError(overrideError)
    }
  }


  const handleServerMessage = async (message: MessageEvent<string>) => {
    const payload = JSON.parse(message.data) as ServerMessage

    if (payload.type === 'session.ready') {
      const nextRuntimeMode = payload.runtime_mode ?? payload.runtimeMode ?? 'unknown'
      const artifactId = payload.artifact_id ?? payload.artifactId ?? null
      setRuntimeMode(nextRuntimeMode)
      setConnectionStats((previous) =>
        previous
          ? {
              ...previous,
              runtime_mode: nextRuntimeMode,
            }
          : previous,
      )
      setSessionMeta((previous) =>
        previous
          ? {
              ...previous,
              artifactId,
            }
          : previous,
      )
      setHudState(payload.hud_state ?? payload.hudState ?? defaultHudState)
      setStatus('live')
      return
    }

    if (payload.type === 'hud.state') {
      setHudState(payload.payload)
      return
    }

    if (payload.type === 'whisper.payload') {
      pushWhisper(payload.payload)
      // whispers are text-only — no audio playback
      return
    }

    if (payload.type === 'transcript.input') {
      pushTranscript({
        direction: 'input',
        speaker_label: 'Buyer',
        text: payload.text,
      })
      return
    }

    if (payload.type === 'transcript.output') {
      pushTranscript({
        direction: 'output',
        speaker_label: 'DealWhisper',
        text: payload.text,
      })
      return
    }

    if (payload.type === 'session.warning') {
      pushTranscript({
        direction: 'system',
        speaker_label: 'System',
        text: payload.message,
      })
      return
    }

    if (payload.type === 'session.error') {
      pushTranscript({
        direction: 'system',
        speaker_label: 'System',
        text: payload.message,
      })
      setError(payload.message)
      setStatus('error')
      return
    }

    if (payload.type === 'live.audio') {
      await playIncomingAudio(payload.data, payload.mime_type ?? payload.mimeType)
    }
  }

  const startAudioCapture = async (stream: MediaStream) => {
    const audioContext = new AudioContext()
    inputAudioContextRef.current = audioContext
    if (audioContext.state === 'suspended') {
      await audioContext.resume()
    }

    const source = audioContext.createMediaStreamSource(stream)
    const processor = audioContext.createScriptProcessor(4096, 1, 1)
    const silenceGain = audioContext.createGain()
    silenceGain.gain.value = 0

    processor.onaudioprocess = (event) => {
      if (websocketRef.current?.readyState !== WebSocket.OPEN) {
        return
      }

      const input = event.inputBuffer.getChannelData(0)
      const pcm = floatToInt16(input, audioContext.sampleRate)

      if (pcm.length === 0) {
        return
      }

      websocketRef.current.send(
        JSON.stringify({
          type: 'audio.chunk',
          mime_type: `audio/pcm;rate=${INPUT_SAMPLE_RATE}`,
          data: arrayBufferToBase64(pcm.buffer),
        }),
      )

      setConnectionStats((previous) =>
        previous
          ? {
              ...previous,
              audio_chunks_sent: previous.audio_chunks_sent + 1,
            }
          : previous,
      )
    }

    source.connect(processor)
    processor.connect(silenceGain)
    silenceGain.connect(audioContext.destination)
    scriptProcessorRef.current = processor
  }

  const startVisualCapture = async (source: VisualSource, existingStream?: MediaStream | null) => {
    if (source === 'none') {
      await stopVisualCapture()
      setCurrentVisualSource('none')
      setConnectionStats((previous) =>
        previous
          ? {
              ...previous,
              visual_source: 'none',
            }
          : previous,
      )
      return
    }

    await stopVisualCapture()
    const stream = existingStream ?? await createVisualStream(source)
    if (!stream) {
      return
    }

    visualStreamRef.current = stream
    setPreviewStream(stream)
    setCurrentVisualSource(source)
    setConnectionStats((previous) =>
      previous
        ? {
            ...previous,
            visual_source: source,
          }
        : previous,
    )

    const videoElement = document.createElement('video')
    videoElement.muted = true
    videoElement.playsInline = true
    videoElement.srcObject = stream
    await videoElement.play()

    const canvas = document.createElement('canvas')
    captureVideoElementRef.current = videoElement
    captureCanvasRef.current = canvas

    const [videoTrack] = stream.getVideoTracks()
    if (videoTrack) {
      videoTrack.onended = () => {
        void stopVisualCapture()
        setCurrentVisualSource('none')
      }
    }

    captureIntervalRef.current = window.setInterval(() => {
      if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
        return
      }

      if (!videoElement.videoWidth || !videoElement.videoHeight) {
        return
      }

      canvas.width = videoElement.videoWidth
      canvas.height = videoElement.videoHeight
      const context = canvas.getContext('2d')
      if (!context) {
        return
      }

      context.drawImage(videoElement, 0, 0, canvas.width, canvas.height)
      canvas.toBlob(
        async (blob) => {
          if (!blob || !websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
            return
          }

          websocketRef.current.send(
            JSON.stringify({
              type: 'video.frame',
              mime_type: 'image/jpeg',
              data: await blobToBase64(blob),
            }),
          )

          setConnectionStats((previous) =>
            previous
              ? {
                  ...previous,
                  video_frames_sent: previous.video_frames_sent + 1,
                }
              : previous,
          )
        },
        'image/jpeg',
        0.72,
      )
    }, 1000)
  }

  const closeTransport = async (sendAudioEnd: boolean) => {
    clearDemoTimeouts()
    if (sendAudioEnd && websocketRef.current?.readyState === WebSocket.OPEN) {
      websocketRef.current.send(JSON.stringify({ type: 'audio.end' }))
    }

    websocketRef.current?.close()
    websocketRef.current = null

    await stopVisualCapture()
    await stopAudioCapture()
  }

  const disconnect = async () => {
    intentionalCloseRef.current = true
    setStatus('ending')
    await closeTransport(true)
    finalizeSummary('ended', null)
  }

  const connect = async ({
    backendWsBase,
    buyerContext,
    callId,
    captureAudio = true,
    initialNotes = [],
    scriptedNotes = [],
    visualSource,
  }: ConnectOptions) => {
    await disconnect().catch(() => undefined)
    summaryBuiltRef.current = false
    intentionalCloseRef.current = false
    resetLiveState()
    clearDemoTimeouts()
    setStatus('connecting')

    const normalizedBase = (backendWsBase ?? DEFAULT_BACKEND_WS_BASE).replace(/\/$/, '')
    const meta: SessionMeta = {
      artifactId: null,
      backendWsBase: normalizedBase,
      buyerContext,
      callId,
    }

    setSessionMeta(meta)
    setConnectionStats({
      audio_chunks_sent: 0,
      video_frames_sent: 0,
      notes_sent: 0,
      backend_ws_base: normalizedBase,
      call_id: callId,
      visual_source: visualSource,
      runtime_mode: 'unknown',
    })
    startedAtRef.current = Date.now()

    try {
      if (captureAudio && !navigator.mediaDevices?.getUserMedia) {
        throw new Error('Microphone capture is not supported in this browser.')
      }

      if (captureAudio) {
        const microphoneStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        })
        microphoneStreamRef.current = microphoneStream
      }

      // Request screen/camera capture early while user-gesture context is still active
      let earlyVisualStream: MediaStream | null = null
      if (visualSource !== 'none') {
        try {
          earlyVisualStream = await createVisualStream(visualSource)
        } catch (visualError) {
          const message = visualError instanceof Error ? visualError.message : 'Visual capture unavailable.'
          setError(message)
          pushTranscript({
            direction: 'system',
            speaker_label: 'System',
            text: `${message} Continuing audio-only.`,
          })
        }
      }

      const websocket = new WebSocket(buildWsEndpoint(normalizedBase, callId))
      websocketRef.current = websocket

      const opened = new Promise<void>((resolve, reject) => {
        websocket.onopen = () => resolve()
        websocket.onerror = () => reject(new Error('WebSocket connection failed.'))
      })

      websocket.onmessage = (event) => {
        void handleServerMessage(event as MessageEvent<string>)
      }

      websocket.onclose = () => {
        void stopVisualCapture()
        void stopAudioCapture()
        if (!intentionalCloseRef.current) {
          finalizeSummary('ended', null)
        }
      }

      await opened

      websocket.send(
        JSON.stringify({
          buyer_context: buyerContext,
          session_options: {
            visual_source: visualSource,
          },
        }),
      )

      for (const note of initialNotes) {
        sendTextTurn(note)
      }

      scriptedNotes.forEach((note) => {
        const timeoutId = window.setTimeout(() => {
          sendTextTurn(note.text)
        }, note.delayMs)
        demoTimeoutsRef.current.push(timeoutId)
      })

      if (captureAudio && microphoneStreamRef.current) {
        await startAudioCapture(microphoneStreamRef.current)
      }

      if (visualSource !== 'none' && earlyVisualStream) {
        try {
          await startVisualCapture(visualSource, earlyVisualStream)
        } catch (visualError) {
          const message = visualError instanceof Error ? visualError.message : 'Visual capture unavailable. Continuing audio-only.'
          setError(message)
          pushTranscript({
            direction: 'system',
            speaker_label: 'System',
            text: `${message} Continuing audio-only.`,
          })
          setCurrentVisualSource('none')
        }
      } else {
        setCurrentVisualSource('none')
      }

      if (!outputAudioContextRef.current) {
        outputAudioContextRef.current = new AudioContext()
      }
      if (outputAudioContextRef.current.state === 'suspended') {
        await outputAudioContextRef.current.resume()
      }
    } catch (connectError) {
      const message = connectError instanceof Error ? connectError.message : 'Unable to start the live session.'
      setError(message)
      setStatus('error')
      await closeTransport(false)
    }
  }

  const sendNote = async (text: string) => {
    sendTextTurn(text)
  }

  const switchVisualSource = async (source: VisualSource) => {
    if (source === currentVisualSource) {
      return
    }

    setCurrentVisualSource(source)
    if (status !== 'live' && status !== 'connecting') {
      return
    }

    try {
      await startVisualCapture(source)
    } catch (switchError) {
      const message = switchError instanceof Error ? switchError.message : 'Unable to switch visual source.'
      setError(message)
      pushTranscript({
        direction: 'system',
        speaker_label: 'System',
        text: message,
      })
    }
  }

  const clearSession = async () => {
    intentionalCloseRef.current = true
    await closeTransport(false)
    setSessionMeta(null)
    setLastSummary(null)
    resetLiveState()
    setStatus('idle')
  }

  return {
    status,
    error,
    hudState,
    latestWhisper,
    whisperHistory,
    transcriptFeed,
    previewStream,
    currentVisualSource,
    runtimeMode,
    elapsedSeconds,
    sessionMeta,
    lastSummary,
    connectionStats,
    connect,
    disconnect,
    sendNote,
    switchVisualSource,
    clearSession,
  }
}
