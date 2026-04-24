<script setup lang="ts">
import { ref, watch } from 'vue'
import { useInstallPrompt } from '@/composables/useInstallPrompt'
import { useNotificationsStore } from '@/stores/notifications'
import { usePushSubscription } from '@/composables/usePushSubscription'
import { useMailStore } from '@/stores/mail'
import { mailApi } from '@/api/mail'
import { authApi } from '@/api/auth'
import type { Alias } from '@/types/mail'

const { canInstall, promptInstall } = useInstallPrompt()
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
    loadAutoResponder(address)
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

const pwCurrent = ref('')
const pwNew = ref('')
const pwConfirm = ref('')
const pwLoading = ref(false)
const pwError = ref('')
const pwSuccess = ref('')

async function changePassword() {
  pwError.value = ''
  pwSuccess.value = ''
  if (!pwNew.value || pwNew.value !== pwConfirm.value) {
    pwError.value = 'New passwords do not match.'
    return
  }
  if (pwNew.value.length < 8) {
    pwError.value = 'Password must be at least 8 characters.'
    return
  }
  pwLoading.value = true
  try {
    const data = await authApi.changePassword(pwCurrent.value, pwNew.value)
    if (data.error) {
      pwError.value = data.error
    } else {
      pwSuccess.value = 'Password changed successfully.'
      pwCurrent.value = ''
      pwNew.value = ''
      pwConfirm.value = ''
    }
  } catch {
    pwError.value = 'Request failed. Try again.'
  } finally {
    pwLoading.value = false
  }
}

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

