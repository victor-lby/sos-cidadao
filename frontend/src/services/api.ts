import { halClient } from './hal'
import type {
  Notification,
  NotificationFilters,
  PaginationResult,
  HalCollection,
  HalResource
} from '@/types'

export class NotificationApi {
  async list(
    filters: NotificationFilters = {},
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginationResult<Notification>> {
    const params: Record<string, string | number> = {
      page,
      pageSize
    }

    // Add filters to params
    if (filters.status) {
      params.status = filters.status
    }
    if (filters.severity !== undefined) {
      params.severity = filters.severity
    }
    if (filters.searchTerm) {
      params.search = filters.searchTerm
    }
    if (filters.dateRange) {
      params.startDate = filters.dateRange.start
      params.endDate = filters.dateRange.end
    }

    const response = await halClient.get<HalCollection<Notification>>('/notifications', params)

    return {
      items: (response._embedded?.items as Notification[]) || [],
      total: (response.total as number) || 0,
      page: (response.page as number) || 1,
      pageSize: (response.pageSize as number) || pageSize,
      links: halClient.extractLinks(response)
    }
  }

  async getById(id: string): Promise<Notification> {
    const response = await halClient.get<Notification>(`/notifications/${id}`)
    return {
      ...response,
      _links: halClient.extractLinks(response)
    } as Notification
  }

  async approve(id: string, targets: string[], categories?: string[]): Promise<Notification> {
    const data = {
      targets,
      ...(categories && { categories })
    }

    const response = await halClient.post<Notification>(`/notifications/${id}/approve`, data)
    return {
      ...response,
      _links: halClient.extractLinks(response)
    } as Notification
  }

  async deny(id: string, reason: string): Promise<Notification> {
    const data = { reason }

    const response = await halClient.post<Notification>(`/notifications/${id}/deny`, data)
    return {
      ...response,
      _links: halClient.extractLinks(response)
    } as Notification
  }

  // Helper method to extract available actions from HAL links
  getAvailableActions(notification: Notification): string[] {
    if (!notification._links) {
      return []
    }

    return halClient.extractAvailableActions(notification as unknown as HalResource)
  }

  // Helper method to check if a specific action is available
  canPerformAction(notification: Notification, action: string): boolean {
    const availableActions = this.getAvailableActions(notification)
    return availableActions.includes(action)
  }
}

interface Organization {
  id: string
  name: string
  type: string
  created_at: string
  updated_at: string
  _links: Record<string, HalLink>
}

export class OrganizationApi {
  async getCurrent(): Promise<Organization> {
    const response = await halClient.get('/organizations/current')
    return response as Organization
  }

  async getById(id: string): Promise<Organization> {
    const response = await halClient.get(`/organizations/${id}`)
    return response as Organization
  }
}

interface AuditLogEntry {
  id: string
  user_id: string
  entity: string
  entity_id: string
  action: string
  before: Record<string, unknown>
  after: Record<string, unknown>
  timestamp: string
  ip_address: string
  user_agent: string
  _links: Record<string, HalLink>
}

export class AuditApi {
  async list(
    filters: Record<string, unknown> = {},
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginationResult<AuditLogEntry>> {
    const params: Record<string, string | number> = {
      page,
      pageSize,
      ...filters
    }

    const response = await halClient.get<HalCollection<AuditLogEntry>>('/audit-logs', params)

    return {
      items: (response._embedded?.items as AuditLogEntry[]) || [],
      total: (response.total as number) || 0,
      page: (response.page as number) || 1,
      pageSize: (response.pageSize as number) || pageSize,
      links: halClient.extractLinks(response)
    }
  }

  async export(
    filters: Record<string, unknown> = {},
    format: 'csv' | 'json' = 'csv'
  ): Promise<Blob> {
    const params = { ...filters, format }
    
    // This would need to be implemented differently for file downloads
    const response = await halClient.get('/audit-logs/export', params)
    
    // Convert response to blob for download
    return new Blob([JSON.stringify(response)], { 
      type: format === 'csv' ? 'text/csv' : 'application/json' 
    })
  }
}

// Create singleton instances
export const notificationApi = new NotificationApi()
export const organizationApi = new OrganizationApi()
export const auditApi = new AuditApi()