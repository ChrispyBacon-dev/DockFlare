<script setup lang="ts">
import { ref } from 'vue'
import { authApi } from '@/api/auth'

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
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Security</h2>
      <p class="text-sm text-muted-foreground mt-1">Manage your mailbox login credentials.</p>
    </div>

    <div class="rounded-lg border p-4 space-y-4">
      <p class="text-sm font-medium">Change Password</p>

      <div class="space-y-1.5">
        <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Current password</label>
        <input v-model="pwCurrent" type="password" autocomplete="current-password" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
      </div>

      <div class="space-y-1.5">
        <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">New password</label>
        <input v-model="pwNew" type="password" autocomplete="new-password" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
      </div>

      <div class="space-y-1.5">
        <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Confirm new password</label>
        <input v-model="pwConfirm" type="password" autocomplete="new-password" class="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
      </div>

      <p v-if="pwError" class="text-xs text-destructive">{{ pwError }}</p>
      <p v-if="pwSuccess" class="text-xs text-green-600 dark:text-green-400">{{ pwSuccess }}</p>

      <button
        :disabled="pwLoading || !pwCurrent || !pwNew || !pwConfirm"
        class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        @click="changePassword"
      >{{ pwLoading ? 'Updating…' : 'Update Password' }}</button>
    </div>
  </div>
</template>

<style scoped>
.dark input {
  background-color: hsl(var(--muted)) !important;
  color: hsl(var(--foreground));
}
</style>
