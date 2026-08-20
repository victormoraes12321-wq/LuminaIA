'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void
  disabled?: boolean
  className?: string
}

export function VoiceInputButton({ onTranscript, disabled = false, className }: VoiceInputButtonProps) {
  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(true)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setIsSupported(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'pt-BR'

    recognition.onresult = (event: any) => {
      let currentTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptChunk = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          currentTranscript += transcriptChunk + ' '
        } else {
          currentTranscript += transcriptChunk
        }
      }
      if (currentTranscript.trim()) {
        onTranscript(currentTranscript.trim())
      }
    }

    recognition.onerror = (event: any) => {
      console.warn('[VoiceInput] Speech recognition error:', event.error)
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      try {
        recognition.stop()
      } catch {}
    }
  }, [onTranscript])

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current || disabled) return

    if (isListening) {
      try {
        recognitionRef.current.stop()
      } catch {}
      setIsListening(false)
    } else {
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        console.warn('[VoiceInput] Could not start speech recognition:', err)
        setIsListening(false)
      }
    }
  }, [isListening, disabled])

  if (!isSupported) {
    return null
  }

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        className={cn(
          'relative flex h-8 w-8 items-center justify-center rounded-xl transition-all duration-200 cursor-pointer',
          isListening
            ? 'bg-rose-500 text-white shadow-[0_0_15px_rgba(244,63,94,0.6)] animate-pulse'
            : 'text-zinc-400 hover:text-cyan-400 hover:bg-zinc-800/60',
          disabled && 'opacity-40 cursor-not-allowed',
          className
        )}
        title={isListening ? 'Clique para parar de gravar' : 'Falar pergunta por voz (Speech-to-Text)'}
        aria-label={isListening ? 'Parar gravação de voz' : 'Iniciar gravação de voz'}
      >
        <AnimatePresence mode="wait">
          {isListening ? (
            <motion.div
              key="listening"
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.8 }}
              className="flex items-center justify-center"
            >
              <Mic size={15} className="text-white animate-bounce" />
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.8 }}
            >
              <Mic size={15} />
            </motion.div>
          )}
        </AnimatePresence>
      </button>

      {isListening && (
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-rose-950/90 border border-rose-500/40 px-2 py-0.5 text-[10px] font-bold text-rose-200 shadow-md">
          Ouvindo...
        </span>
      )}
    </div>
  )
}
