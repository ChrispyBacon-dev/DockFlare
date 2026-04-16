<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { authApi } from '../api/auth'
import Button from '../components/ui/Button.vue'

const route = useRoute()
const { login } = useAuth()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

onMounted(() => {
  const token = route.query.token as string
  if (token) {
    login(token)
  }
})

const getMasterUrl = async (): Promise<string> => {
  let url = import.meta.env.VITE_MASTER_URL as string
  if (!url) {
    try {
      const cfg = await fetch('/config.json').then(r => r.json())
      url = cfg.masterUrl
    } catch {}
  }
  return url || window.location.origin.replace('mail.', '')
}

const handleLogin = async () => {
  error.value = ''
  loading.value = true
  try {
    const data = await authApi.loginWithPassword(email.value, password.value)
    if (data.success && data.token) {
      login(data.token)
    } else {
      error.value = data.error || 'Invalid email or password'
    }
  } catch {
    error.value = 'Connection error. Please try again.'
  } finally {
    loading.value = false
  }
}

const redirectToMaster = async () => {
  const masterUrl = await getMasterUrl()
  window.location.href = `${masterUrl}/email/sso/callback?return_to=${window.location.hostname}`
}
</script>

<template>
  <div class="flex h-screen w-screen items-center justify-center bg-background">
    <div class="w-full max-w-sm space-y-6 rounded-lg border p-8 shadow-sm">
      <div class="flex flex-col space-y-2 text-center">
        <h1 class="text-2xl font-semibold tracking-tight">Login to Webmail</h1>
        <p class="text-sm text-muted-foreground">Sign in with your email and password</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-3">
        <input
          v-model="email"
          type="email"
          placeholder="you@example.com"
          required
          class="input input-bordered w-full"
        />
        <input
          v-model="password"
          type="password"
          placeholder="Password"
          required
          class="input input-bordered w-full"
        />
        <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
        <Button type="submit" class="w-full" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </Button>
      </form>

      <div class="flex items-center gap-2">
        <div class="flex-1 border-t" />
        <span class="text-xs text-muted-foreground">or</span>
        <div class="flex-1 border-t" />
      </div>

      <Button variant="outline" class="w-full" @click="redirectToMaster">
        Admin SSO
      </Button>
    </div>
  </div>
</template>
