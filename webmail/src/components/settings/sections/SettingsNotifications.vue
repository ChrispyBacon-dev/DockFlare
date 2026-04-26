<script setup lang="ts">
import { ref, watch } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import { usePushSubscription } from '@/composables/usePushSubscription'
import { useMailStore } from '@/stores/mail'
import { mailApi } from '@/api/mail'

const notificationsStore = useNotificationsStore()
const push = usePushSubscription()
const mailStore = useMailStore()

const notificationPreview = ref(true)
const previewLoading = ref(false)

watch(
  () => mailStore.currentMailbox,
  async (address) => {
    if (!address) return
    try {
      const res = await mailApi.getMailboxPreferences(address)
      notificationPreview.value = res.data.notification_preview
    } catch { /* ignore */ }
  },
  { immediate: true }
)

async function togglePreview() {
  if (!mailStore.currentMailbox || previewLoading.value) return
  previewLoading.value = true
  const next = !notificationPreview.value
  try {
    await mailApi.updateMailboxPreferences(mailStore.currentMailbox, { notification_preview: next })
    notificationPreview.value = next
  } catch { /* ignore */ } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Notifications</h2>
      <p class="text-sm text-muted-foreground mt-1">Get notified when new mail arrives, even when the app is closed.</p>
    </div>

    <template v-if="notificationsStore.isDenied">
      <div class="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-muted-foreground">
        Notifications are blocked. Enable them in your browser or OS settings.
      </div>
    </template>

    <template v-else-if="!notificationsStore.isGranted">
      <button
        class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        @click="notificationsStore.requestPermission"
      >
        Enable Notifications
      </button>
    </template>

    <template v-else>
      <div class="rounded-lg border p-4 space-y-4">
        <p class="text-sm font-medium text-green-600 dark:text-green-400">Permission granted</p>

        <div v-if="push.isSupported">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium">Background push</p>
              <p class="text-xs text-muted-foreground mt-0.5">Receive notifications even when the app is closed.</p>
            </div>
            <button
              v-if="!push.isSubscribed.value"
              :disabled="push.isLoading.value"
              class="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              @click="push.subscribe()"
            >
              {{ push.isLoading.value ? 'Enabling…' : 'Enable' }}
            </button>
            <button
              v-else
              :disabled="push.isLoading.value"
              class="inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
              @click="push.unsubscribe()"
            >
              {{ push.isLoading.value ? 'Disabling…' : 'Disable' }}
            </button>
          </div>
          <p v-if="push.error.value" class="text-xs text-destructive mt-1">{{ push.error.value }}</p>
        </div>
        <p v-else class="text-sm text-muted-foreground">Background push is not supported in this browser.</p>
      </div>

      <div v-if="mailStore.currentMailbox" class="rounded-lg border p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium">Show subject &amp; sender</p>
            <p class="text-xs text-muted-foreground mt-0.5">Display message details in the notification preview.</p>
          </div>
          <button
            :disabled="previewLoading"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 disabled:opacity-50"
            :class="notificationPreview ? 'bg-primary' : 'bg-muted'"
            role="switch"
            :aria-checked="notificationPreview"
            @click="togglePreview"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200"
              :class="notificationPreview ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
