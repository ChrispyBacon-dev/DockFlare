import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import { format as dateFnsFormat } from 'date-fns'
import type { Mailbox, Folder, Message, Toast, ComposeDefaults } from '../types/mail'

export type DateFormatKey = 'us' | 'eu' | 'iso'

const DATE_FORMATS: Record<DateFormatKey, string> = {
  us:  'PPpp',
  eu:  'dd.MM.yyyy, HH:mm:ss',
  iso: 'yyyy-MM-dd HH:mm:ss',
}

export const useMailStore = defineStore('mail', () => {
  const mailboxes = ref<Mailbox[]>([])
  const currentMailbox = ref<string>('')
  const folders = ref<Folder[]>([])
  const currentFolder = ref<string>('')
  const messages = shallowRef<Message[]>([])
  const totalMessages = ref(0)
  const hasMoreMessages = ref(false)
  const messagesPage = ref(1)
  const isFetchingNextPage = ref(false)
  const currentMessage = ref<Message | null>(null)
  const messagesLoading = ref(false)
  const isComposeOpen = ref(false)
  const isComposeFullView = ref(false)
  const isSettingsOpen = ref(false)
  const composeDefaults = ref<ComposeDefaults | null>(null)
  const composeBody = ref('')
  const activeTab = ref<'all' | 'unread' | 'starred'>('all')
  const isCollapsed = ref(false)
  const sortOrder = ref<'asc' | 'desc'>('desc')
  const isDark = ref(localStorage.getItem('theme') === 'dark')
  const dateFormat = ref<DateFormatKey>((localStorage.getItem('dateFormat') as DateFormatKey) || 'us')
  const settingsCategory = ref<string>('notifications')

  function formatDate(ts: string | null | undefined): string {
    if (!ts) return ''
    return dateFnsFormat(new Date(ts), DATE_FORMATS[dateFormat.value])
  }

  function setDateFormat(key: DateFormatKey) {
    dateFormat.value = key
    localStorage.setItem('dateFormat', key)
  }
  const viewMode = ref<'split' | 'full'>((localStorage.getItem('viewMode') as 'split' | 'full') || 'split')
  const toast = ref<Toast | null>(null)

  let toastTimer: ReturnType<typeof setTimeout> | null = null
  let _loadMore: (() => void) | null = null

  function showToast(message: string, type: Toast['type'] = 'error') {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = { message, type }
    toastTimer = setTimeout(() => { toast.value = null }, 4000)
  }

  function registerLoadMore(fn: () => void) {
    _loadMore = fn
  }

  function loadMore() {
    if (_loadMore) _loadMore()
  }

  const unreadMessages = computed(() =>
    messages.value.filter((m) => !m.is_read)
  )

  const starredMessages = computed(() =>
    messages.value.filter((m) => m.is_starred)
  )

  const currentFolderObj = computed(() =>
    folders.value.find((f) => f.name === currentFolder.value) || null
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
    messages, totalMessages, hasMoreMessages, messagesPage, isFetchingNextPage,
    currentMessage, messagesLoading,
    isComposeOpen, isComposeFullView, isSettingsOpen, composeDefaults, composeBody,
    activeTab, isCollapsed,
    sortOrder, isDark, toggleTheme,
    dateFormat, setDateFormat, formatDate,
    settingsCategory,
    viewMode, toggleViewMode,
    unreadMessages, starredMessages,
    toast, showToast,
    registerLoadMore, loadMore,
  }
})
