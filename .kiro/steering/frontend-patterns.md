# Frontend Coding Patterns & Rules

## ⚠️ MANDATORY PATTERNS - STRICT ENFORCEMENT

These patterns are **REQUIRED** for all frontend code. Deviations must be explicitly justified and approved.

## Vue 3 Composition API Patterns

### 1. Composition API Only (MANDATORY)
**RULE**: ALL components MUST use Composition API, NO Options API allowed.

```vue
<!-- ✅ CORRECT - Composition API -->
<template>
  <div>
    <h1>{{ notification.title }}</h1>
    <button @click="approveNotification" :disabled="isLoading">
      Approve
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'

interface Props {
  notificationId: string
}

const props = defineProps<Props>()
const notificationStore = useNotificationStore()

const isLoading = ref(false)
const notification = computed(() => 
  notificationStore.getNotificationById(props.notificationId)
)

const approveNotification = async () => {
  isLoading.value = true
  try {
    await notificationStore.approveNotification(props.notificationId)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  notificationStore.fetchNotification(props.notificationId)
})
</script>

<!-- ❌ WRONG - Options API (FORBIDDEN) -->
<script>
export default {
  data() {
    return {
      isLoading: false
    }
  },
  methods: {
    approveNotification() {
      // Don't use Options API
    }
  }
}
</script>
```

### 2. TypeScript Strict Mode (MANDATORY)
**RULE**: ALL components and composables MUST use strict TypeScript.

```typescript
// ✅ CORRECT - Strict TypeScript
interface NotificationListProps {
  organizationId: string
  status?: NotificationStatus
  pageSize?: number
}

interface NotificationListEmits {
  (event: 'notification-selected', notification: Notification): void
  (event: 'page-changed', page: number): void
}

const props = withDefaults(defineProps<NotificationListProps>(), {
  pageSize: 20
})

const emit = defineEmits<NotificationListEmits>()

// Typed reactive references
const notifications = ref<Notification[]>([])
const currentPage = ref<number>(1)
const isLoading = ref<boolean>(false)

// Typed computed properties
const totalPages = computed((): number => 
  Math.ceil(notificationStore.totalCount / props.pageSize)
)

// ❌ WRONG - Missing types
const props = defineProps(['organizationId', 'status'])  // No types
const notifications = ref([])  // No type annotation
const currentPage = ref(1)     // Inferred but not explicit

const totalPages = computed(() => {
  // No return type annotation
  return Math.ceil(store.totalCount / props.pageSize)
})
```

### 3. Composable Pattern for Logic Reuse
**RULE**: Reusable logic MUST be extracted into composables with proper typing.

```typescript
// ✅ CORRECT - Typed composable
// composables/useNotificationActions.ts
import { ref, computed } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import type { Notification, UserPermissions } from '@/types'

interface UseNotificationActionsReturn {
  isApproving: Readonly<Ref<boolean>>
  isDenying: Readonly<Ref<boolean>>
  canApprove: ComputedRef<boolean>
  canDeny: ComputedRef<boolean>
  approveNotification: (id: string, targets: string[]) => Promise<void>
  denyNotification: (id: string, reason: string) => Promise<void>
}

export function useNotificationActions(
  notification: ComputedRef<Notification | null>,
  userPermissions: ComputedRef<UserPermissions>
): UseNotificationActionsReturn {
  const notificationStore = useNotificationStore()
  
  const isApproving = ref(false)
  const isDenying = ref(false)
  
  const canApprove = computed(() => 
    notification.value?.status === 'received' && 
    userPermissions.value.includes('notification:approve')
  )
  
  const canDeny = computed(() =>
    notification.value?.status === 'received' && 
    userPermissions.value.includes('notification:deny')
  )
  
  const approveNotification = async (id: string, targets: string[]): Promise<void> => {
    isApproving.value = true
    try {
      await notificationStore.approveNotification(id, targets)
    } finally {
      isApproving.value = false
    }
  }
  
  const denyNotification = async (id: string, reason: string): Promise<void> => {
    isDenying.value = true
    try {
      await notificationStore.denyNotification(id, reason)
    } finally {
      isDenying.value = false
    }
  }
  
  return {
    isApproving: readonly(isApproving),
    isDenying: readonly(isDenying),
    canApprove,
    canDeny,
    approveNotification,
    denyNotification
  }
}

// ❌ WRONG - Untyped composable
export function useNotificationActions(notification, permissions) {
  // No types, no clear interface
  const isLoading = ref(false)
  
  const approve = async (id) => {
    // No type safety
  }
  
  return { isLoading, approve }  // No clear return type
}
```

