<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMail } from '../composables/useMail'
import { useMailPolling } from '../composables/useMailPolling'
import { useNotificationsStore } from '../stores/notifications'
import { mailApi } from '../api/mail'
import MailLayout from '../components/mail/MailLayout.vue'
import type { Message } from '../types/mail'

const route = useRoute()
const { store, loadMailboxes } = useMail()
const mailStore = store
const notificationsStore = useNotificationsStore()
useMailPolling()

const showNotifPrompt = ref(false)

let mailboxLoadSeq = 0

const loadMessages = async (addr: string, folder: string, page = 1) => {
  if (!addr || !folder) return
  if (page === 1) {
    store.messagesLoading = true
    store.messages = []
    store.messagesPage = 1
  } else {
    store.isFetchingNextPage = true
  }
  try {
    const mRes = await mailApi.getMessages(addr, { folder, order: store.sortOrder, page, per_page: 50 })
    const payload = mRes.data
    const items: any[] = Array.isArray(payload) ? payload : payload.items || []
    store.messages = page === 1 ? items : [...store.messages, ...items]
    store.totalMessages = payload.total ?? items.length
    store.messagesPage = page
    store.hasMoreMessages = items.length === 50
    if (page === 1) store.currentMessage = null
  } catch {
    store.showToast('Failed to load messages')
  } finally {
    store.messagesLoading = false
    store.isFetchingNextPage = false
  }
}

store.registerLoadMore(() => {
  if (store.hasMoreMessages && !store.isFetchingNextPage) {
    loadMessages(store.currentMailbox, store.currentFolder, store.messagesPage + 1)
  }
})

async function enableNotifications() {
  await notificationsStore.requestPermission()
  showNotifPrompt.value = false
  localStorage.setItem('notif_prompted', '1')
  if (notificationsStore.isGranted) {
    mailStore.isSettingsOpen = true
  }
}

function dismissPrompt() {
  showNotifPrompt.value = false
  localStorage.setItem('notif_prompted', '1')
}

onMounted(async () => {
  await loadMailboxes()

  const mailboxParam = route.query.mailbox as string | undefined
  if (mailboxParam) {
    const found = store.mailboxes.find((b) => b.address === mailboxParam)
    if (found) store.currentMailbox = mailboxParam
  }

  if (Notification.permission === 'default' && !localStorage.getItem('notif_prompted')) {
    showNotifPrompt.value = true
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (ev: MessageEvent) => {
      if (ev.data?.type === 'NOTIFICATION_CLICK' && ev.data.mailbox) {
        store.currentMailbox = ev.data.mailbox
      }
      if (ev.data?.type === 'SET_BADGE') {
        const count: number = ev.data.count ?? 0
        if ('setAppBadge' in navigator) {
          if (count > 0) {
            navigator.setAppBadge(count).catch(() => {})
          } else {
            navigator.clearAppBadge().catch(() => {})
          }
        }
      }
    })
  }
})

watch(() => store.currentMailbox, async (addr) => {
  if (!addr) return
  const seq = ++mailboxLoadSeq
  try {
    const fRes = await mailApi.getFolders(addr)
    if (seq !== mailboxLoadSeq) return
    store.folders = fRes.data
    if (store.folders.length > 0) {
      const inbox = store.folders.find((f) => f.name.toLowerCase() === 'inbox')
      store.currentFolder = inbox ? inbox.name : store.folders[0].name
    }
  } catch {
    if (seq !== mailboxLoadSeq) return
    store.showToast('Failed to load folders')
  }
})

watch(() => [store.currentMailbox, store.currentFolder], ([addr, folder]) => {
  loadMessages(addr as string, folder as string)
})

watch(() => store.sortOrder, () => {
  loadMessages(store.currentMailbox, store.currentFolder)
})

let openedMessageId: string | null = null

watch(() => store.currentMessage, async (msg) => {
  if (!msg) return
  try {
    const idx = store.messages.findIndex((m) => m.id === msg.id)
    let fullMsg = msg

    const isUserOpen = msg.attachments === undefined || msg.id !== openedMessageId

    if (msg.attachments === undefined) {
      const res = await mailApi.getMessage(store.currentMailbox, msg.id)
      fullMsg = res.data
      store.currentMessage = fullMsg
      if (idx !== -1) store.messages[idx] = fullMsg
    }

    if (!fullMsg.is_read && isUserOpen) {
      openedMessageId = msg.id
      await mailApi.updateMessage(store.currentMailbox, msg.id, { is_read: true })
      if (idx !== -1) {
        store.messages[idx] = { ...store.messages[idx], is_read: 1 }
      }
      store.currentMessage = { ...store.currentMessage!, is_read: 1 } as Message
      const fRes = await mailApi.getFolders(store.currentMailbox)
      store.folders = fRes.data
    } else {
      openedMessageId = msg.id
    }
  } catch {
    store.showToast('Failed to load message')
  }
})
</script>

<template>
  <div class="relative h-full">
    <MailLayout />

    <Transition name="slide-up">
      <div
        v-if="showNotifPrompt"
        class="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-xl border bg-background shadow-lg px-5 py-3.5 text-sm"
      >
        <span class="text-muted-foreground">Enable notifications for new mail?</span>
        <button
          class="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          @click="enableNotifications"
        >
          Enable
        </button>
        <button
          class="text-muted-foreground hover:text-foreground transition-colors"
          @click="dismissPrompt"
        >
          Dismiss
        </button>
      </div>
    </Transition>

    <Transition name="slide-up">
      <div
        v-if="store.toast"
        class="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-xl border px-5 py-3.5 text-sm shadow-lg"
        :class="store.toast.type === 'error'
          ? 'bg-destructive text-destructive-foreground border-destructive'
          : store.toast.type === 'success'
            ? 'bg-green-600 text-white border-green-700'
            : 'bg-background text-foreground border-border'"
      >
        {{ store.toast.message }}
      </div>
    </Transition>
  </div>
</template>
