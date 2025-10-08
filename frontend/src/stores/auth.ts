import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import { authService } from '@/services/auth'
import type { User, Organization, LoginRequest, UserContext } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const organization = ref<Organization | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => user.value !== null)
  
  const permissions = computed(() => user.value?.permissions || [])
  
  const userContext = computed((): UserContext => ({
    user: user.value,
    organization: organization.value,
    permissions: permissions.value,
    isAuthenticated: isAuthenticated.value
  }))

  const hasPermission = computed(() => (permission: string): boolean => {
    return permissions.value.includes(permission)
  })

  const hasAnyPermission = computed(() => (requiredPermissions: string[]): boolean => {
    return requiredPermissions.some(permission => permissions.value.includes(permission))
  })

  const hasAllPermissions = computed(() => (requiredPermissions: string[]): boolean => {
    return requiredPermissions.every(permission => permissions.value.includes(permission))
  })

  // Actions
  const login = async (credentials: LoginRequest): Promise<void> => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authService.login(credentials)
      user.value = response.user
      
      // Fetch organization data if not included in login response
      if (response.user.organizationId && !organization.value) {
        await fetchOrganization()
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Login failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const logout = async (): Promise<void> => {
    isLoading.value = true
    error.value = null

    try {
      await authService.logout()
    } catch (err) {
      console.warn('Logout error:', err)
    } finally {
      user.value = null
      organization.value = null
      isLoading.value = false
    }
  }

  const refreshToken = async (): Promise<boolean> => {
    try {
      const response = await authService.refreshToken()
      return response !== null
    } catch (err) {
      console.warn('Token refresh failed:', err)
      await logout()
      return false
    }
  }

  const fetchCurrentUser = async (): Promise<void> => {
    if (!authService.isAuthenticated()) {
      return
    }

    isLoading.value = true
    error.value = null

    try {
      const currentUser = await authService.getCurrentUser()
      if (currentUser) {
        user.value = currentUser
        
        if (currentUser.organizationId && !organization.value) {
          await fetchOrganization()
        }
      } else {
        // User fetch failed, clear state
        user.value = null
        organization.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch user'
      user.value = null
      organization.value = null
    } finally {
      isLoading.value = false
    }
  }

  const fetchOrganization = async (): Promise<void> => {
    if (!user.value?.organizationId) {
      return
    }

    try {
      // This will be implemented when we create the organization API
      // const org = await organizationApi.getById(user.value.organizationId)
      // organization.value = org
      
      // For now, create a mock organization
      organization.value = {
        id: user.value.organizationId,
        name: 'Mock Organization',
        slug: 'mock-org',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    } catch (err) {
      console.warn('Failed to fetch organization:', err)
    }
  }

  const initialize = async (): Promise<void> => {
    // Check if user is already authenticated
    if (authService.isAuthenticated()) {
      await fetchCurrentUser()
    }

    // Setup automatic token refresh
    authService.setupTokenRefresh()

    // Listen for unauthorized events from HAL client
    window.addEventListener('auth:unauthorized', () => {
      logout()
    })
  }

  const clearError = (): void => {
    error.value = null
  }

  // Check specific permissions
  const canApproveNotifications = computed(() => 
    hasPermission.value('notification:approve')
  )

  const canDenyNotifications = computed(() => 
    hasPermission.value('notification:deny')
  )

  const canManageUsers = computed(() => 
    hasPermission.value('user:manage')
  )

  const canManageOrganization = computed(() => 
    hasPermission.value('organization:manage')
  )

  const canViewAuditLogs = computed(() => 
    hasPermission.value('audit:view')
  )

  return {
    // State
    user: readonly(user),
    organization: readonly(organization),
    isLoading: readonly(isLoading),
    error: readonly(error),

    // Getters
    isAuthenticated,
    permissions,
    userContext,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,

    // Permission checks
    canApproveNotifications,
    canDenyNotifications,
    canManageUsers,
    canManageOrganization,
    canViewAuditLogs,

    // Actions
    login,
    logout,
    refreshToken,
    fetchCurrentUser,
    fetchOrganization,
    initialize,
    clearError
  }
})