/** The Maps JavaScript API namespace and the objects it makes (the API ships no types without @types/google.maps) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- untyped third-party global, kept to this one alias
export type GoogleMaps = any

let loading: Promise<GoogleMaps> | null = null

/**
 * Loads the Maps JavaScript API once per page and resolves to `google.maps`. Resolves to null without a key, so
 * the page can show its fallback instead of a broken map.
 */
export function useGoogleMaps(): Promise<GoogleMaps | null> {
  const apiKey = useRuntimeConfig().public.googleMapsApiKey as string
  if (!apiKey || import.meta.server) return Promise.resolve(null)
  const win = window as unknown as { google?: { maps?: GoogleMaps }; __nomadRouteMapsReady?: () => void }
  if (win.google?.maps) return Promise.resolve(win.google.maps)

  loading ??= new Promise<GoogleMaps>((resolve, reject) => {
    win.__nomadRouteMapsReady = () => resolve(win.google!.maps)
    const script = document.createElement('script')
    const params = new URLSearchParams({
      key: apiKey,
      v: 'weekly',
      loading: 'async',
      callback: '__nomadRouteMapsReady',
    })
    script.src = `https://maps.googleapis.com/maps/api/js?${params}`
    script.async = true
    script.onerror = () => {
      loading = null
      reject(new Error('Google Maps failed to load'))
    }
    document.head.appendChild(script)
  })
  return loading
}
