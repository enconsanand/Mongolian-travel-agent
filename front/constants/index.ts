export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
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
  USERS: {
    LIST: '/users',
    CREATE: '/users',
    UPDATE: (id: string) => `/users/${id}`,
    DELETE: (id: string) => `/users/${id}`,
    GET: (id: string) => `/users/${id}`,
  },
} as const

export const COOKIE_NAMES = {
  AUTH_TOKEN: 'user-auth',
  USER_EMAIL: 'user-email',
} as const

export const HTTP_STATUS = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
} as const

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  FORBIDDEN: '/403',
} as const
