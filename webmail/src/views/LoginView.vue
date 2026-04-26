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
  <div class="flex h-screen w-screen items-center justify-center">
    <div class="df-login-card w-full max-w-sm space-y-6 p-8">
      <div class="flex flex-col items-center space-y-1 text-center">
        <img src="/logo.gif" alt="DockFlare" class="h-12 w-auto select-none mb-1" draggable="false" />
        <p class="text-sm text-muted-foreground">Webmail</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-3">
        <input
          v-model="email"
          type="email"
          placeholder="you@example.com"
          required
          class="df-login-input w-full rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[rgba(251,166,18,0.4)]"
        />
        <input
          v-model="password"
          type="password"
          placeholder="Password"
          required
          class="df-login-input w-full rounded-xl px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[rgba(251,166,18,0.4)]"
        />
        <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
        <button
          type="submit"
          class="df-login-submit w-full h-10 rounded-md text-sm font-semibold transition-all disabled:opacity-50"
          :disabled="loading"
        >
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <div class="flex items-center gap-2">
        <div class="flex-1 border-t border-border" />
        <span class="text-xs text-muted-foreground">or</span>
        <div class="flex-1 border-t border-border" />
      </div>

      <button
        class="df-login-sso w-full h-10 rounded-md text-sm font-medium transition-all"
        @click="redirectToMaster"
      >
        Admin SSO
      </button>
    </div>
  </div>
</template>

<style scoped>
.df-login-card {
  background: rgba(252, 254, 255, 0.88);
  backdrop-filter: blur(32px) saturate(1.8);
  border: 1px solid rgba(255, 255, 255, 0.38);
  border-radius: 22px;
  box-shadow: 0 20px 52px rgba(0,0,0,0.13);
}
.dark .df-login-card {
  background: rgba(12, 24, 52, 0.90);
  border-color: rgba(255, 255, 255, 0.10);
  box-shadow: 0 20px 52px rgba(0,0,0,0.50);
}

.df-login-input {
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(128, 128, 128, 0.15);
}
.dark .df-login-input {
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: hsl(210 40% 92%);
}

.df-login-submit {
  background: #FBA612;
  color: white;
  box-shadow: 0 2px 10px rgba(251, 166, 18, 0.32);
}
.df-login-submit:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(251, 166, 18, 0.45);
}

.df-login-sso {
  background: rgba(25, 68, 102, 0.10);
  color: #194466;
  border: 1px solid rgba(25, 68, 102, 0.25);
}
.df-login-sso:hover {
  background: rgba(25, 68, 102, 0.18);
}
.dark .df-login-sso {
  background: rgba(94, 177, 229, 0.10);
  color: #5EB1E5;
  border: 1px solid rgba(94, 177, 229, 0.22);
}
.dark .df-login-sso:hover {
  background: rgba(94, 177, 229, 0.18);
}
</style>
