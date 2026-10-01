/** Anir takes WAV/MP3/OGG; browsers record WebM or MP4, so recordings are re-encoded as 16 kHz mono PCM WAV */
const SAMPLE_RATE = 16_000

export async function toWav(recording: Blob): Promise<Blob> {
  const decoder = new AudioContext()
  let decoded: AudioBuffer
  try {
    decoded = await decoder.decodeAudioData(await recording.arrayBuffer())
  } finally {
    void decoder.close()
  }

  const frames = Math.max(1, Math.ceil(decoded.duration * SAMPLE_RATE))
  const offline = new OfflineAudioContext(1, frames, SAMPLE_RATE)
  const source = offline.createBufferSource()
  source.buffer = decoded
  source.connect(offline.destination)
  source.start()
  const samples = (await offline.startRendering()).getChannelData(0)
  return encodePcm16(samples, SAMPLE_RATE)
}

function encodePcm16(samples: Float32Array, sampleRate: number): Blob {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2))
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i))
  }
  text(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  text(8, 'WAVE')
  text(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  text(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((sample, i) => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return new Blob([view], { type: 'audio/wav' })
}
