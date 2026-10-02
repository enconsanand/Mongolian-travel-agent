import { API_ENDPOINTS } from '~/constants'

/** tsuurAI takes at most 800 characters a call; stay under it with room for trimming */
const MAX_CHARS = 780

export type SpeechError = 'unavailable' | 'failed'

/** Sentences packed into pieces tsuurAI accepts; a single over-long sentence is cut at a space */
export function speechChunks(texts: string[]): string[] {
  const chunks: string[] = []
  for (const text of texts) {
    let current = ''
    for (const sentence of text.trim().split(/(?<=[.!?…])\s+/u)) {
      let rest = sentence
      while (rest.length > MAX_CHARS) {
        const cut = rest.lastIndexOf(' ', MAX_CHARS)
        const at = cut > 0 ? cut : MAX_CHARS
        if (current) chunks.push(current)
        current = ''
        chunks.push(rest.slice(0, at).trim())
        rest = rest.slice(at).trim()
      }
      if (current && current.length + 1 + rest.length > MAX_CHARS) {
        chunks.push(current)
        current = rest
      } else current = current ? `${current} ${rest}` : rest
    }
    if (current.trim()) chunks.push(current.trim())
  }
  return chunks.filter(Boolean)
}

/**
 * Read Mongolian text aloud with tsuurAI (oyu TTS, through our backend), one piece after another.
 * The next piece is fetched while the current one plays.
 */
export function useSpeech() {
  const api = useApi()
  const speaking = ref(false)
  const loading = ref(false)
  const error = ref<SpeechError | null>(null)

  let audio: HTMLAudioElement | null = null
  let urls: string[] = []
  // Bumped by stop(), so a fetch or playback from an earlier run is dropped
  let run = 0

  async function fetchAudio(text: string): Promise<string | null> {
    const { data, error: failure } = await api.post<Blob>(API_ENDPOINTS.VOICE.SPEAK, { text }, { responseType: 'blob' })
    if (failure || !data) {
      error.value = failure?.statusCode === 503 ? 'unavailable' : 'failed'
      return null
    }
    const url = URL.createObjectURL(data)
    urls.push(url)
    return url
  }

  function play(url: string, seq: number): Promise<void> {
    return new Promise((resolve) => {
      if (seq !== run) return resolve()
      audio = new Audio(url)
      audio.onended = () => resolve()
      audio.onerror = () => resolve()
      audio.play().catch(() => {
        error.value = 'failed'
        resolve()
      })
    })
  }

  async function speak(texts: string[]) {
    stop()
    const seq = run
    const chunks = speechChunks(texts)
    if (!chunks.length) return
    error.value = null
    speaking.value = true
    loading.value = true
    let next = fetchAudio(chunks[0]!)
    for (let i = 0; i < chunks.length; i++) {
      const url = await next
      if (seq !== run) return
      loading.value = false
      if (!url) break
      if (i + 1 < chunks.length) next = fetchAudio(chunks[i + 1]!)
      await play(url, seq)
      if (seq !== run) return
    }
    stop()
  }

  function stop() {
    run++
    audio?.pause()
    audio = null
    urls.forEach((url) => URL.revokeObjectURL(url))
    urls = []
    speaking.value = false
    loading.value = false
  }

  function toggle(texts: string[]) {
    if (speaking.value) stop()
    else void speak(texts)
  }

  onScopeDispose(stop)

  return { speaking, loading, error, speak, stop, toggle }
}
