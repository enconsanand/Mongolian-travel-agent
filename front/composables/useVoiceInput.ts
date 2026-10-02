import { API_ENDPOINTS } from '~/constants'
import type { TripPlannerMessages } from '~/types/trip-planner'

/** Anir works on 16 kHz speech */
const SAMPLE_RATE = 16_000
/** A request, not a monologue: recording stops by itself after this long */
const MAX_RECORDING_MS = 60_000

/** `denied`: no microphone permission; `unavailable`: speech-to-text is not set up on the server (no oyu key) */
export type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error' | 'denied' | 'unavailable'

/** What the bar says while the microphone works (or why it does not); `idle` when it waits for the traveller */
export function voiceStatusText(state: VoiceState, messages: TripPlannerMessages, idle: string): string {
  if (state === 'recording') return messages.listening
  if (state === 'transcribing') return messages.transcribing
  if (state === 'denied') return messages.voiceDenied
  if (state === 'unavailable') return messages.voiceUnavailable
  if (state === 'error') return messages.voiceFailed
  return idle
}

/** Mono 16-bit PCM samples as a WAV file, which Anir accepts (the browser records WebM or Ogg, which it may not) */
function toWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) =>
    [...value].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)))
  text(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  text(8, 'WAVE')
  text(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  text(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((sample, i) => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return new Blob([buffer], { type: 'audio/wav' })
}

/** The browser's recording, decoded and resampled to 16 kHz mono */
async function toSpeechWav(recording: Blob): Promise<Blob> {
  const decoded = await new AudioContext().decodeAudioData(await recording.arrayBuffer())
  const length = Math.ceil(decoded.duration * SAMPLE_RATE)
  const offline = new OfflineAudioContext(1, length, SAMPLE_RATE)
  const source = offline.createBufferSource()
  source.buffer = decoded
  source.connect(offline.destination)
  source.start()
  return toWav((await offline.startRendering()).getChannelData(0), SAMPLE_RATE)
}

/**
 * The microphone button: record, then let Anir (oyu's Mongolian speech-to-text, through our API so the key stays
 * on the server) turn the recording into text. `onText` gets each transcript.
 */
export function useVoiceInput(onText: (text: string) => void) {
  const api = useApi()
  const state = ref<VoiceState>('idle')
  let recorder: MediaRecorder | null = null
  let stopTimer: ReturnType<typeof setTimeout> | null = null

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chunks: Blob[] = []
      recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (event) => event.data.size && chunks.push(event.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop())
        await transcribe(new Blob(chunks, { type: recorder?.mimeType }))
      }
      recorder.start()
      state.value = 'recording'
      stopTimer = setTimeout(stop, MAX_RECORDING_MS)
    } catch (error) {
      state.value = (error as DOMException)?.name === 'NotAllowedError' ? 'denied' : 'error'
    }
  }

  function stop() {
    if (stopTimer) clearTimeout(stopTimer)
    stopTimer = null
    if (recorder?.state === 'recording') {
      state.value = 'transcribing'
      recorder.stop()
    }
  }

  async function transcribe(recording: Blob) {
    try {
      const form = new FormData()
      form.append('file', await toSpeechWav(recording), 'speech.wav')
      const { data, error } = await api.post<{ text: string }>(API_ENDPOINTS.SPEECH.TRANSCRIBE, form)
      const code = (error as { data?: { detail?: { code?: string } } } | null)?.data?.detail?.code
      if (data?.text) {
        onText(data.text)
        state.value = 'idle'
      } else state.value = code === 'not_configured' ? 'unavailable' : 'error'
    } catch {
      state.value = 'error'
    }
  }

  function toggle() {
    if (state.value === 'recording') stop()
    else if (state.value !== 'transcribing') start()
  }

  onScopeDispose(stop)

  return { state, toggle }
}
