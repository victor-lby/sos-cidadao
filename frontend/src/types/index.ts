// HAL (Hypertext Application Language) types
export interface HalLink {
  href: string
  method?: string
  type?: string
  title?: string
}

export interface HalResource<T = Record<string, unknown>> {
  _links: Record<string, HalLink>
  _embedded?: Record<string, unknown>
  [key: string]: unknown
}

export interface HalCollection<T> extends HalResource {
  _embedded: {
    items: T[]
  }
  total: number
  page: number
  pageSize: number
}

// Authentication types
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
  user: User
}

export interface RefreshTokenRequest {
  refreshToken: string
}

export interface RefreshTokenResponse {
  accessToken: string
  refreshToken: string
}

// User and Organization types
export interface User {
  id: string
  organizationId: string
  email: string
  name: string
  roles: string[]
  permissions: string[]
  createdAt: string
  updatedAt: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  createdAt: string
  updatedAt: string
}

// Notification types
export enum NotificationStatus {
  RECEIVED = 'received',
  APPROVED = 'approved',
  DENIED = 'denied',
  DISPATCHED = 'dispatched'
}

export interface Notification {
  id: string
  organizationId: string
  title: string
  body: string
  severity: number
  origin: string
  originalPayload: Record<string, unknown>
  baseTarget?: string
  targets: string[]
  categories: string[]
  status: NotificationStatus
  denialReason?: string
  createdAt: string
  updatedAt: string
  createdBy: string
  updatedBy: string
  _links?: Record<string, HalLink>
}

export interface NotificationFilters {
  status?: NotificationStatus
  severity?: number
  dateRange?: {
    start: string
    end: string
  }
  searchTerm?: string
}

// API Response types
export interface PaginationResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  links: Record<string, HalLink>
}

export interface ApiError {
  type: string
  title: string
  status: number
  detail: string
  instance: string
  errors?: Array<{
    field: string
    message: string
  }>
  _links?: Record<string, HalLink>
}

// User context for authentication
export interface UserContext {
  user: User | null
  organization: Organization | null
  permissions: string[]
  isAuthenticated: boolean
}