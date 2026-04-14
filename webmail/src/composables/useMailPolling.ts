import { onUnmounted, ref, watch } from 'vue'
import { mailApi } from '@/api/mail'
import { useMailStore } from '@/stores/mail'

interface MailboxStatus {
  address: string
  unread_count: number
  latest_received_at: string | null
}

function updateBadge(count: number) {
  if (!('setAppBadge' in navigator)) return
  if (count > 0) {
    navigator.setAppBadge(count).catch(() => {})
  } else {
    navigator.clearAppBadge().catch(() => {})
  }
}

export function useMailPolling() {
  const mailStore = useMailStore()
  const lastSeen = ref<Record<string, string | null>>({})
  const initialized = ref(false)

  const poll = async () => {
    if (mailStore.mailboxes.length === 0) return

    try {
      const res = await mailApi.getMailboxStatus()
      const statuses: MailboxStatus[] = res.data

      const totalUnread = statuses.reduce((sum, s) => sum + s.unread_count, 0)
      updateBadge(totalUnread)

      if (!initialized.value) {
        for (const s of statuses) {
          lastSeen.value[s.address] = s.latest_received_at
        }
        initialized.value = true
        return
      }

      for (const s of statuses) {
        const prev = lastSeen.value[s.address]
        if (
          s.latest_received_at &&
          (prev === undefined || prev === null || s.latest_received_at > prev)
        ) {
          lastSeen.value[s.address] = s.latest_received_at

          if (s.address === mailStore.currentMailbox && mailStore.currentFolder) {
            try {
              const mRes = await mailApi.getMessages(s.address, {
                folder: mailStore.currentFolder,
                order: mailStore.sortOrder,
              })
              const payload = mRes.data
              mailStore.messages = Array.isArray(payload) ? payload : payload.items || []
            } catch { /* network error — skip */ }

            try {
              const fRes = await mailApi.getFolders(s.address)
              mailStore.folders = fRes.data
            } catch { /* network error — skip */ }
          }

          if (Notification.permission === 'granted') {
            fireNotification(s.address, s.unread_count)
          }
        }
      }
    } catch {
      // network error — skip
    }
  }

  const fireNotification = (address: string, unreadCount: number) => {
    const n = new Notification(address, {
      body: `${unreadCount} unread message${unreadCount !== 1 ? 's' : ''}`,
      icon: '/favicon/android-chrome-192x192.png',
      tag: address,
      data: { mailbox: address },
    })
    n.onclick = () => {
      window.focus()
      mailStore.currentMailbox = address
      n.close()
    }
  }

  watch(
    () => mailStore.mailboxes,
    (boxes) => {
      if (boxes.length > 0 && !initialized.value) poll()
    },
    { immediate: true }
  )

  const interval = setInterval(poll, 30_000)
  onUnmounted(() => clearInterval(interval))
}