## Pinia Store Patterns

### 4. Typed Pinia Stores (MANDATORY)
**RULE**: ALL stores MUST be fully typed with proper state, getters, and actions.

```typescript
// ✅ CORRECT - Typed Pinia store
// stores/notifications.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Notification, NotificationFilters, PaginationResult } from '@/types'
import { notificationApi } from '@/services/api'

interface NotificationState {
  notifications: Notification[]
  currentNotification: Notification | null
  isLoading: boolean
  error: string | null
  totalCount: number
  currentPage: number
}

export const useNotificationStore = defineStore('notifications', () => {
  // State
  const notifications = ref<Notification[]>([])
  const currentNotification = ref<Notification | null>(null)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const totalCount = ref<number>(0)
  const currentPage = ref<number>(1)
  
  // Getters
  const getNotificationById = computed(() => 
    (id: string): Notification | undefined => 
      notifications.value.find(n => n.id === id)
  )
  
  const pendingNotifications = computed((): Notification[] =>
    notifications.value.filter(n => n.status === 'received')
  )
  
  const hasNextPage = computed((): boolean =>
    currentPage.value * 20 < totalCount.value
  )
  
  // Actions
  const fetchNotifications = async (
    filters: NotificationFilters = {},
    page: number = 1
  ): Promise<void> => {
    isLoading.value = true
    error.value = null
    
    try {
      const result: PaginationResult<Notification> = await notificationApi.list(filters, page)
      notifications.value = result.items
      totalCount.value = result.total
      currentPage.value = page
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch notifications'
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  const approveNotification = async (
    id: string, 
    targets: string[]
  ): Promise<Notification> => {
    try {
      const approved = await notificationApi.approve(id, targets)
      
      // Update local state
      const index = notifications.value.findIndex(n => n.id === id)
      if (index !== -1) {
        notifications.value[index] = approved
      }
      
      if (currentNotification.value?.id === id) {
        currentNotification.value = approved
      }
      
      return approved
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to approve notification'
      throw err
    }
  }
  
  return {
    // State
    notifications: readonly(notifications),
    currentNotification: readonly(currentNotification),
    isLoading: readonly(isLoading),
    error: readonly(error),
    totalCount: readonly(totalCount),
    currentPage: readonly(currentPage),
    
    // Getters
    getNotificationById,
    pendingNotifications,
    hasNextPage,
    
    // Actions
    fetchNotifications,
    approveNotification
  }
})

// ❌ WRONG - Untyped store
export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([])  // No types
  const isLoading = ref(false)
  
  const fetchNotifications = async (filters) => {  // No parameter types
    // No error handling, no type safety
    const result = await api.get('/notifications')
    notifications.value = result.data
  }
  
  return { notifications, fetchNotifications }  // No readonly, no clear interface
})
```

### 5. HAL Response Handling (MANDATORY)
**RULE**: ALL API responses MUST be processed through HAL-aware utilities.

