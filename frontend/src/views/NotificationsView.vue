<template>
  <div class="notifications">
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4 font-weight-bold">Notifications</h1>
      
      <!-- Filter Chips -->
      <div class="d-flex gap-2">
        <v-chip
          :color="selectedStatus === null ? 'primary' : 'default'"
          :variant="selectedStatus === null ? 'flat' : 'outlined'"
          @click="filterByStatus(null)"
        >
          All ({{ stats.total }})
        </v-chip>
        <v-chip
          :color="selectedStatus === 'received' ? 'warning' : 'default'"
          :variant="selectedStatus === 'received' ? 'flat' : 'outlined'"
          @click="filterByStatus('received')"
        >
          Pending ({{ stats.pending }})
        </v-chip>
        <v-chip
          :color="selectedStatus === 'approved' ? 'success' : 'default'"
          :variant="selectedStatus === 'approved' ? 'flat' : 'outlined'"
          @click="filterByStatus('approved')"
        >
          Approved ({{ stats.approved }})
        </v-chip>
        <v-chip
          :color="selectedStatus === 'denied' ? 'error' : 'default'"
          :variant="selectedStatus === 'denied' ? 'flat' : 'outlined'"
          @click="filterByStatus('denied')"
        >
          Denied ({{ stats.denied }})
        </v-chip>
      </div>
    </div>

    <!-- Loading State -->
    <v-card v-if="loading" class="mb-4">
      <v-card-text class="text-center py-8">
        <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
        <p class="mt-4">Loading notifications...</p>
      </v-card-text>
    </v-card>

    <!-- Error State -->
    <v-alert v-if="error" type="error" class="mb-4" dismissible @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- Empty State -->
    <v-card v-if="!loading && notifications.length === 0" class="mb-4">
      <v-card-text class="text-center py-12">
        <v-icon size="64" color="grey-lighten-1">mdi-bell-off</v-icon>
        <p class="text-h6 mt-4">No notifications found</p>
        <p class="text-body-2 text-medium-emphasis">
          {{ selectedStatus ? `No ${selectedStatus} notifications at the moment.` : 'No notifications have been created yet.' }}
        </p>
      </v-card-text>
    </v-card>

    <!-- Notifications List -->
    <div v-if="!loading && notifications.length > 0">
      <v-card
        v-for="notification in notifications"
        :key="notification.id"
        class="mb-4"
        :class="getNotificationCardClass(notification.status)"
      >
        <v-card-text>
          <div class="d-flex justify-space-between align-start mb-3">
            <div class="flex-grow-1">
              <h3 class="text-h6 font-weight-bold mb-2">{{ notification.title }}</h3>
              <p class="text-body-1 mb-3">{{ notification.body }}</p>
              
              <div class="d-flex align-center gap-4 text-caption text-medium-emphasis">
                <span>
                  <v-icon size="small" class="mr-1">mdi-source-branch</v-icon>
                  {{ notification.origin }}
                </span>
                <span>
                  <v-icon size="small" class="mr-1">mdi-clock</v-icon>
                  {{ formatDate(notification.created_at) }}
                </span>
                <span>
                  <v-icon size="small" class="mr-1">mdi-alert</v-icon>
                  Severity {{ notification.severity }}
                </span>
              </div>
            </div>
            
            <div class="d-flex flex-column align-end gap-2">
              <!-- Status Chip -->
              <v-chip
                :color="getStatusColor(notification.status)"
                size="small"
                variant="flat"
              >
                {{ getStatusText(notification.status) }}
              </v-chip>
              
              <!-- Action Buttons -->
              <div v-if="notification._links" class="d-flex gap-2">
                <v-btn
                  v-if="notification._links.approve"
                  color="success"
                  size="small"
                  variant="outlined"
                  @click="approveNotification(notification)"
                >
                  <v-icon start>mdi-check</v-icon>
                  Approve
                </v-btn>
                
                <v-btn
                  v-if="notification._links.deny"
                  color="error"
                  size="small"
                  variant="outlined"
                  @click="denyNotification(notification)"
                >
                  <v-icon start>mdi-close</v-icon>
                  Deny
                </v-btn>
                
                <v-btn
                  v-if="notification._links.self"
                  color="primary"
                  size="small"
                  variant="text"
                  @click="viewDetails(notification)"
                >
                  <v-icon start>mdi-eye</v-icon>
                  Details
                </v-btn>
              </div>
            </div>
          </div>
          
          <!-- Additional Info for Denied/Approved -->
          <v-alert
            v-if="notification.denial_reason"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <strong>Denial Reason:</strong> {{ notification.denial_reason }}
          </v-alert>
          
          <v-alert
            v-if="notification.status === 'approved' && notification.approved_by"
            type="success"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <strong>Approved by:</strong> {{ notification.approved_by }}
            <span v-if="notification.approved_at"> on {{ formatDate(notification.approved_at) }}</span>
          </v-alert>
        </v-card-text>
      </v-card>
    </div>

    <!-- Pagination -->
    <v-pagination
      v-if="totalPages > 1"
      v-model="currentPage"
      :length="totalPages"
      class="mt-6"
      @update:model-value="loadNotifications"
    ></v-pagination>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { HalClient } from '@/services/hal'

