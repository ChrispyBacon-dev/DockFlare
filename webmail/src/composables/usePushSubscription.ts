import { ref } from 'vue'
import apiClient from '@/api/client'
import { useMailStore } from '@/stores/mail'

const isSupported = typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'))
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

export function usePushSubscription() {
  const isSubscribed = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const mailStore = useMailStore()

  const checkSubscription = async () => {
    if (!isSupported) return
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    isSubscribed.value = !!sub
  }

  const subscribe = async () => {
    if (!isSupported) return
    isLoading.value = true
    error.value = null
    try {
      const { data } = await apiClient.get('/notifications/vapid-key')

      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.public_key),
      })
      const subJson = sub.toJSON()

      let addresses: string[] = mailStore.mailboxes.map((m: any) => m.address)
      if (addresses.length === 0) {
        const statusRes = await apiClient.get('/mailboxes/status')
        addresses = (statusRes.data as any[]).map((s) => s.address)
      }

      if (addresses.length === 0) {
        error.value = 'No mailboxes found'
        return
      }

      for (const address of addresses) {
        await apiClient.post('/notifications/subscribe', {
          endpoint: subJson.endpoint,
          keys: subJson.keys,
          mailbox_address: address,
        })
      }
      isSubscribed.value = true
    } catch (err: any) {
      console.error('Push subscribe failed:', err)
      error.value = err?.message ?? 'Subscription failed'
    } finally {
      isLoading.value = false
    }
  }

  const unsubscribe = async () => {
    if (!isSupported) return
    isLoading.value = true
    error.value = null
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await apiClient.delete('/notifications/subscribe', {
          data: { endpoint: sub.endpoint },
        })
        await sub.unsubscribe()
      }
      isSubscribed.value = false
    } catch (err: any) {
      console.error('Push unsubscribe failed:', err)
      error.value = err?.message ?? 'Unsubscribe failed'
    } finally {
      isLoading.value = false
    }
  }

  checkSubscription()

  return { isSubscribed, isLoading, isSupported, error, subscribe, unsubscribe }
}
