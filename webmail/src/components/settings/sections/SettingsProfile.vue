<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMailStore } from '@/stores/mail'
import { mailApi } from '@/api/mail'

const store = useMailStore()

const displayName = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')

async function load(address: string) {
  loading.value = true
  error.value = ''
  try {
    const res = await mailApi.getMailboxPreferences(address)
    displayName.value = res.data.display_name || ''
  } catch {
    error.value = 'Failed to load profile.'
  } finally {
    loading.value = false
  }
}

watch(() => store.currentMailbox, (addr) => { if (addr) load(addr) }, { immediate: true })

async function save() {
  if (!store.currentMailbox) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    await mailApi.updateMailboxPreferences(store.currentMailbox, { display_name: displayName.value })
    const mb = store.mailboxes.find(m => m.address === store.currentMailbox)
    if (mb) mb.display_name = displayName.value
    success.value = 'Display name updated.'
  } catch {
    error.value = 'Failed to save.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Profile</h2>
      <p class="text-sm text-muted-foreground mt-1">Your display name appears in the From field of emails you send.</p>
    </div>

    <div v-if="!store.currentMailbox" class="text-sm text-muted-foreground">No mailbox selected.</div>

    <template v-else>
      <div v-if="loading" class="text-sm text-muted-foreground">Loading…</div>

      <template v-else>
        <div class="rounded-lg border p-4 space-y-4">
          <div class="space-y-1.5">
            <label class="text-sm font-medium">Email address</label>
            <p class="text-sm font-mono text-muted-foreground">{{ store.currentMailbox }}</p>
          </div>

          <div class="space-y-1.5">
            <label class="text-sm font-medium" for="display-name-input">Display name</label>
            <input
              id="display-name-input"
              v-model="displayName"
              type="text"
              placeholder="Your Name"
              maxlength="100"
              class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              @keydown.enter="save"
            />
            <p class="text-xs text-muted-foreground">Sent as: {{ displayName ? `${displayName} <${store.currentMailbox}>` : store.currentMailbox }}</p>
          </div>

          <p v-if="error" class="text-xs text-destructive">{{ error }}</p>
          <p v-if="success" class="text-xs text-green-600 dark:text-green-400">{{ success }}</p>

          <button
            :disabled="saving"
            class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            @click="save"
          >{{ saving ? 'Saving…' : 'Save' }}</button>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.dark input {
  background-color: hsl(var(--muted)) !important;
  color: hsl(var(--foreground));
}
.dark input::placeholder {
  color: hsl(var(--muted-foreground)); opacity: 1;
}
</style>
