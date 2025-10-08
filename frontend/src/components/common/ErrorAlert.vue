<template>
  <v-alert
    v-if="error"
    type="error"
    variant="tonal"
    closable
    class="mb-4"
    @click:close="$emit('close')"
  >
    <template #title>
      <v-icon start>mdi-alert-circle</v-icon>
      {{ title }}
    </template>

    <div class="error-content">
      {{ error.message }}
    </div>

    <template v-if="error.retryable" #append>
      <v-btn
        variant="outlined"
        size="small"
        color="error"
        @click="$emit('retry')"
      >
        <v-icon start>mdi-refresh</v-icon>
        Retry
      </v-btn>
    </template>
  </v-alert>
</template>

<script setup lang="ts">
import type { AppError } from '@/types'

interface Props {
  error: AppError | null
  title?: string
}

interface Emits {
  (event: 'close'): void
  (event: 'retry'): void
}

withDefaults(defineProps<Props>(), {
  title: 'Error'
})

defineEmits<Emits>()
</script>

<style scoped>
.error-content {
  margin-top: 0.5rem;
  line-height: 1.5;
}
</style>