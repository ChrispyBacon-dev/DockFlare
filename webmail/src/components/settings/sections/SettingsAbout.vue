<script setup lang="ts">
import { ref } from 'vue'

const deferredPrompt = ref<any>(null)
const canInstall = ref(false)
const installed = ref(false)

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferredPrompt.value = e
  canInstall.value = true
})

window.addEventListener('appinstalled', () => {
  installed.value = true
  canInstall.value = false
})

async function installApp() {
  if (!deferredPrompt.value) return
  deferredPrompt.value.prompt()
  const result = await deferredPrompt.value.userChoice
  if (result.outcome === 'accepted') {
    installed.value = true
    canInstall.value = false
  }
  deferredPrompt.value = null
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">About</h2>
      <p class="text-sm text-muted-foreground mt-1">App information and installation options.</p>
    </div>

    <div class="rounded-lg border p-4 space-y-3">
      <div class="flex items-center gap-3">
        <img src="/logo.gif" alt="DockFlare" class="h-10 w-auto select-none" draggable="false" />
        <div>
          <p class="text-sm font-semibold">DockFlare Webmail</p>
          <p class="text-xs text-muted-foreground">Part of the DockFlare platform</p>
        </div>
      </div>
      <div class="flex flex-col gap-1.5 pt-1">
        <a
          href="https://dockflare.app"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 text-xs text-[#FBA612] hover:underline"
        >
          dockflare.app
        </a>
        <a
          href="https://github.com/ChrispyBacon-dev/DockFlare"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 text-xs text-[#FBA612] hover:underline"
        >
          GitHub
        </a>
      </div>
    </div>

    <div class="rounded-lg border p-4 space-y-3">
      <p class="text-sm font-medium">Install as App</p>
      <p class="text-xs text-muted-foreground">Install DockFlare Webmail to your home screen for a native app experience — works offline and opens without the browser bar.</p>

      <div v-if="installed" class="text-xs text-green-600 dark:text-green-400">App installed successfully.</div>
      <button
        v-else-if="canInstall"
        class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        @click="installApp"
      >
        Install App
      </button>
      <p v-else class="text-xs text-muted-foreground">
        To install: open your browser menu and choose <span class="font-medium">Add to Home Screen</span> or <span class="font-medium">Install App</span>.
      </p>
    </div>
  </div>
</template>