const router = useRouter()
const halClient = new HalClient()

// Reactive state
const notifications = ref([])
const loading = ref(false)
const error = ref(null)
const selectedStatus = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 20

// Stats
const stats = reactive({
  total: 0,
  pending: 0,
  approved: 0,
  denied: 0
})

// Computed
const filteredNotifications = computed(() => {
  if (!selectedStatus.value) return notifications.value
  return notifications.value.filter(n => n.status === selectedStatus.value)
})

// Methods
const loadNotifications = async () => {
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      size: pageSize.toString()
    })
    
    if (selectedStatus.value) {
      params.append('status', selectedStatus.value)
    }
    
    const response = await halClient.get(`/notifications?${params}`)
    
    notifications.value = response._embedded?.notifications || []
    totalPages.value = response.total_pages || 1
    
    // Update stats
    updateStats()
    
  } catch (err) {
    error.value = err.message || 'Failed to load notifications'
    console.error('Error loading notifications:', err)
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  stats.total = notifications.value.length
  stats.pending = notifications.value.filter(n => n.status === 'received').length
  stats.approved = notifications.value.filter(n => n.status === 'approved').length
  stats.denied = notifications.value.filter(n => n.status === 'denied').length
}

const filterByStatus = (status) => {
  selectedStatus.value = status
  currentPage.value = 1
  loadNotifications()
}

const approveNotification = async (notification) => {
  try {
    loading.value = true
    
    // For now, just approve with the existing targets and categories
    const approvalData = {
      target_ids: notification.target_ids || [],
      category_ids: notification.category_ids || []
    }
    
    await halClient.post(notification._links.approve.href, approvalData)
    
    // Reload notifications
    await loadNotifications()
    
  } catch (err) {
    error.value = err.message || 'Failed to approve notification'
  } finally {
    loading.value = false
  }
}

const denyNotification = async (notification) => {
  const reason = prompt('Please provide a reason for denial:')
  if (!reason) return
  
  try {
    loading.value = true
    
    const denialData = {
      reason: reason
    }
    
    await halClient.post(notification._links.deny.href, denialData)
    
    // Reload notifications
    await loadNotifications()
    
  } catch (err) {
    error.value = err.message || 'Failed to deny notification'
  } finally {
    loading.value = false
  }
}

const viewDetails = (notification) => {
  router.push({ name: 'notification-detail', params: { id: notification.id } })
}

const getStatusColor = (status) => {
  switch (status) {
    case 'received': return 'warning'
    case 'approved': return 'success'
    case 'denied': return 'error'
    case 'dispatched': return 'info'
    default: return 'default'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'received': return 'Pending Review'
    case 'approved': return 'Approved'
    case 'denied': return 'Denied'
    case 'dispatched': return 'Dispatched'
    default: return status
  }
}

const getNotificationCardClass = (status) => {
  switch (status) {
    case 'received': return 'border-l-warning'
    case 'approved': return 'border-l-success'
    case 'denied': return 'border-l-error'
    case 'dispatched': return 'border-l-info'
    default: return ''
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString()
}

// Lifecycle
onMounted(() => {
  loadNotifications()
})
</script>

<style scoped>
.border-l-warning {
  border-left: 4px solid rgb(var(--v-theme-warning));
}

.border-l-success {
  border-left: 4px solid rgb(var(--v-theme-success));
}

.border-l-error {
  border-left: 4px solid rgb(var(--v-theme-error));
}

.border-l-info {
  border-left: 4px solid rgb(var(--v-theme-info));
}
</style>