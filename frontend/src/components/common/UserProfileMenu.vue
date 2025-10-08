<template>
  <v-menu>
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
        variant="text"
        class="user-profile-btn"
      >
        <v-avatar size="32" color="primary">
          <v-icon v-if="!user?.name">mdi-account</v-icon>
          <span v-else class="text-caption font-weight-bold">
            {{ userInitials }}
          </span>
        </v-avatar>
        
        <div class="user-info ml-2 d-none d-sm-block">
          <div class="text-body-2 font-weight-medium">
            {{ user?.name || 'User' }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{ organization?.name || 'Organization' }}
          </div>
        </div>
        
        <v-icon class="ml-1">mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-list min-width="280">
      <!-- User Info Header -->
      <v-list-item class="user-header">
        <template #prepend>
          <v-avatar size="40" color="primary">
            <v-icon v-if="!user?.name">mdi-account</v-icon>
            <span v-else class="text-body-1 font-weight-bold">
              {{ userInitials }}
            </span>
          </v-avatar>
        </template>
        
        <v-list-item-title class="font-weight-medium">
          {{ user?.name || 'User' }}
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ user?.email || 'user@example.com' }}
        </v-list-item-subtitle>
      </v-list-item>

      <v-divider />

      <!-- Organization Info -->
      <v-list-item>
        <template #prepend>
          <v-icon>mdi-domain</v-icon>
        </template>
        <v-list-item-title>{{ organization?.name || 'Organization' }}</v-list-item-title>
        <v-list-item-subtitle>Organization</v-list-item-subtitle>
      </v-list-item>

      <v-divider />

      <!-- Menu Items -->
      <v-list-item @click="$emit('profile')">
        <template #prepend>
          <v-icon>mdi-account-circle</v-icon>
        </template>
        <v-list-item-title>Profile Settings</v-list-item-title>
      </v-list-item>

      <v-list-item v-if="canManageOrganization" @click="$emit('organization')">
        <template #prepend>
          <v-icon>mdi-cog</v-icon>
        </template>
        <v-list-item-title>Organization Settings</v-list-item-title>
      </v-list-item>

      <v-list-item @click="toggleTheme">
        <template #prepend>
          <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
        </template>
        <v-list-item-title>
          {{ isDark ? 'Light Mode' : 'Dark Mode' }}
        </v-list-item-title>
      </v-list-item>

      <v-divider />

      <v-list-item @click="handleLogout" class="logout-item">
        <template #prepend>
          <v-icon color="error">mdi-logout</v-icon>
        </template>
        <v-list-item-title class="text-error">Logout</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import type { User, Organization } from '@/types'

interface Props {
  user: User | null
  organization: Organization | null
  canManageOrganization?: boolean
}

interface Emits {
  (event: 'logout'): void
  (event: 'profile'): void
  (event: 'organization'): void
}

const props = withDefaults(defineProps<Props>(), {
  canManageOrganization: false
})

const emit = defineEmits<Emits>()

const theme = useTheme()
const authStore = useAuthStore()

const isDark = computed(() => theme.global.current.value.dark)

const userInitials = computed(() => {
  if (!props.user?.name) return 'U'
  
  const names = props.user.name.split(' ')
  if (names.length === 1) {
    return names[0].charAt(0).toUpperCase()
  }
  
  return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase()
})

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

const handleLogout = async () => {
  try {
    await authStore.logout()
    emit('logout')
  } catch (error) {
    console.error('Logout failed:', error)
  }
}
</script>

<style scoped>
.user-profile-btn {
  text-transform: none !important;
  height: auto !important;
  padding: 8px 12px !important;
}

.user-info {
  text-align: left;
  line-height: 1.2;
}

.user-header {
  padding: 16px !important;
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.logout-item:hover {
  background-color: rgba(var(--v-theme-error), 0.08) !important;
}
</style>