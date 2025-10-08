<template>
  <v-app-bar
    elevation="1"
    class="app-bar"
  >
    <!-- Mobile Menu Toggle -->
    <v-app-bar-nav-icon
      class="d-lg-none"
      @click="$emit('toggle-drawer')"
    />

    <!-- Breadcrumbs -->
    <v-breadcrumbs
      v-if="breadcrumbs.length > 0"
      :items="breadcrumbs"
      class="pa-0"
    >
      <template #divider>
        <v-icon size="16">mdi-chevron-right</v-icon>
      </template>
    </v-breadcrumbs>

    <!-- Page Title (fallback if no breadcrumbs) -->
    <v-toolbar-title v-else class="text-h6 font-weight-medium">
      {{ pageTitle }}
    </v-toolbar-title>

    <v-spacer />

    <!-- Notification Badge -->
    <v-btn
      icon
      variant="text"
      class="mr-2"
      @click="$emit('notifications')"
    >
      <v-badge
        v-if="pendingCount > 0"
        :content="pendingCount"
        color="error"
        overlap
      >
        <v-icon>mdi-bell</v-icon>
      </v-badge>
      <v-icon v-else>mdi-bell-outline</v-icon>
    </v-btn>

    <!-- User Profile Menu -->
    <UserProfileMenu
      :user="user"
      :organization="organization"
      :can-manage-organization="canManageOrganization"
      @logout="handleLogout"
      @profile="$emit('profile')"
      @organization="$emit('organization')"
    />
  </v-app-bar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserProfileMenu from './UserProfileMenu.vue'
import type { User, Organization } from '@/types'

interface BreadcrumbItem {
  title: string
  disabled?: boolean
  href?: string
  to?: string | object
}

interface Props {
  user: User | null
  organization: Organization | null
  pendingCount?: number
}

interface Emits {
  (event: 'toggle-drawer'): void
  (event: 'notifications'): void
  (event: 'logout'): void
  (event: 'profile'): void
  (event: 'organization'): void
}

withDefaults(defineProps<Props>(), {
  pendingCount: 0
})

const emit = defineEmits<Emits>()

const route = useRoute()
const authStore = useAuthStore()

const canManageOrganization = computed(() => authStore.canManageOrganization)

// Generate breadcrumbs based on current route
const breadcrumbs = computed((): BreadcrumbItem[] => {
  const crumbs: BreadcrumbItem[] = []
  
  // Always start with Dashboard
  crumbs.push({
    title: 'Dashboard',
    to: { name: 'dashboard' }
  })

  // Add route-specific breadcrumbs
  if (route.name === 'notifications') {
    crumbs.push({
      title: 'Notifications',
      disabled: true
    })
  } else if (route.name?.toString().startsWith('admin-')) {
    crumbs.push({
      title: 'Administration',
      to: { name: 'admin' }
    })
    
    if (route.name === 'admin-users') {
      crumbs.push({ title: 'Users & Roles', disabled: true })
    } else if (route.name === 'admin-organization') {
      crumbs.push({ title: 'Organization', disabled: true })
    } else if (route.name === 'admin-targets') {
      crumbs.push({ title: 'Targets & Categories', disabled: true })
    } else if (route.name === 'admin-endpoints') {
      crumbs.push({ title: 'Endpoints', disabled: true })
    }
  } else if (route.name === 'audit-logs') {
    crumbs.push({
      title: 'Audit Logs',
      disabled: true
    })
  }

  return crumbs
})

// Fallback page title when no breadcrumbs
const pageTitle = computed(() => {
  const routeName = route.name?.toString() || ''
  
  const titleMap: Record<string, string> = {
    dashboard: 'Dashboard',
    notifications: 'Notifications',
    'admin-users': 'Users & Roles',
    'admin-organization': 'Organization Settings',
    'admin-targets': 'Targets & Categories',
    'admin-endpoints': 'Endpoints',
    'audit-logs': 'Audit Logs'
  }

  return titleMap[routeName] || 'S.O.S Cidadão'
})

const handleLogout = () => {
  emit('logout')
}
</script>

<style scoped>
.app-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

:deep(.v-breadcrumbs-item--disabled) {
  opacity: 1;
}

:deep(.v-breadcrumbs-item--disabled .v-breadcrumbs-item--link) {
  color: rgba(var(--v-theme-on-surface), 0.87);
  pointer-events: none;
}
</style>