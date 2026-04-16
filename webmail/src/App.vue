<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { needRefresh, updateServiceWorker } = useRegisterSW()
</script>

<template>
  <RouterView />
  <Transition name="slide-up">
    <div
      v-if="needRefresh"
      class="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg border bg-card px-4 py-3 shadow-lg text-card-foreground"
    >
      <span class="text-sm">Update available</span>
      <button
        class="text-sm font-medium underline underline-offset-2"
        @click="updateServiceWorker()"
      >
        Reload
      </button>
    </div>
  </Transition>
</template>
