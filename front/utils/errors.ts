export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public data?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class AuthError extends ApiError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401)
    this.name = 'AuthError'
  }
}

export class ValidationError extends ApiError {
  constructor(
    message: string = 'Validation failed',
    public errors?: Record<string, string[]>
  ) {
    super(message, 400)
    this.name = 'ValidationError'
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network error occurred') {
    super(message)
    this.name = 'NetworkError'
  }
}
