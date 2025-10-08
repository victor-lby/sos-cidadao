<template>
  <div class="dashboard">
    <!-- Welcome Header -->
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold mb-2">
        Welcome back, {{ user?.name || 'User' }}!
      </h1>
      <p class="text-subtitle-1 text-medium-emphasis">
        {{ organization?.name || 'Organization' }} Dashboard
      </p>
    </div>

    <!-- Stats Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-avatar color="primary" size="48" class="mr-4">
                <v-icon color="white">mdi-bell</v-icon>
              </v-avatar>
              <div>
                <div class="text-h5 font-weight-bold">{{ stats.total }}</div>
                <div class="text-caption text-medium-emphasis">Total Notifications</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-avatar color="warning" size="48" class="mr-4">
                <v-icon color="white">mdi-clock-alert</v-icon>
              </v-avatar>
              <div>
                <div class="text-h5 font-weight-bold">{{ stats.pending }}</div>
                <div class="text-caption text-medium-emphasis">Pending Review</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-avatar color="success" size="48" class="mr-4">
                <v-icon color="white">mdi-check-circle</v-icon>
              </v-avatar>
              <div>
                <div class="text-h5 font-weight-bold">{{ stats.approved }}</div>
                <div class="text-caption text-medium-emphasis">Approved Today</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card">
          <v-card-text>
            <div class="d-flex align-center">
              <v-avatar color="info" size="48" class="mr-4">
                <v-icon color="white">mdi-send</v-icon>
              </v-avatar>
              <div>
                <div class="text-h5 font-weight-bold">{{ stats.dispatched }}</div>
                <div class="text-caption text-medium-emphasis">Dispatched Today</div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-lightning-bolt</v-icon>
            Quick Actions
          </v-card-title>
          
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <v-btn
                  color="primary"
                  variant="tonal"
                  size="large"
                  block
                  class="mb-3"
                  @click="goToNotifications"
                >
                  <v-icon start>mdi-bell</v-icon>
                  View All Notifications
                </v-btn>
              </v-col>

              <v-col v-if="canApproveNotifications" cols="12" sm="6" md="4">
                <v-btn
                  color="warning"
                  variant="tonal"
                  size="large"
                  block
                  class="mb-3"
                  @click="goToPendingNotifications"
                >
                  <v-icon start>mdi-clock-alert</v-icon>
                  Review Pending
                </v-btn>
              </v-col>

              <v-col v-if="canViewAuditLogs" cols="12" sm="6" md="4">
                <v-btn
                  color="info"
                  variant="tonal"
                  size="large"
                  block
                  class="mb-3"
                  @click="goToAuditLogs"
                >
                  <v-icon start>mdi-history</v-icon>
                  Audit Logs
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-account</v-icon>
            Your Profile
          </v-card-title>
          
          <v-card-text>
            <div class="d-flex align-center mb-4">
              <v-avatar size="48" color="primary" class="mr-3">
                <span class="text-h6 font-weight-bold">
                  {{ userInitials }}
                </span>
              </v-avatar>
              <div>
                <div class="text-body-1 font-weight-medium">{{ user?.name }}</div>
                <div class="text-caption text-medium-emphasis">{{ user?.email }}</div>
              </div>
            </div>

            <v-chip
              v-for="role in user?.roles || []"
              :key="role"
              size="small"
              color="primary"
              variant="tonal"
              class="mr-1 mb-1"
            >
              {{ role }}
            </v-chip>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Activity -->
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-history</v-icon>
        Recent Activity
      </v-card-title>
      
      <v-card-text>
        <div class="text-center py-8">
          <v-icon size="64" color="grey-lighten-1">mdi-history</v-icon>
          <p class="text-body-1 text-medium-emphasis mt-4">
            Recent activity will appear here
          </p>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// Computed properties
const user = computed(() => authStore.user)
const organization = computed(() => authStore.organization)
const canApproveNotifications = computed(() => authStore.canApproveNotifications)
const canViewAuditLogs = computed(() => authStore.canViewAuditLogs)

const userInitials = computed(() => {
  if (!user.value?.name) return 'U'
  
  const names = user.value.name.split(' ')
  if (names.length === 1) {
    return names[0].charAt(0).toUpperCase()
  }
  
  return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase()
})

// Mock stats (will be replaced with real data)
const stats = reactive({
  total: 0,
  pending: 0,
  approved: 0,
  dispatched: 0
})

// Navigation methods
const goToNotifications = () => {
  router.push({ name: 'notifications' })
}

const goToPendingNotifications = () => {
  router.push({ name: 'notifications', query: { status: 'received' } })
}

const goToAuditLogs = () => {
  router.push({ name: 'audit-logs' })
}
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.stat-card {
  height: 100%;
  transition: transform 0.2s ease-in-out;
}

.stat-card:hover {
  transform: translateY(-2px);
}
</style>