import { API_ENDPOINTS } from '~/constants'
import { toWav } from '~/utils/wav'

/** A trip request is a sentence or two; stop on our own so a forgotten mic does not upload minutes of audio */
const MAX_RECORDING_MS = 30_000

export type VoiceError = 'unsupported' | 'denied' | 'empty' | 'unavailable' | 'failed'

/**
 * Record from the microphone, then Anir (oyu STT, through our backend) turns it into text.
 * ``toggle`` starts recording, and on the second press stops and hands the text to ``onText``.
 */
export function useVoiceInput(onText: (text: string) => void) {
  const api = useApi()
  const isListening = ref(false)
  const isTranscribing = ref(false)
  const error = ref<VoiceError | null>(null)

  let recorder: MediaRecorder | null = null
  let chunks: Blob[] = []
  let stopTimer: ReturnType<typeof setTimeout> | null = null

  async function start() {
    error.value = null
    if (!import.meta.client || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      error.value = 'unsupported'
      return
    }
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      error.value = 'denied'
      return
    }
    chunks = []
    recorder = new MediaRecorder(stream)
    recorder.ondataavailable = (event) => {
      if (event.data.size) chunks.push(event.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop())
      void transcribe(new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' }))
    }
    recorder.start()
    isListening.value = true
    stopTimer = setTimeout(stop, MAX_RECORDING_MS)
  }

  function stop() {
    if (stopTimer) clearTimeout(stopTimer)
    stopTimer = null
    isListening.value = false
    if (recorder?.state === 'recording') recorder.stop()
  }

  /** Drop a recording in progress without sending it */
  function cancel() {
    if (recorder) recorder.onstop = () => recorder?.stream.getTracks().forEach((track) => track.stop())
    stop()
  }

  async function transcribe(recording: Blob) {
    if (!recording.size) {
      error.value = 'empty'
      return
    }
    isTranscribing.value = true
    try {
      const form = new FormData()
      form.append('file', await toWav(recording), 'speech.wav')
      const { data, error: failure } = await api.post<{ text: string }>(API_ENDPOINTS.VOICE.TRANSCRIBE, form)
      if (failure) {
        error.value = failure.statusCode === 503 ? 'unavailable' : 'failed'
        return
      }
      const text = data?.text.trim() ?? ''
      if (!text) {
        error.value = 'empty'
        return
      }
      onText(text)
    } catch {
      // The browser could not decode its own recording
      error.value = 'failed'
    } finally {
      isTranscribing.value = false
    }
  }

  function toggle() {
    if (isTranscribing.value) return
    if (isListening.value) stop()
    else void start()
  }

  onScopeDispose(cancel)

  return { isListening, isTranscribing, error, toggle, cancel }
}
