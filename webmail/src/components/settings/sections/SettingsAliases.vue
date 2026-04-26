<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMailStore } from '@/stores/mail'
import { mailApi } from '@/api/mail'
import type { Alias } from '@/types/mail'

const mailStore = useMailStore()

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

const confirmTarget = ref<Alias | null>(null)
const confirmLoading = ref(false)

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

watch(() => mailStore.currentMailbox, (addr) => { if (addr) loadAliases(addr) }, { immediate: true })

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

function promptDelete(alias: Alias) {
  confirmTarget.value = alias
}

async function confirmDelete() {
  if (!confirmTarget.value) return
  const alias = confirmTarget.value
  confirmLoading.value = true
  try {
    await mailApi.deleteAlias(alias.address)
    alAliases.value = alAliases.value.filter(a => a.address !== alias.address)
    confirmTarget.value = null
  } catch { /* ignore */ } finally {
    confirmLoading.value = false
  }
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString()
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Email Aliases</h2>
      <p class="text-sm text-muted-foreground mt-1">Create aliases that forward mail to your mailbox while keeping your real address private.</p>
    </div>

    <div v-if="!mailStore.currentMailbox" class="text-sm text-muted-foreground">No mailbox selected.</div>

    <template v-else>
      <div v-if="alLoading" class="text-sm text-muted-foreground">Loading…</div>

      <template v-else>
        <!-- Existing aliases -->
        <div v-if="alAliases.length" class="rounded-lg border overflow-hidden">
          <div
            v-for="alias in alAliases"
            :key="alias.address"
            class="flex items-center gap-3 px-4 py-3 bg-background text-sm border-b last:border-b-0"
          >
            <div class="flex-1 min-w-0">
              <div class="font-mono text-xs truncate">{{ alias.address }}</div>
              <div class="flex items-center gap-2 mt-0.5 flex-wrap">
                <span v-if="alias.label" class="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{{ alias.label }}</span>
                <span v-if="alias.expires_at" class="text-xs text-muted-foreground">Expires {{ fmtDate(alias.expires_at) }}</span>
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
              <span class="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform duration-200" :class="alias.is_active ? 'translate-x-4' : 'translate-x-0'" />
            </button>
            <button class="text-muted-foreground hover:text-destructive transition-colors text-xs" @click="promptDelete(alias)">Delete</button>
          </div>
        </div>
        <p v-else class="text-sm text-muted-foreground">No aliases yet.</p>

        <!-- Create alias -->
        <div class="rounded-lg border p-4 space-y-3">
          <p class="text-sm font-medium">Create alias</p>
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
            >{{ alGenerating ? '…' : 'Generate' }}</button>
          </div>
          <input v-model="alNewLabel" type="text" placeholder="Label (optional)" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <input v-model="alNewDescription" type="text" placeholder="Description (optional)" maxlength="200" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input v-model="alNeverExpire" type="checkbox" class="rounded border-border" />
              Never expire
            </label>
            <input v-if="!alNeverExpire" v-model="alNewExpires" type="date" class="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>

          <p v-if="alError" class="text-xs text-destructive">{{ alError }}</p>
          <p v-if="alSuccess" class="text-xs text-green-600 dark:text-green-400">{{ alSuccess }}</p>

          <button
            :disabled="alCreateLoading || !alNewAddress"
            class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            @click="createAlias"
          >{{ alCreateLoading ? 'Creating…' : 'Create Alias' }}</button>
        </div>
      </template>
    </template>

    <!-- Delete confirmation modal -->
    <Teleport to="body">
      <Transition name="al-fade">
        <div
          v-if="confirmTarget"
          class="fixed inset-0 z-[60] flex items-center justify-center"
          style="background: rgba(20,30,60,0.28); backdrop-filter: blur(4px);"
          @click.self="confirmTarget = null"
        >
          <div class="al-modal w-full max-w-sm mx-4 rounded-xl border p-5 space-y-4 shadow-xl" style="background: var(--df-pane-bg, hsl(var(--background)));">
            <p class="text-sm font-semibold">Delete alias?</p>
            <p class="text-xs text-muted-foreground font-mono break-all">{{ confirmTarget.address }}</p>
            <p class="text-xs text-muted-foreground">This cannot be undone.</p>
            <div class="flex gap-2 pt-1">
              <button
                :disabled="confirmLoading"
                class="inline-flex items-center justify-center rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50"
                @click="confirmDelete"
              >{{ confirmLoading ? 'Deleting…' : 'Delete' }}</button>
              <button
                :disabled="confirmLoading"
                class="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
                @click="confirmTarget = null"
              >Cancel</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.dark input, .dark textarea {
  background-color: hsl(var(--muted)) !important;
  color: hsl(var(--foreground));
}
.dark input::placeholder {
  color: hsl(var(--muted-foreground)); opacity: 1;
}
.dark .al-modal {
  background: hsl(var(--card)) !important;
  border-color: rgba(255,255,255,0.08) !important;
}
.al-fade-enter-active,
.al-fade-leave-active {
  transition: opacity 0.15s ease;
}
.al-fade-enter-from,
.al-fade-leave-to {
  opacity: 0;
}
</style>
