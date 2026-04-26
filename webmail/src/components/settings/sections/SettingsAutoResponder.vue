<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMailStore } from '@/stores/mail'
import { mailApi } from '@/api/mail'

const mailStore = useMailStore()

const arActive = ref(false)
const arSubject = ref('')
const arBody = ref('')
const arStartDate = ref('')
const arEndDate = ref('')
const arInterval = ref(24)
const arLoading = ref(false)
const arSaveLoading = ref(false)
const arDeleteLoading = ref(false)
const arError = ref('')
const arSuccess = ref('')
const arExists = ref(false)

async function loadAutoResponder(address: string) {
  arLoading.value = true
  arError.value = ''
  arExists.value = false
  try {
    const res = await mailApi.getAutoResponder(address)
    const d = res.data
    arExists.value = true
    arActive.value = d.is_active === 1 || d.is_active === true
    arSubject.value = d.subject || ''
    arBody.value = d.message_body || ''
    arStartDate.value = d.start_date || ''
    arEndDate.value = d.end_date || ''
    arInterval.value = d.reply_interval_hours ?? 24
  } catch (e: any) {
    if (e?.response?.status === 404) {
      arActive.value = false
      arSubject.value = ''
      arBody.value = ''
      arStartDate.value = ''
      arEndDate.value = ''
      arInterval.value = 24
    } else {
      arError.value = 'Failed to load auto-responder settings.'
    }
  } finally {
    arLoading.value = false
  }
}

watch(() => mailStore.currentMailbox, (addr) => { if (addr) loadAutoResponder(addr) }, { immediate: true })

async function saveAutoResponder() {
  if (!mailStore.currentMailbox) return
  arError.value = ''
  arSuccess.value = ''
  if (!arBody.value.trim()) { arError.value = 'Message body is required.'; return }
  arSaveLoading.value = true
  try {
    await mailApi.setAutoResponder(mailStore.currentMailbox, {
      is_active: arActive.value,
      subject: arSubject.value,
      message_body: arBody.value,
      start_date: arStartDate.value || null,
      end_date: arEndDate.value || null,
      reply_interval_hours: arInterval.value,
    })
    arExists.value = true
    arSuccess.value = 'Auto-responder saved.'
  } catch {
    arError.value = 'Failed to save. Try again.'
  } finally {
    arSaveLoading.value = false
  }
}

async function deleteAutoResponder() {
  if (!mailStore.currentMailbox || !arExists.value) return
  arError.value = ''
  arSuccess.value = ''
  arDeleteLoading.value = true
  try {
    await mailApi.deleteAutoResponder(mailStore.currentMailbox)
    arExists.value = false
    arActive.value = false
    arSubject.value = ''
    arBody.value = ''
    arStartDate.value = ''
    arEndDate.value = ''
    arInterval.value = 24
    arSuccess.value = 'Auto-responder deleted.'
  } catch {
    arError.value = 'Failed to delete. Try again.'
  } finally {
    arDeleteLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Auto-Responder</h2>
      <p class="text-sm text-muted-foreground mt-1">Automatically reply to incoming messages when you're away.</p>
    </div>

    <div v-if="!mailStore.currentMailbox" class="text-sm text-muted-foreground">No mailbox selected.</div>

    <div v-else-if="arLoading" class="text-sm text-muted-foreground">Loading…</div>

    <template v-else>
      <div class="rounded-lg border p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium">Enable auto-responder</p>
            <p class="text-xs text-muted-foreground mt-0.5">Replies will be sent automatically while active.</p>
          </div>
          <button
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200"
            :class="arActive ? 'bg-primary' : 'bg-muted'"
            role="switch"
            :aria-checked="arActive"
            @click="arActive = !arActive"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200"
              :class="arActive ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>
      </div>

      <div class="rounded-lg border p-4 space-y-4">
        <p class="text-sm font-medium">Message</p>

        <div class="space-y-1.5">
          <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Subject</label>
          <input
            v-model="arSubject"
            type="text"
            placeholder="e.g. Out of Office"
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div class="space-y-1.5">
          <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Body</label>
          <textarea
            v-model="arBody"
            rows="5"
            placeholder="I'm currently away and will respond when I return."
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
        </div>
      </div>

      <div class="rounded-lg border p-4 space-y-4">
        <p class="text-sm font-medium">Schedule (optional)</p>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1.5">
            <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Start date</label>
            <input v-model="arStartDate" type="date" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">End date</label>
            <input v-model="arEndDate" type="date" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
        </div>
        <div class="space-y-1.5">
          <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Reply interval (hours)</label>
          <input v-model.number="arInterval" type="number" min="1" max="720" class="w-28 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <p class="text-xs text-muted-foreground">Minimum hours between replies to the same sender.</p>
        </div>
      </div>

      <p v-if="arError" class="text-xs text-destructive">{{ arError }}</p>
      <p v-if="arSuccess" class="text-xs text-green-600 dark:text-green-400">{{ arSuccess }}</p>

      <div class="flex gap-2">
        <button
          :disabled="arSaveLoading"
          class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          @click="saveAutoResponder"
        >{{ arSaveLoading ? 'Saving…' : 'Save' }}</button>
        <button
          v-if="arExists"
          :disabled="arDeleteLoading"
          class="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium text-destructive hover:bg-accent transition-colors disabled:opacity-50"
          @click="deleteAutoResponder"
        >{{ arDeleteLoading ? 'Deleting…' : 'Delete' }}</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dark input, .dark textarea {
  background-color: hsl(var(--muted)) !important;
  color: hsl(var(--foreground));
}
.dark input::placeholder, .dark textarea::placeholder {
  color: hsl(var(--muted-foreground)); opacity: 1;
}
</style>
