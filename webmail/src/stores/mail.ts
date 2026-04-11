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
  const isComposeFullView = ref(false)
  const composeDefaults = ref<{ to?: string; subject?: string; body?: string; quotedHtml?: string; draftId?: number } | null>(null)
  const composeBody = ref('')
  const activeTab = ref<'all' | 'unread' | 'starred'>('all')
  const isCollapsed = ref(false)
  const sortOrder = ref<'asc' | 'desc'>('desc')
  const isDark = ref(localStorage.getItem('theme') === 'dark')
  const viewMode = ref<'split' | 'full'>((localStorage.getItem('viewMode') as 'split' | 'full') || 'split')

  const unreadMessages = computed(() =>
    messages.value.filter((m: any) => !m.is_read)
  )

  const starredMessages = computed(() =>
    messages.value.filter((m: any) => m.is_starred)
  )

  const currentFolderObj = computed(() =>
    folders.value.find((f: any) => f.name === currentFolder.value) || null
  )

  function toggleTheme() {
    isDark.value = !isDark.value
    if (isDark.value) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  function toggleViewMode() {
    viewMode.value = viewMode.value === 'split' ? 'full' : 'split'
    localStorage.setItem('viewMode', viewMode.value)
  }

  return {
    mailboxes, currentMailbox,
    folders, currentFolder, currentFolderObj,
    messages, currentMessage,
    isComposeOpen, isComposeFullView, composeDefaults, composeBody,
    activeTab, isCollapsed,
    sortOrder, isDark, toggleTheme,
    viewMode, toggleViewMode,
    unreadMessages, starredMessages,
  }
})
