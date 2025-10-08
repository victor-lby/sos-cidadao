<template>
  <v-navigation-drawer
    v-model="drawer"
    :rail="rail"
    permanent
    class="app-navigation"
  >
    <!-- Navigation Header -->
    <div class="navigation-header pa-4">
      <div class="d-flex align-center">
        <v-avatar
          :size="rail ? 32 : 40"
          color="primary"
          class="mr-3"
        >
          <v-icon :size="rail ? 20 : 24">mdi-shield-alert</v-icon>
        </v-avatar>
        
        <div v-if="!rail" class="app-title">
          <div class="text-h6 font-weight-bold primary--text">
            S.O.S Cidadão
          </div>
          <div class="text-caption text-medium-emphasis">
            Civic Notification Platform
          </div>
        </div>
      </div>
    </div>

    <v-divider />

    <!-- Navigation Items -->
    <v-list nav density="comfortable">
      <!-- Dashboard -->
      <v-list-item
        :to="{ name: 'dashboard' }"
        prepend-icon="mdi-view-dashboard"
        title="Dashboard"
        value="dashboard"
      />

      <!-- Notifications -->
      <v-list-group value="notifications">
        <template #activator="{ props }">
          <v-list-item
            v-bind="props"
            prepend-icon="mdi-bell"
            title="Notifications"
          />
        </template>

        <v-list-item
          :to="{ name: 'notifications' }"
          prepend-icon="mdi-bell-outline"
          title="All Notifications"
          value="notifications-list"
        />

        <v-list-item
          v-if="canApproveNotifications"
          :to="{ name: 'notifications', query: { status: 'received' } }"
          prepend-icon="mdi-bell-alert"
          title="Pending Review"
          value="notifications-pending"
        />

        <v-list-item
          :to="{ name: 'notifications', query: { status: 'approved' } }"
          prepend-icon="mdi-bell-check"
          title="Approved"
          value="notifications-approved"
        />
      </v-list-group>

      <!-- Administration -->
      <v-list-group v-if="hasAdminAccess" value="admin">
        <template #activator="{ props }">
          <v-list-item
            v-bind="props"
            prepend-icon="mdi-cog"
            title="Administration"
          />
        </template>

        <v-list-item
          v-if="canManageUsers"
          :to="{ name: 'admin-users' }"
          prepend-icon="mdi-account-group"
          title="Users & Roles"
          value="admin-users"
        />

        <v-list-item
          v-if="canManageOrganization"
          :to="{ name: 'admin-organization' }"
          prepend-icon="mdi-domain"
          title="Organization"
          value="admin-organization"
        />

        <v-list-item
          :to="{ name: 'admin-targets' }"
          prepend-icon="mdi-target"
          title="Targets & Categories"
          value="admin-targets"
        />

        <v-list-item
          :to="{ name: 'admin-endpoints' }"
          prepend-icon="mdi-api"
          title="Endpoints"
          value="admin-endpoints"
        />
      </v-list-group>

      <!-- Audit Logs -->
      <v-list-item
        v-if="canViewAuditLogs"
        :to="{ name: 'audit-logs' }"
        prepend-icon="mdi-history"
        title="Audit Logs"
        value="audit-logs"
      />

      <v-divider class="my-2" />

      <!-- Help & Support -->
      <v-list-item
        prepend-icon="mdi-help-circle"
        title="Help & Support"
        value="help"
        @click="$emit('help')"
      />

      <v-list-item
        prepend-icon="mdi-information"
        title="About"
        value="about"
        @click="$emit('about')"
      />
    </v-list>

    <!-- Rail Toggle Button -->
    <template #append>
      <div class="pa-2">
        <v-btn
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          size="small"
          @click="toggleRail"
        />
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

interface Emits {
  (event: 'help'): void
  (event: 'about'): void
}

defineEmits<Emits>()

const authStore = useAuthStore()

const drawer = ref(true)
const rail = ref(false)

// Permission-based computed properties
const canApproveNotifications = computed(() => authStore.canApproveNotifications)
const canManageUsers = computed(() => authStore.canManageUsers)
const canManageOrganization = computed(() => authStore.canManageOrganization)
const canViewAuditLogs = computed(() => authStore.canViewAuditLogs)

const hasAdminAccess = computed(() => 
  canManageUsers.value || 
  canManageOrganization.value || 
  authStore.hasAnyPermission(['target:manage', 'endpoint:manage'])
)

const toggleRail = () => {
  rail.value = !rail.value
}
</script>

<style scoped>
.app-navigation {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.navigation-header {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.app-title {
  line-height: 1.2;
}

:deep(.v-list-group__items) {
  padding-left: 16px;
}

:deep(.v-list-item--active) {
  background-color: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

:deep(.v-list-item--active .v-list-item__prepend .v-icon) {
  color: rgb(var(--v-theme-primary));
}
</style>