```typescript
// ✅ CORRECT - HAL-aware API service
// services/hal.ts
interface HalLink {
  href: string
  method?: string
  type?: string
}

interface HalResource<T = any> {
  _links: Record<string, HalLink>
  _embedded?: Record<string, any>
  [key: string]: any
}

interface HalCollection<T> extends HalResource {
  _embedded: {
    items: T[]
  }
  total: number
  page: number
  pageSize: number
}

export class HalClient {
  private baseUrl: string
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }
  
  async get<T>(url: string): Promise<HalResource<T>> {
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/hal+json',
        'Authorization': `Bearer ${this.getToken()}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  async post<T>(url: string, data: any): Promise<HalResource<T>> {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/hal+json',
        'Authorization': `Bearer ${this.getToken()}`
      },
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  extractLinks(resource: HalResource): Record<string, HalLink> {
    return resource._links || {}
  }
  
  hasLink(resource: HalResource, rel: string): boolean {
    return !!(resource._links && resource._links[rel])
  }
  
  getLink(resource: HalResource, rel: string): HalLink | null {
    return resource._links?.[rel] || null
  }
  
  private getToken(): string {
    // Get JWT token from auth store
    return useAuthStore().token || ''
  }
}

// services/notificationApi.ts
export class NotificationApi {
  private hal: HalClient
  
  constructor() {
    this.hal = new HalClient('/api')
  }
  
  async list(filters: NotificationFilters, page: number = 1): Promise<PaginationResult<Notification>> {
    const params = new URLSearchParams({
      page: page.toString(),
      ...filters
    })
    
    const response = await this.hal.get<HalCollection<Notification>>(`/notifications?${params}`)
    
    return {
      items: response._embedded?.items || [],
      total: response.total,
      page: response.page,
      pageSize: response.pageSize,
      links: this.hal.extractLinks(response)
    }
  }
  
  async approve(id: string, targets: string[]): Promise<Notification> {
    const response = await this.hal.post<Notification>(`/notifications/${id}/approve`, {
      targets
    })
    
    return {
      ...response,
      availableActions: this.extractAvailableActions(response)
    }
  }
  
  private extractAvailableActions(resource: HalResource): string[] {
    const actions: string[] = []
    const links = this.hal.extractLinks(resource)
    
    if (links.approve) actions.push('approve')
    if (links.deny) actions.push('deny')
    if (links.edit) actions.push('edit')
    
    return actions
  }
}

// ❌ WRONG - Plain HTTP without HAL awareness
export class NotificationApi {
  async list(filters) {
    // Missing HAL processing, no link extraction
    const response = await fetch('/api/notifications')
    return response.json()
  }
  
