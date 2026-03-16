import { useCallback, useRef, useState } from 'react'

type VoiceInputState = 'idle' | 'listening' | 'error'

interface SpeechRecognitionEvent {
  resultIndex: number
  results: SpeechRecognitionResultList
}

export function useVoiceInput(onTranscript: (text: string) => void) {
  const [state, setState] = useState<VoiceInputState>('idle')
  const recognitionRef = useRef<any>(null)

  const isSupported =
    typeof window !== 'undefined' &&
    ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)

  const start = useCallback(() => {
    if (!isSupported) {
      setState('error')
      return
    }

    const SpeechRecognition =
      (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => setState('listening')

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const last = event.results[event.results.length - 1]
      if (last?.isFinal) {
        const text = last[0]?.transcript?.trim()
        if (text) onTranscript(text)
      }
    }

    recognition.onerror = () => {
      setState('idle')
    }

    recognition.onend = () => {
      setState('idle')
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [isSupported, onTranscript])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  const toggle = useCallback(() => {
    if (state === 'listening') {
      stop()
    } else {
      start()
    }
  }, [state, start, stop])

  return { state, isSupported, toggle }
}
