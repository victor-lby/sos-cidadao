import axios, { type AxiosInstance, type AxiosResponse, type AxiosError } from 'axios'
import type { HalResource, HalLink, ApiError } from '@/types'

export class HalClient {
  private client: AxiosInstance
  private baseUrl: string

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/hal+json'
      },
      timeout: 30000
    })

    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      config => {
        const token = this.getAuthToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      error => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      response => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid - trigger logout
          this.handleUnauthorized()
        }
        return Promise.reject(this.transformError(error))
      }
    )
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('accessToken')
  }

  private handleUnauthorized(): void {
    // Clear tokens and redirect to login
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
    
    // Dispatch custom event for auth store to handle
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }

  private transformError(error: AxiosError): ApiError {
    if (error.response?.data) {
      return error.response.data as ApiError
    }

    return {
      type: 'about:blank',
      title: 'Network Error',
      status: error.response?.status || 0,
      detail: error.message || 'An unexpected error occurred',
      instance: error.config?.url || ''
    }
  }

  async get<T>(url: string, params?: Record<string, unknown>): Promise<T & HalResource> {
    const response: AxiosResponse<T & HalResource> = await this.client.get(url, { params })
    return response.data
  }

  async post<T>(
    url: string,
    data?: Record<string, unknown>
  ): Promise<T & HalResource> {
    const response: AxiosResponse<T & HalResource> = await this.client.post(url, data)
    return response.data
  }

  async put<T>(
    url: string,
    data?: Record<string, unknown>
  ): Promise<T & HalResource> {
    const response: AxiosResponse<T & HalResource> = await this.client.put(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T & HalResource> {
    const response: AxiosResponse<T & HalResource> = await this.client.delete(url)
    return response.data
  }

  // HAL-specific methods
  extractLinks(resource: HalResource): Record<string, HalLink> {
    return resource._links || {}
  }

  hasLink(resource: HalResource, rel: string): boolean {
    return !!(resource._links && resource._links[rel])
  }

  getLink(resource: HalResource, rel: string): HalLink | null {
    return resource._links?.[rel] || null
  }

  getLinkHref(resource: HalResource, rel: string): string | null {
    const link = this.getLink(resource, rel)
    return link?.href || null
  }

  async followLink<T>(
    resource: HalResource,
    rel: string,
    data?: Record<string, unknown>
  ): Promise<T & HalResource | null> {
    const link = this.getLink(resource, rel)
    if (!link) {
      return null
    }

    const method = (link.method || 'GET').toUpperCase()
    const url = link.href

    switch (method) {
      case 'GET':
        return this.get<T>(url)
      case 'POST':
        return this.post<T>(url, data)
      case 'PUT':
        return this.put<T>(url, data)
      case 'DELETE':
        return this.delete<T>(url)
      default:
        throw new Error(`Unsupported HTTP method: ${method}`)
    }
  }

  extractAvailableActions(resource: HalResource): string[] {
    const actions: string[] = []
    const links = this.extractLinks(resource)

    // Common action mappings
    const actionMappings: Record<string, string> = {
      approve: 'approve',
      deny: 'deny',
      edit: 'edit',
      delete: 'delete',
      update: 'update',
      create: 'create'
    }

    Object.keys(links).forEach(rel => {
      if (actionMappings[rel]) {
        actions.push(actionMappings[rel])
      }
    })

    return actions
  }

  // Utility method to build URLs
  buildUrl(path: string, params?: Record<string, string | number>): string {
    let url = `${this.baseUrl}${path}`

    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value))
      })
      url += `?${searchParams.toString()}`
    }

    return url
  }
}

// Create a singleton instance
export const halClient = new HalClient()