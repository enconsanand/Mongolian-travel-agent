export const API_ENDPOINTS = {
  AUTH: {
    LOGOUT: '/auth/logout',
  },
  PAYMENTS: {
    KEYS: '/me/keys',
    MERCHANT_JWKS: '/merchant/jwks',
    PAY: (checkoutId: string) => `/me/checkouts/${checkoutId}/pay`,
  },
  BOOKINGS: {
    CREATE_CHECKOUT: (tripId: string) => `/me/trips/${tripId}/checkouts`,
    CHECKOUT: (checkoutId: string) => `/me/checkouts/${checkoutId}`,
  },
  TRAVEL: {
    MY_TRIPS: '/me/trips',
    STAYS: '/stays',
    EVENTS: '/events',
    PLACES: '/places',
    SCHEDULES: '/transport/schedules',
  },
  PLANNER: {
    PROPOSALS: '/planner/proposals',
    READ: '/planner/read',
    PROPOSAL: (id: string) => `/planner/proposals/${id}`,
    REVISE: (id: string) => `/planner/proposals/${id}/revise`,
    NIGHTS: (id: string) => `/planner/proposals/${id}/nights`,
    STAY: (id: string) => `/planner/proposals/${id}/stay`,
    STAYS: (id: string) => `/planner/proposals/${id}/stays`,
    ACCEPT: (id: string) => `/me/planner/proposals/${id}/accept`,
  },
  VOICE: {
    TRANSCRIBE: '/voice/transcribe',
    SPEAK: '/voice/speak',
    TRANSLATE: '/translate',
  },
} as const

export const COOKIE_NAMES = {
  AUTH_TOKEN: 'user-auth',
  USER_EMAIL: 'user-email',
} as const

export const HTTP_STATUS = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
} as const

export const ROUTES = {
  LOGIN: '/login',
  FORBIDDEN: '/403',
} as const
