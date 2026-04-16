<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { useMailStore } from '../../stores/mail'
import SettingsContent from '../settings/SettingsContent.vue'

const store = useMailStore()
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="store.isSettingsOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="store.isSettingsOpen = false"
      >
        <div class="relative w-full max-w-3xl rounded-xl border bg-background shadow-xl mx-4 max-h-[90vh] overflow-y-auto">
          <button
            class="absolute right-4 top-4 inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            @click="store.isSettingsOpen = false"
          >
            <X class="size-4" />
          </button>
          <SettingsContent />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
