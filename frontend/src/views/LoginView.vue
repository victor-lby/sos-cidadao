<template>
  <v-container class="login-container">
    <v-row justify="center" align="center" class="fill-height">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="login-card" elevation="8">
          <!-- Header -->
          <v-card-title class="text-center pa-6">
            <div class="login-header">
              <v-avatar size="64" color="primary" class="mb-4">
                <v-icon size="32" color="white">mdi-shield-alert</v-icon>
              </v-avatar>
              <h1 class="text-h4 font-weight-bold mb-2">S.O.S Cidadão</h1>
              <p class="text-subtitle-1 text-medium-emphasis">
                Civic Notification Platform
              </p>
            </div>
          </v-card-title>

          <!-- Login Form -->
          <v-card-text class="pa-6">
            <ErrorAlert
              :error="error"
              title="Login Failed"
              @close="clearError"
            />

            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email"
                variant="outlined"
                :rules="emailRules"
                :disabled="isLoading"
                class="mb-4"
                required
              />

              <v-text-field
                v-model="password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="passwordRules"
                :disabled="isLoading"
                class="mb-6"
                required
                @click:append-inner="showPassword = !showPassword"
              />

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="isLoading"
                :disabled="!isFormValid"
              >
                Sign In
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- Footer -->
          <v-card-actions class="pa-6 pt-0">
            <div class="text-center w-100">
              <p class="text-caption text-medium-emphasis">
                Secure access to municipal notification management
              </p>
            </div>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useErrorHandler } from '@/composables/useErrorHandler'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

const router = useRouter()
const authStore = useAuthStore()
const { error, isLoading, handleAsyncAction, clearError } = useErrorHandler()

// Form data
const email = ref('')
const password = ref('')
const showPassword = ref(false)

// Validation rules
const emailRules = [
  (v: string) => !!v || 'Email is required',
  (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
]

const passwordRules = [
  (v: string) => !!v || 'Password is required',
  (v: string) => v.length >= 6 || 'Password must be at least 6 characters'
]

// Computed properties
const isFormValid = computed(() => {
  return email.value && 
         password.value && 
         /.+@.+\..+/.test(email.value) && 
         password.value.length >= 6
})

// Methods
const handleLogin = async () => {
  if (!isFormValid.value) return

  const result = await handleAsyncAction(
    () => authStore.login({
      email: email.value,
      password: password.value
    }),
    {
      successMessage: 'Login successful',
      errorMessage: 'Login failed. Please check your credentials.'
    }
  )

  if (result) {
    // Redirect to dashboard or intended route
    const redirect = router.currentRoute.value.query.redirect as string
    router.push(redirect || { name: 'dashboard' })
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: transparent;
}

.login-card {
  backdrop-filter: blur(10px);
  background-color: rgba(255, 255, 255, 0.95) !important;
}

.login-header {
  text-align: center;
}

:deep(.v-theme--dark .login-card) {
  background-color: rgba(33, 33, 33, 0.95) !important;
}
</style>