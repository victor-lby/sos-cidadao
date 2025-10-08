<template>
  <v-app>
    <!-- Loading Overlay -->
    <LoadingSpinner
      v-if="isInitializing"
      overlay
      message="Loading application..."
    />

    <!-- Main Layout (only show when authenticated and initialized) -->
    <template v-else-if="isAuthenticated">
      <!-- Navigation Drawer -->
      <AppNavigation
        @help="showHelp"
        @about="showAbout"
      />

      <!-- App Bar -->
      <AppBar
        :user="user"
        :organization="organization"
        :pending-count="pendingNotificationsCount"
        @toggle-drawer="toggleDrawer"
        @notifications="goToNotifications"
        @logout="handleLogout"
        @profile="goToProfile"
        @organization="goToOrganizationSettings"
      />

      <!-- Main Content -->
      <v-main class="main-content">
        <v-container fluid class="pa-6">
          <!-- Global Error Alert -->
          <ErrorAlert
            v-if="globalError"
            :error="globalError"
            title="Application Error"
            @close="clearGlobalError"
            @retry="retryLastAction"
          />

          <!-- Page Content -->
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </v-container>
      </v-main>
    </template>

    <!-- Login/Unauthenticated View -->
    <template v-else>
      <v-main class="login-main">
        <router-view />
      </v-main>
    </template>

    <!-- Help Dialog -->
    <v-dialog v-model="helpDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-help-circle</v-icon>
          Help & Support
        </v-card-title>
        
        <v-card-text>
          <div class="mb-4">
            <h3 class="text-h6 mb-2">Getting Started</h3>
            <p>Welcome to S.O.S Cidadão, your civic notification management platform.</p>
          </div>

          <div class="mb-4">
            <h3 class="text-h6 mb-2">Key Features</h3>
            <ul>
              <li>Review and moderate incoming notifications</li>
              <li>Approve or deny notifications with audit trails</li>
              <li>Manage notification targets and categories</li>
              <li>Configure endpoints for message dispatch</li>
              <li>View comprehensive audit logs</li>
            </ul>
          </div>

          <div class="mb-4">
            <h3 class="text-h6 mb-2">Need Help?</h3>
            <p>
              For technical support or questions about using the platform,
              please contact your system administrator.
            </p>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="helpDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- About Dialog -->
    <v-dialog v-model="aboutDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-information</v-icon>
          About S.O.S Cidadão
        </v-card-title>
        
        <v-card-text>
          <div class="text-center mb-4">
            <v-avatar size="64" color="primary" class="mb-3">
              <v-icon size="32">mdi-shield-alert</v-icon>
            </v-avatar>
            <h2 class="text-h5 mb-2">S.O.S Cidadão</h2>
            <p class="text-subtitle-1 text-medium-emphasis">
              Civic Notification Platform
            </p>
          </div>

          <div class="mb-4">
            <p>
              An open-source platform for managing municipal emergency notifications
              with comprehensive audit trails and role-based access control.
            </p>
          </div>

          <div class="mb-4">
            <v-chip size="small" color="primary" variant="tonal" class="mr-2">
              Version 1.0.0
            </v-chip>
            <v-chip size="small" color="success" variant="tonal">
              Apache 2.0 License
            </v-chip>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="aboutDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import type { User, Organization } from '@/types'
import AppNavigation from './AppNavigation.vue'
import AppBar from './AppBar.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorAlert from './ErrorAlert.vue'

const router = useRouter()
const authStore = useAuthStore()
const { error: globalError, clearError: clearGlobalError, retryLastAction } = useErrorHandler()

const isInitializing = ref(true)
const helpDialog = ref(false)
const aboutDialog = ref(false)

// Computed properties
const isAuthenticated = computed(() => authStore.isAuthenticated)
const user = computed(() => authStore.user as User | null)
const organization = computed(() => authStore.organization as Organization | null)

// Mock pending notifications count (will be replaced with real data)
const pendingNotificationsCount = computed(() => 0)

// Methods
const toggleDrawer = () => {
  // This will be handled by the navigation component
}

const goToNotifications = () => {
  router.push({ name: 'notifications' })
}

const goToProfile = () => {
  router.push({ name: 'profile' })
}

const goToOrganizationSettings = () => {
  router.push({ name: 'admin-organization' })
}

const handleLogout = async () => {
  try {
    await authStore.logout()
    router.push({ name: 'login' })
  } catch (error) {
    console.error('Logout failed:', error)
  }
}

const showHelp = () => {
  helpDialog.value = true
}

const showAbout = () => {
  aboutDialog.value = true
}

// Initialize the application
onMounted(async () => {
  try {
    await authStore.initialize()
  } catch (error) {
    console.error('Failed to initialize auth:', error)
  } finally {
    isInitializing.value = false
  }
})
</script>

<style scoped>
.main-content {
  background-color: rgb(var(--v-theme-background));
}

.login-main {
  background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, rgb(var(--v-theme-secondary)) 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Page transition animations */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease-in-out;
}

.page-enter-from,
.page-leave-to {
  opacity: 0;
}
</style>