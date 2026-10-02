export interface LatLng {
  lat: number
  lng: number
}

export interface RouteLeg {
  durationSec: number
  distanceM: number
  /** Google had no road for this leg (e.g. a stop in a lake or off-road), so it is a straight line */
  straight?: boolean
}

/** Driving time and distance between two consecutive stops, keyed `${fromPlaceId}>${toPlaceId}` */
export type StopLegs = Record<string, RouteLeg>

export interface DrivingRoute {
  path: LatLng[]
  /** One leg between each pair of consecutive points */
  legs: RouteLeg[]
  durationSec: number
  distanceM: number
}

const ROUTES_URL = 'https://routes.googleapis.com/directions/v2:computeRoutes'
const FIELDS =
  'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.duration,routes.legs.distanceMeters'
/** The Routes API takes at most 25 stops between origin and destination */
const MAX_INTERMEDIATES = 25

const seconds = (duration?: string) => Number.parseInt(duration ?? '0', 10) || 0
const waypoint = ({ lat, lng }: LatLng) => ({ location: { latLng: { latitude: lat, longitude: lng } } })

/** Google's encoded polyline format to points (https://developers.google.com/maps/documentation/utilities/polylinealgorithm) */
export function decodePolyline(encoded: string): LatLng[] {
  const points: LatLng[] = []
  let index = 0
  let lat = 0
  let lng = 0
  while (index < encoded.length) {
    for (const axis of ['lat', 'lng'] as const) {
      let shift = 0
      let result = 0
      let byte: number
      do {
        byte = encoded.charCodeAt(index++) - 63
        result |= (byte & 0x1f) << shift
        shift += 5
      } while (byte >= 0x20)
      const delta = result & 1 ? ~(result >> 1) : result >> 1
      if (axis === 'lat') lat += delta
      else lng += delta
    }
    points.push({ lat: lat / 1e5, lng: lng / 1e5 })
  }
  return points
}

/** Straight-line kilometres between two points (haversine) */
function kmBetween(a: LatLng, b: LatLng): number {
  const rad = Math.PI / 180
  const h =
    Math.sin(((b.lat - a.lat) * rad) / 2) ** 2 +
    Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(((b.lng - a.lng) * rad) / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}

/**
 * The driving route through the points in order: one request for the whole trip, and when Google cannot route it
 * all (one stop off any road is enough), each leg on its own, so only the legs without a road are drawn straight.
 * Resolves to null when no leg has a road (or the key may not use the Routes API).
 */
export async function fetchDrivingRoute(apiKey: string, points: LatLng[]): Promise<DrivingRoute | null> {
  const key = points.map(({ lat, lng }) => `${lat.toFixed(4)},${lng.toFixed(4)}`).join(';')
  const cached = cache.get(key)
  if (cached !== undefined) return cached
  const route = await routeThrough(apiKey, points)
  cache.set(key, route)
  return route
}

// The same stops are drawn again on every theme switch and plan version; asking once saves the daily quota
const cache = new Map<string, DrivingRoute | null>()

/** Google first, then OpenStreetMap (OSRM): Google's free daily quota runs out, and some roads only OSM knows */
async function anyRoute(apiKey: string, points: LatLng[]): Promise<DrivingRoute | null> {
  return (await fetchRoute(apiKey, points)) ?? (await fetchOsrmRoute(points))
}

async function routeThrough(apiKey: string, points: LatLng[]): Promise<DrivingRoute | null> {
  const whole = await anyRoute(apiKey, points)
  if (whole || points.length < 3) return whole

  const legs = await Promise.all(points.slice(1).map((to, i) => anyRoute(apiKey, [points[i]!, to])))
  if (legs.every((leg) => !leg)) return null
  const route: DrivingRoute = { path: [], legs: [], durationSec: 0, distanceM: 0 }
  legs.forEach((leg, i) => {
    const [from, to] = [points[i]!, points[i + 1]!]
    route.path.push(...(leg?.path ?? [from, to]))
    const part = leg?.legs[0] ?? { durationSec: 0, distanceM: Math.round(kmBetween(from, to) * 1000), straight: true }
    route.legs.push(part)
    route.durationSec += part.durationSec
    route.distanceM += part.distanceM
  })
  return route
}

/** One Routes API request through the points in order; null when Google has no road route for all of it */
async function fetchRoute(apiKey: string, points: LatLng[]): Promise<DrivingRoute | null> {
  if (points.length < 2 || points.length - 2 > MAX_INTERMEDIATES) return null
  try {
    const response = await fetch(ROUTES_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': apiKey, 'X-Goog-FieldMask': FIELDS },
      body: JSON.stringify({
        origin: waypoint(points[0]!),
        destination: waypoint(points.at(-1)!),
        intermediates: points.slice(1, -1).map(waypoint),
        travelMode: 'DRIVE',
      }),
    })
    if (!response.ok) return null
    const route = (await response.json()).routes?.[0]
    if (!route?.polyline?.encodedPolyline) return null
    return {
      path: decodePolyline(route.polyline.encodedPolyline),
      legs: (route.legs ?? []).map((leg: { duration?: string; distanceMeters?: number }) => ({
        durationSec: seconds(leg.duration),
        distanceM: leg.distanceMeters ?? 0,
      })),
      durationSec: seconds(route.duration),
      distanceM: route.distanceMeters ?? 0,
    }
  } catch {
    return null
  }
}

const OSRM_URL = 'https://router.project-osrm.org/route/v1/driving'

/** The OpenStreetMap router (OSRM demo server: fine for a demo, not for production traffic) */
async function fetchOsrmRoute(points: LatLng[]): Promise<DrivingRoute | null> {
  if (points.length < 2) return null
  const coords = points.map(({ lat, lng }) => `${lng},${lat}`).join(';')
  try {
    const response = await fetch(`${OSRM_URL}/${coords}?overview=full&geometries=polyline`)
    if (!response.ok) return null
    const data = await response.json()
    const route = data.code === 'Ok' ? data.routes?.[0] : null
    if (!route?.geometry) return null
    return {
      path: decodePolyline(route.geometry),
      legs: (route.legs ?? []).map((leg: { duration: number; distance: number }) => ({
        durationSec: Math.round(leg.duration),
        distanceM: Math.round(leg.distance),
      })),
      durationSec: Math.round(route.duration),
      distanceM: Math.round(route.distance),
    }
  } catch {
    return null
  }
}