  async approve(id, targets) {
    // No HAL link following, hardcoded URLs
    const response = await fetch(`/api/notifications/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ targets })
    })
    return response.json()
  }
}
```

## Component Architecture Patterns

### 6. Component Composition (MANDATORY)
**RULE**: Components MUST follow single responsibility and composition patterns.

```vue
<!-- ✅ CORRECT - Composed components -->
<!-- NotificationCard.vue -->
<template>
  <v-card class="notification-card">
    <NotificationHeader 
      :notification="notification"
      :show-actions="showActions"
    />
    
    <NotificationContent 
      :title="notification.title"
      :body="notification.body"
      :severity="notification.severity"
    />
    
    <NotificationActions
      v-if="showActions"
      :notification="notification"
      :available-actions="availableActions"
      @approve="handleApprove"
      @deny="handleDeny"
    />
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Notification } from '@/types'
import NotificationHeader from './NotificationHeader.vue'
import NotificationContent from './NotificationContent.vue'
import NotificationActions from './NotificationActions.vue'

interface Props {
  notification: Notification
  showActions?: boolean
}

interface Emits {
  (event: 'approve', notification: Notification, targets: string[]): void
  (event: 'deny', notification: Notification, reason: string): void
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true
})

const emit = defineEmits<Emits>()

const availableActions = computed(() => 
  extractActionsFromHalLinks(props.notification._links)
)

const handleApprove = (targets: string[]) => {
  emit('approve', props.notification, targets)
}

const handleDeny = (reason: string) => {
  emit('deny', props.notification, reason)
}
</script>

<!-- ❌ WRONG - Monolithic component -->
<template>
  <v-card>
    <!-- Everything in one component - hard to maintain and test -->
    <v-card-title>{{ notification.title }}</v-card-title>
    <v-card-text>{{ notification.body }}</v-card-text>
    <v-card-actions>
      <v-btn @click="approve">Approve</v-btn>
      <v-btn @click="deny">Deny</v-btn>
      <!-- Lots of inline logic and UI mixed together -->
    </v-card-actions>
  </v-card>
</template>
```

### 7. Props and Emits Validation (MANDATORY)
**RULE**: ALL props and emits MUST be strictly typed and validated.

```typescript
// ✅ CORRECT - Strict prop and emit typing
interface NotificationListProps {
  organizationId: string
  filters?: NotificationFilters
  pageSize?: number
  selectable?: boolean
  multiSelect?: boolean
}

interface NotificationListEmits {
  (event: 'notification-selected', notification: Notification): void
  (event: 'notifications-selected', notifications: Notification[]): void
  (event: 'page-changed', page: number): void
  (event: 'filters-changed', filters: NotificationFilters): void
}

const props = withDefaults(defineProps<NotificationListProps>(), {
  pageSize: 20,
  selectable: false,
  multiSelect: false
})

const emit = defineEmits<NotificationListEmits>()

// Runtime validation for complex props
const filtersValidator = (filters: NotificationFilters): boolean => {
  if (filters.dateRange) {
    return filters.dateRange.start <= filters.dateRange.end
  }
  return true
}

// ❌ WRONG - Loose prop typing
const props = defineProps({
  organizationId: String,  // Should be required
  filters: Object,         // No type safety
  pageSize: {
    type: Number,
    default: 20
  }
})

const emit = defineEmits(['selected', 'changed'])  // No type information
```

## State Management Patterns

### 8. Reactive State Patterns (MANDATORY)
**RULE**: State updates MUST be reactive and follow Vue's reactivity principles.

```typescript
// ✅ CORRECT - Proper reactive state management
const useNotificationFilters = () => {
  const filters = reactive<NotificationFilters>({
    status: null,
    severity: null,
    dateRange: null,
    searchTerm: ''
  })
  
  const activeFiltersCount = computed(() => {
    let count = 0
    if (filters.status) count++
    if (filters.severity !== null) count++
    if (filters.dateRange) count++
    if (filters.searchTerm.trim()) count++
    return count
  })
  
  const clearFilters = () => {
    Object.assign(filters, {
      status: null,
      severity: null,
      dateRange: null,
      searchTerm: ''
    })
  }
  
  const updateFilter = <K extends keyof NotificationFilters>(
    key: K, 
    value: NotificationFilters[K]
  ) => {
    filters[key] = value
  }
  
  return {
    filters: readonly(filters),
    activeFiltersCount,
    clearFilters,
    updateFilter
  }
}

// ❌ WRONG - Non-reactive state updates
const useNotificationFilters = () => {
  let filters = {  // Not reactive
    status: null,
    severity: null
  }
  
  const updateFilter = (key, value) => {
    filters[key] = value  // Won't trigger reactivity
    // Missing type safety
  }
  
  return { filters, updateFilter }
}
```

### 9. Error Handling Patterns (MANDATORY)
**RULE**: ALL async operations MUST have proper error handling with user feedback.

```vue
<!-- ✅ CORRECT - Comprehensive error handling -->
<template>
  <div>
    <v-alert
      v-if="error"
      type="error"
      dismissible
      @click:close="clearError"
    >
      {{ error.message }}
      <template v-if="error.retryable" #append>
        <v-btn
          size="small"
          variant="outlined"
          @click="retryLastAction"
        >
          Retry
        </v-btn>
      </template>
    </v-alert>
    
    <NotificationList
      :loading="isLoading"
      :notifications="notifications"
      @approve="handleApprove"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useErrorHandler } from '@/composables/useErrorHandler'
import { useNotificationStore } from '@/stores/notifications'

const notificationStore = useNotificationStore()
const { error, isLoading, handleAsyncAction, clearError, retryLastAction } = useErrorHandler()

const notifications = computed(() => notificationStore.notifications)

const handleApprove = async (notification: Notification, targets: string[]) => {
  await handleAsyncAction(
    () => notificationStore.approveNotification(notification.id, targets),
    {
      successMessage: `Notification "${notification.title}" approved successfully`,
      errorMessage: 'Failed to approve notification',
      retryable: true
    }
  )
}

// composables/useErrorHandler.ts
interface ErrorHandlerOptions {
  successMessage?: string
  errorMessage?: string
  retryable?: boolean
}

interface AppError {
  message: string
  retryable: boolean
  originalError?: Error
}

export function useErrorHandler() {
  const error = ref<AppError | null>(null)
  const isLoading = ref(false)
  const lastAction = ref<(() => Promise<any>) | null>(null)
  
  const handleAsyncAction = async <T>(
    action: () => Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | null> => {
    isLoading.value = true
    error.value = null
    lastAction.value = options.retryable ? action : null
    
    try {
      const result = await action()
      
      if (options.successMessage) {
        // Show success toast
        useToast().success(options.successMessage)
      }
      
      return result
    } catch (err) {
      const errorMessage = options.errorMessage || 
        (err instanceof Error ? err.message : 'An unexpected error occurred')
      
      error.value = {
        message: errorMessage,
        retryable: options.retryable || false,
        originalError: err instanceof Error ? err : undefined
      }
      
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  const clearError = () => {
    error.value = null
  }
  
  const retryLastAction = async () => {
    if (lastAction.value) {
      await handleAsyncAction(lastAction.value, { retryable: true })
    }
  }
  
  return {
    error: readonly(error),
    isLoading: readonly(isLoading),
    handleAsyncAction,
    clearError,
    retryLastAction
  }
}

// ❌ WRONG - Poor error handling
const handleApprove = async (notification, targets) => {
  try {
    await store.approveNotification(notification.id, targets)
    // No success feedback
  } catch (err) {
    console.error(err)  // Only console logging
    // No user feedback, no retry mechanism
  }
}
```

### 10. Performance Optimization Patterns (MANDATORY)
**RULE**: Components MUST implement proper performance optimizations.

```vue
<!-- ✅ CORRECT - Performance optimized -->
<template>
  <div>
    <!-- Virtual scrolling for large lists -->
    <VirtualList
      :items="notifications"
      :item-height="120"
      :buffer="5"
      v-slot="{ item, index }"
    >
      <NotificationCard
        :key="item.id"
        :notification="item"
        @approve="handleApprove"
      />
    </VirtualList>
  </div>
</template>

<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { debounce } from 'lodash-es'

// Debounced search
const debouncedSearch = debounce((searchTerm: string) => {
  notificationStore.searchNotifications(searchTerm)
}, 300)

// Memoized computed properties
const filteredNotifications = computed(() => {
  return notificationStore.notifications.filter(notification => {
    if (filters.status && notification.status !== filters.status) return false
    if (filters.severity !== null && notification.severity !== filters.severity) return false
    return true
  })
})

// Lazy loading with intersection observer
const { isIntersecting, targetRef } = useIntersectionObserver()

watchEffect(() => {
  if (isIntersecting.value && notificationStore.hasNextPage) {
    notificationStore.loadNextPage()
  }
})

// ❌ WRONG - Performance issues
<template>
  <div>
    <!-- Rendering all items without virtualization -->
    <div v-for="notification in allNotifications" :key="notification.id">
      <!-- Expensive operations in template -->
      <NotificationCard 
        :notification="notification"
        :formatted-date="formatDate(notification.createdAt)"
        :can-approve="checkPermissions(notification, user)"
      />
    </div>
  </div>
</template>

<script setup>
// No debouncing, immediate API calls
watch(searchTerm, (newTerm) => {
  api.search(newTerm)  // Called on every keystroke
})

// Expensive computed without memoization
const processedNotifications = computed(() => {
  return notifications.value.map(n => ({
    ...n,
    // Expensive operation on every render
    formattedContent: expensiveFormatting(n.content)
  }))
})
</script>
```

These patterns are **NON-NEGOTIABLE** and must be followed in all frontend code. Any deviations require explicit architectural review and approval.