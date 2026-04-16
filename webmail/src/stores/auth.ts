import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { setIDBItem, removeIDBItem } from '@/lib/idb'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('jwt_token') || '')

  const isAuthenticated = computed(() => {
    if (!token.value) return false
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      return payload.exp ? payload.exp > Math.floor(Date.now() / 1000) : true
    } catch {
      return false
    }
  })

  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('jwt_token', newToken)
    setIDBItem('jwt_token', newToken).catch(() => {})
  }

  const logout = async () => {
    if ('serviceWorker' in navigator) {
      try {
        const reg = await navigator.serviceWorker.ready
        const sub = await reg.pushManager.getSubscription()
        if (sub) {
          await fetch('/api/v1/notifications/subscribe', {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token.value}`,
            },
            body: JSON.stringify({ endpoint: sub.endpoint }),
          })
          await sub.unsubscribe()
        }
      } catch { /* ignore push cleanup errors */ }
    }
    token.value = ''
    localStorage.removeItem('jwt_token')
    removeIDBItem('jwt_token').catch(() => {})
  }

  const decodeToken = () => {
    if (!token.value) return null
    try {
      const payload = token.value.split('.')[1]
      return JSON.parse(atob(payload))
    } catch {
      return null
    }
  }

  return { token, isAuthenticated, setToken, logout, decodeToken }
})