async function saveAutoResponder() {
  if (!mailStore.currentMailbox) return
  arError.value = ''
  arSuccess.value = ''
  if (!arBody.value.trim()) {
    arError.value = 'Message body is required.'
    return
  }
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

const alAliases = ref<Alias[]>([])
const alLoading = ref(false)
const alError = ref('')
const alSuccess = ref('')
const alNewAddress = ref('')
const alNewLabel = ref('')
const alNewDescription = ref('')
const alNewExpires = ref('')
const alNeverExpire = ref(true)
const alCreateLoading = ref(false)
const alGenerating = ref(false)

async function loadAliases(address: string) {
  alLoading.value = true
  alError.value = ''
  try {
    const res = await mailApi.getAllAliases(address)
    alAliases.value = res.data.aliases || []
  } catch {
    alError.value = 'Failed to load aliases.'
  } finally {
    alLoading.value = false
  }
}

watch(
  () => mailStore.currentMailbox,
  (address) => { if (address) loadAliases(address) },
  { immediate: true }
)

async function generateAlias() {
  if (!mailStore.currentMailbox) return
  const domain = mailStore.currentMailbox.split('@')[1]
  if (!domain) return
  alGenerating.value = true
  try {
    const res = await mailApi.generateAlias(mailStore.currentMailbox, domain)
    alNewAddress.value = res.data.suggestion?.split('@')[0] || ''
  } catch { /* ignore */ } finally {
    alGenerating.value = false
  }
}

async function createAlias() {
  if (!mailStore.currentMailbox || !alNewAddress.value) return
  const domain = mailStore.currentMailbox.split('@')[1]
  alError.value = ''
  alSuccess.value = ''
  alCreateLoading.value = true
  try {
    await mailApi.createAlias({
      address: `${alNewAddress.value}@${domain}`,
      mailbox_address: mailStore.currentMailbox,
      label: alNewLabel.value || undefined,
      description: alNewDescription.value || undefined,
      expires_at: alNeverExpire.value ? null : (alNewExpires.value || null),
    })
    alNewAddress.value = ''
    alNewLabel.value = ''
    alNewDescription.value = ''
    alNewExpires.value = ''
    alNeverExpire.value = true
    alSuccess.value = 'Alias created.'
    await loadAliases(mailStore.currentMailbox)
  } catch (e: any) {
    alError.value = e?.response?.data?.error || 'Failed to create alias.'
  } finally {
    alCreateLoading.value = false
  }
}

async function toggleAlias(alias: Alias) {
  try {
    await mailApi.updateAlias(alias.address, { is_active: !alias.is_active })
    alias.is_active = !alias.is_active
  } catch { /* ignore */ }
}

async function deleteAlias(alias: Alias) {
  if (!confirm(`Delete alias ${alias.address}? This cannot be undone.`)) return
  try {
    await mailApi.deleteAlias(alias.address)
    alAliases.value = alAliases.value.filter(a => a.address !== alias.address)
  } catch { /* ignore */ }
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString()
}
</script>

<template>
  <div class="p-6">
    <h1 class="text-xl font-semibold mb-5">Settings</h1>

    <div v-if="canInstall" class="mb-4 rounded-lg border p-4 space-y-3">
      <div>
        <h2 class="text-sm font-medium">Install App</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Install DockFlare Mail as a desktop app for faster access and desktop notifications.
        </p>
      </div>
      <button
        class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        @click="promptInstall"
      >
        Install
      </button>
    </div>

    <div class="mb-4 rounded-lg border p-4 space-y-3">
      <div>
        <h2 class="text-sm font-medium">Notifications</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Get notified when new mail arrives, even when the app is closed.
        </p>
      </div>

      <template v-if="notificationsStore.isDenied">
        <p class="text-sm text-muted-foreground">
          Notifications are blocked. Enable them in your browser or OS settings.
        </p>
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
        <p class="text-sm text-muted-foreground">Permission granted.</p>

        <div v-if="push.isSupported" class="space-y-1.5">
          <div class="flex items-center gap-3">
            <span class="text-sm">Background push (all mailboxes)</span>
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
          <p v-if="push.error.value" class="text-xs text-destructive">{{ push.error.value }}</p>
        </div>
        <p v-else class="text-sm text-muted-foreground">
          Background push is not supported in this browser.
        </p>

        <div v-if="mailStore.currentMailbox" class="flex items-center gap-3 pt-1">
          <span class="text-sm">Show subject &amp; sender in notifications</span>
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
      </template>
    </div>

    <div v-if="mailStore.currentMailbox" class="mb-4 rounded-lg border p-4 space-y-3">
      <div>
        <h2 class="text-sm font-medium">Auto-Responder</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Automatically reply to incoming messages when you're away.
        </p>
      </div>

      <div v-if="arLoading" class="text-sm text-muted-foreground">Loading…</div>

      <template v-else>
        <div class="flex items-center gap-3">
          <span class="text-sm">Enable auto-responder</span>
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

        <div class="space-y-2">
          <label class="text-sm font-medium">Subject</label>
          <input
            v-model="arSubject"
            type="text"
            placeholder="e.g. Out of Office"
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-medium">Message</label>
          <textarea
            v-model="arBody"
            rows="4"
            placeholder="I'm currently away and will respond when I return."
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-sm font-medium">Start date (optional)</label>
            <input
              v-model="arStartDate"
              type="date"
              class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div class="space-y-1">
            <label class="text-sm font-medium">End date (optional)</label>
            <input
              v-model="arEndDate"
              type="date"
              class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-sm font-medium">Reply interval (hours)</label>
          <input
            v-model.number="arInterval"
            type="number"
            min="1"
            max="720"
            class="w-32 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <p class="text-xs text-muted-foreground">Minimum hours between replies to the same sender.</p>
        </div>

        <p v-if="arError" class="text-xs text-destructive">{{ arError }}</p>
        <p v-if="arSuccess" class="text-xs text-green-600">{{ arSuccess }}</p>

        <div class="flex gap-2 pt-1">
          <button
            :disabled="arSaveLoading"
            class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            @click="saveAutoResponder"
          >
            {{ arSaveLoading ? 'Saving…' : 'Save' }}
          </button>
          <button
            v-if="arExists"
            :disabled="arDeleteLoading"
            class="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium text-destructive hover:bg-accent transition-colors disabled:opacity-50"
            @click="deleteAutoResponder"
          >
            {{ arDeleteLoading ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </template>
    </div>

    <div class="mb-4 rounded-lg border p-4 space-y-3">
      <div>
        <h2 class="text-sm font-medium">Change Password</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Update your mailbox login password.
        </p>
      </div>

      <div class="space-y-2">
        <label class="text-sm font-medium">Current password</label>
        <input
          v-model="pwCurrent"
          type="password"
          autocomplete="current-password"
          class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div class="space-y-2">
        <label class="text-sm font-medium">New password</label>
        <input
          v-model="pwNew"
          type="password"
          autocomplete="new-password"
          class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div class="space-y-2">
        <label class="text-sm font-medium">Confirm new password</label>
        <input
          v-model="pwConfirm"
          type="password"
          autocomplete="new-password"
          class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <p v-if="pwError" class="text-xs text-destructive">{{ pwError }}</p>
      <p v-if="pwSuccess" class="text-xs text-green-600">{{ pwSuccess }}</p>

      <button
        :disabled="pwLoading || !pwCurrent || !pwNew || !pwConfirm"
        class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        @click="changePassword"
      >
        {{ pwLoading ? 'Updating…' : 'Update Password' }}
      </button>
    </div>

    <div v-if="mailStore.currentMailbox" class="mb-4 rounded-lg border p-4 space-y-3">
      <div>
        <h2 class="text-sm font-medium">Email Aliases</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Create aliases that forward mail to your mailbox while keeping your real address private.
        </p>
      </div>

      <div v-if="alLoading" class="text-sm text-muted-foreground">Loading…</div>

      <template v-else>
        <div v-if="alAliases.length" class="divide-y divide-border rounded-md border overflow-hidden">
          <div
            v-for="alias in alAliases"
            :key="alias.address"
            class="flex items-center gap-3 px-3 py-2.5 bg-background text-sm"
          >
            <div class="flex-1 min-w-0">
              <div class="font-mono text-xs truncate">{{ alias.address }}</div>
              <div class="flex items-center gap-2 mt-0.5">
                <span v-if="alias.label" class="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{{ alias.label }}</span>
                <span v-if="alias.expires_at" class="text-xs text-muted-foreground">Expires {{ formatDate(alias.expires_at) }}</span>
                <span class="text-xs text-muted-foreground">{{ alias.use_count }} received</span>
              </div>
            </div>
            <button
              class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200"
              :class="alias.is_active ? 'bg-primary' : 'bg-muted'"
              role="switch"
              :aria-checked="alias.is_active"
              @click="toggleAlias(alias)"
            >
              <span
                class="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform duration-200"
                :class="alias.is_active ? 'translate-x-4' : 'translate-x-0'"
              />
            </button>
            <button
              class="text-muted-foreground hover:text-destructive transition-colors text-xs"
              @click="deleteAlias(alias)"
            >
              Delete
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-muted-foreground">No aliases yet.</p>

        <div class="space-y-2 pt-1">
          <label class="text-sm font-medium">Create alias</label>
          <div class="flex items-center gap-2">
            <input
              v-model="alNewAddress"
              type="text"
              placeholder="local-part"
              class="flex-1 rounded-md border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <span class="text-sm text-muted-foreground shrink-0">@{{ mailStore.currentMailbox.split('@')[1] }}</span>
            <button
              :disabled="alGenerating"
              class="inline-flex items-center justify-center rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50 shrink-0"
              @click="generateAlias"
            >
              {{ alGenerating ? '…' : 'Generate' }}
            </button>
          </div>
          <input
            v-model="alNewLabel"
            type="text"
            placeholder="Label (optional, e.g. shopping)"
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <input
            v-model="alNewDescription"
            type="text"
            placeholder="Description (optional)"
            maxlength="200"
            class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input v-model="alNeverExpire" type="checkbox" class="rounded border-border" />
              Never expire
            </label>
            <input
              v-if="!alNeverExpire"
              v-model="alNewExpires"
              type="date"
              class="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <p v-if="alError" class="text-xs text-destructive">{{ alError }}</p>
        <p v-if="alSuccess" class="text-xs text-green-600">{{ alSuccess }}</p>

        <button
          :disabled="alCreateLoading || !alNewAddress"
          class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          @click="createAlias"
        >
          {{ alCreateLoading ? 'Creating…' : 'Create Alias' }}
        </button>
      </template>
    </div>

    <p class="text-sm text-muted-foreground">Additional settings are managed in DockFlare Master.</p>
  </div>
</template>
