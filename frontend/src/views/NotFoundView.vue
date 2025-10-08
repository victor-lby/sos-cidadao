<template>
  <div class="not-found">
    <v-container class="text-center">
      <v-row justify="center" align="center" class="fill-height">
        <v-col cols="12" md="6">
          <v-icon size="120" color="grey-lighten-1" class="mb-4">
            mdi-file-question
          </v-icon>
          
          <h1 class="text-h3 font-weight-bold mb-4">
            Page Not Found
          </h1>
          
          <p class="text-h6 text-medium-emphasis mb-6">
            The page you're looking for doesn't exist or has been moved.
          </p>
          
          <v-btn
            color="primary"
            size="large"
            @click="goHome"
          >
            <v-icon start>mdi-home</v-icon>
            Go to Dashboard
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push({ name: 'dashboard' })
}
</script>

<style scoped>
.not-found {
  min-height: 60vh;
  display: flex;
  align-items: center;
}
</style>