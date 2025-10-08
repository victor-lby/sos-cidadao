<template>
  <div class="loading-container" :class="{ 'loading-overlay': overlay }">
    <v-progress-circular
      :size="size"
      :width="width"
      :color="color"
      :indeterminate="indeterminate"
      :model-value="value"
    />
    <div v-if="message" class="loading-message mt-4">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  size?: number | string
  width?: number | string
  color?: string
  indeterminate?: boolean
  value?: number
  message?: string
  overlay?: boolean
}

withDefaults(defineProps<Props>(), {
  size: 40,
  width: 4,
  color: 'primary',
  indeterminate: true,
  value: 0,
  overlay: false
})
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  z-index: 9999;
}

.loading-message {
  text-align: center;
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.875rem;
}
</style>