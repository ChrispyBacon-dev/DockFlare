import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useMailStore = defineStore('mail', () => {
  const mailboxes = ref<any[]>([])
  const currentMailbox = ref<string>('')
  const folders = ref<any[]>([])
  const currentFolder = ref<string>('')
  const messages = ref<any[]>([])
  const currentMessage = ref<any>(null)
  const isComposeOpen = ref(false)
  const composeDefaults = ref<{ to?: string; subject?: string; body?: string } | null>(null)
  const composeBody = ref('')
  const activeTab = ref<'all' | 'unread'>('all')
  const isCollapsed = ref(false)

  const unreadMessages = computed(() =>
    messages.value.filter((m: any) => !m.is_read)
  )

  return {
    mailboxes, currentMailbox,
    folders, currentFolder,
    messages, currentMessage,
    isComposeOpen, composeDefaults, composeBody,
    activeTab, isCollapsed, unreadMessages,
  }
})
