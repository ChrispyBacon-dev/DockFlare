<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted, onMounted, type Ref, computed } from 'vue'
import { useBreakpoint } from '../../composables/useBreakpoint'
import {
  Paperclip, X, Bold as BoldIcon, Italic as ItalicIcon, Link2, List as ListIcon, ListOrdered, Minus,
  Underline as UnderlineIcon, AlignLeft as AlignLeftIcon, AlignCenter as AlignCenterIcon, AlignRight as AlignRightIcon, AlignJustify as AlignJustifyIcon,
  Quote as QuoteIcon, RemoveFormatting, Baseline, Trash2, Strikethrough as StrikethroughIcon, Type, BookmarkCheck, Maximize2, Minimize2, Smile
} from 'lucide-vue-next'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import LinkExtension from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import Typography from '@tiptap/extension-typography'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Color from '@tiptap/extension-color'
import TextStyle from '@tiptap/extension-text-style'
import Highlight from '@tiptap/extension-highlight'
import FontFamily from '@tiptap/extension-font-family'

import { mailApi } from '../../api/mail'
import { useMailStore } from '../../stores/mail'
import Button from '../ui/Button.vue'
import Input from '../ui/Input.vue'

const props = defineProps({ panelMode: { type: Boolean, default: false } })

const store = useMailStore()
const { isMobile } = useBreakpoint()
const effectivePanelMode = computed(() => props.panelMode || isMobile.value)

const _EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const toTags = ref<string[]>([])
const toInput = ref('')
const ccTags = ref<string[]>([])
const ccInput = ref('')
const bccTags = ref<string[]>([])
const bccInput = ref('')
const showCc = ref(false)
const showBcc = ref(false)

const fromAddress = ref('')
const aliases = ref<string[]>([])
const subject = ref('')
const attachments = ref<File[]>([])
const sending = ref(false)
const savingDraft = ref(false)
const savedDraft = ref(false)
const draftId = ref<number | null>(null)
const error = ref('')
const minimized = ref(false)
const showFormatting = ref(false)
const quotedHtml = ref('')

const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

const editor = useEditor({
  extensions: [
    StarterKit,
    LinkExtension.configure({ openOnClick: false }),
    Placeholder.configure({ placeholder: 'Write your message…' }),
    Typography,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
    FontFamily,
  ],
  editorProps: {
    attributes: { class: 'tiptap-editor' },
  },
  onUpdate: ({ editor }) => {
    if (store.composeDefaults !== null) {
      store.composeDefaults = { ...store.composeDefaults, body: editor.getHTML() }
    } else {
      store.composeDefaults = { body: editor.getHTML() }
    }
  },
})

const loadAliases = async () => {
  if (!store.currentMailbox) return
  try {
    const res = await mailApi.getAliases(store.currentMailbox)
    aliases.value = (res.data.aliases || []).map((a: any) => a.address)
  } catch { aliases.value = [] }
}

const reset = () => {
  toTags.value = []
  toInput.value = ''
  ccTags.value = []
  ccInput.value = ''
  bccTags.value = []
  bccInput.value = ''
  showCc.value = false
  showBcc.value = false
  fromAddress.value = store.currentMailbox || ''
  subject.value = ''
  attachments.value = []
  error.value = ''
  minimized.value = false
  draftId.value = null
  savedDraft.value = false
  quotedHtml.value = ''
  editor.value?.commands.clearContent()
  store.composeDefaults = null
}

const addTag = (tags: Ref<string[]>, input: Ref<string>) => {
  const val = input.value.trim().replace(/[,;]+$/, '')
  if (val && _EMAIL_RE.test(val) && !tags.value.includes(val)) {
    tags.value.push(val)
  }
  input.value = ''
}

const makeTagHandlers = (tags: Ref<string[]>, input: Ref<string>) => ({
  onKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',' || e.key === 'Tab') {
      e.preventDefault()
      addTag(tags, input)
    } else if (e.key === 'Backspace' && !input.value && tags.value.length) {
      tags.value.pop()
    }
  },
  onBlur() { addTag(tags, input) },
  onPaste(e: ClipboardEvent) {
    e.preventDefault()
    const text = e.clipboardData?.getData('text') || ''
    for (const addr of text.split(/[,;\s]+/)) {
      const trimmed = addr.trim()
      if (trimmed && _EMAIL_RE.test(trimmed) && !tags.value.includes(trimmed)) {
        tags.value.push(trimmed)
      }
    }
  },
})

const toHandlers = makeTagHandlers(toTags, toInput)
const ccHandlers = makeTagHandlers(ccTags, ccInput)
const bccHandlers = makeTagHandlers(bccTags, bccInput)

onMounted(loadAliases)

watch(() => store.isComposeOpen, async (open) => {
  if (open) {
    await loadAliases()
    if (store.composeDefaults) {
      const rawTo = store.composeDefaults.to || ''
      if (rawTo) {
        for (const addr of rawTo.split(',').map((s: string) => s.trim()).filter(Boolean)) {
          if (_EMAIL_RE.test(addr) && !toTags.value.includes(addr)) toTags.value.push(addr)
        }
      }
      subject.value = store.composeDefaults.subject || ''
      quotedHtml.value = store.composeDefaults.quotedHtml || ''
      if (store.composeDefaults.draftId) {
        draftId.value = store.composeDefaults.draftId
      }
      const requestedFrom = store.composeDefaults.from
      fromAddress.value = (requestedFrom && aliases.value.includes(requestedFrom))
        ? requestedFrom
        : (store.currentMailbox || '')
    } else {
      fromAddress.value = store.currentMailbox || ''
    }
    minimized.value = false
    await nextTick()
    if (store.composeDefaults?.body) {
      editor.value?.commands.setContent(store.composeDefaults.body)
    } else {
      editor.value?.commands.clearContent()
    }
  } else if (!open) {
    reset()
  }
}, { immediate: true })

onUnmounted(() => editor.value?.destroy())

const close = () => {
  store.isComposeOpen = false
  store.isComposeFullView = false
}

const toggleFullView = () => {
  store.isComposeFullView = !store.isComposeFullView
  minimized.value = false
}

const discardDraft = async () => {
  if (draftId.value && store.currentMailbox) {
    try {
      await mailApi.deleteMessage(store.currentMailbox, String(draftId.value))
      const res = await mailApi.getFolders(store.currentMailbox)
      store.folders = res.data
      if (store.currentFolder === 'Drafts') {
        store.messages = store.messages.filter((m: any) => m.id !== draftId.value)
      }
    } catch (e) {}
  }
  close()
}

const toggleMinimize = () => {
  minimized.value = !minimized.value
}

const onFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  for (const file of Array.from(input.files)) {
    if (!attachments.value.find(f => f.name === file.name && f.size === file.size)) {
      attachments.value.push(file)
    }
  }
  input.value = ''
}

const removeAttachment = (index: number) => {
  attachments.value.splice(index, 1)
}

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const showLinkPopover = ref(false)
const linkInput = ref('')

const openLinkPopover = () => {
  linkInput.value = editor.value?.getAttributes('link').href || ''
  showLinkPopover.value = true
  nextTick(() => {
    const el = document.getElementById('compose-link-input')
    el?.focus()
  })
}

const applyLink = () => {
  const url = linkInput.value.trim()
  if (!url) {
    editor.value?.chain().focus().unsetLink().run()
  } else {
    const href = url.startsWith('http') ? url : `https://${url}`
    editor.value?.chain().focus().setLink({ href }).run()
  }
  showLinkPopover.value = false
}

const onLinkKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') { e.preventDefault(); applyLink() }
  if (e.key === 'Escape') { showLinkPopover.value = false }
}

const saveDraft = async () => {
  if (!store.currentMailbox || !editor.value) return
  toHandlers.onBlur()
  savingDraft.value = true
  error.value = ''
  try {
    const payload = {
      to: toTags.value,
      cc: ccTags.value,
      bcc: bccTags.value,
      subject: subject.value,
      html_body: editor.value.getHTML() + (quotedHtml.value || ''),
      text_body: editor.value.getText(),
    }
    if (draftId.value) {
      await mailApi.updateDraft(store.currentMailbox, draftId.value, payload)
    } else {
      const res = await mailApi.createDraft(store.currentMailbox, payload)
      draftId.value = res.data.id
    }
    savedDraft.value = true
    setTimeout(() => { savedDraft.value = false }, 2000)
    const res = await mailApi.getFolders(store.currentMailbox)
    store.folders = res.data
  } catch (e: any) {
    error.value = e?.response?.data?.error || 'Failed to save draft.'
  } finally {
    savingDraft.value = false
  }
}

const send = async () => {
  if (!store.currentMailbox || !editor.value) return

  toHandlers.onBlur()
  if (!toTags.value.length) {
    error.value = 'Please add at least one recipient.'
    return
  }

  const totalSize = attachments.value.reduce((sum, f) => sum + f.size, 0)
  if (totalSize > MAX_ATTACHMENT_BYTES) {
    error.value = `Attachments exceed 10 MB limit (${formatBytes(totalSize)} total).`
    return
  }

  sending.value = true
  error.value = ''
  try {
    const html = editor.value.getHTML() + (quotedHtml.value || '')
    const text = editor.value.getText()
    const formData = new FormData()
    for (const addr of toTags.value) formData.append('to', addr)
    for (const addr of ccTags.value) formData.append('cc', addr)
    for (const addr of bccTags.value) formData.append('bcc', addr)
    formData.append('subject', subject.value)
    formData.append('html', html)
    formData.append('text', text)
    if (fromAddress.value && fromAddress.value !== store.currentMailbox) {
      formData.append('from_address', fromAddress.value)
    }
    for (const file of attachments.value) {
      formData.append('attachments', file)
    }
    await mailApi.sendMessage(store.currentMailbox, formData)
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
    close()
  } catch (e: any) {
    error.value = e?.response?.data?.error || 'Failed to send. Please try again.'
  } finally {
    sending.value = false
  }
}

const fonts = [
  { label: 'Sans Serif', value: 'Inter, ui-sans-serif, system-ui, sans-serif' },
  { label: 'Serif', value: 'ui-serif, Georgia, serif' },
  { label: 'Monospace', value: 'ui-monospace, Consolas, monospace' },
  { label: 'Comic Sans', value: '"Comic Sans MS", "Comic Sans", cursive' },
  { label: 'Garamond', value: 'Garamond, serif' },
  { label: 'Trebuchet', value: '"Trebuchet MS", sans-serif' },
]

const setFont = (e: Event) => {
  const target = e.target as HTMLSelectElement
  if (target.value) {
    editor.value?.chain().focus().setFontFamily(target.value).run()
  } else {
    editor.value?.chain().focus().unsetFontFamily().run()
  }
}

const setColor = (e: Event) => {
  const target = e.target as HTMLInputElement
  editor.value?.chain().focus().setColor(target.value).run()
}

const setHighlight = (e: Event) => {
  const target = e.target as HTMLInputElement
  editor.value?.chain().focus().setHighlight({ color: target.value }).run()
}

const showEmojiPicker = ref(false)
const emojiPickerContainer = ref<HTMLElement | null>(null)

const openEmojiPicker = async () => {
  showEmojiPicker.value = !showEmojiPicker.value
  if (!showEmojiPicker.value) return
  await nextTick()
  if (!emojiPickerContainer.value) return
  emojiPickerContainer.value.innerHTML = ''
  const { Picker } = await import('emoji-mart')
  const data = (await import('@emoji-mart/data')).default
  new Picker({
    data,
    onEmojiSelect: (emoji: any) => {
      editor.value?.chain().focus().insertContent(emoji.native).run()
      showEmojiPicker.value = false
    },
    parent: emojiPickerContainer.value,
    theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
  })
}

const onEmojiClickOutside = (e: MouseEvent) => {
  if (!emojiPickerContainer.value) return
  const wrapper = emojiPickerContainer.value.closest('.emoji-picker-wrapper')
  if (wrapper && !wrapper.contains(e.target as Node)) {
    showEmojiPicker.value = false
  }
}

watch(showEmojiPicker, (val) => {
  if (val) document.addEventListener('mousedown', onEmojiClickOutside)
  else document.removeEventListener('mousedown', onEmojiClickOutside)
})

onUnmounted(() => document.removeEventListener('mousedown', onEmojiClickOutside))
</script>

<template>
  <div
    v-if="store.isComposeOpen && (effectivePanelMode || !store.isComposeFullView)"
    :class="effectivePanelMode
      ? 'flex flex-col h-full w-full'
      : 'df-compose-popup fixed bottom-4 right-6 z-50 flex flex-col'"
    :style="!effectivePanelMode ? (minimized ? 'width:320px' : 'width:620px') : 'background: var(--df-pane-bg);'"
  >
    <!-- Panel mode title bar -->
    <div v-if="effectivePanelMode" class="h-[52px] flex items-center gap-2 px-4 border-b border-border flex-shrink-0">
      <span class="flex-1 text-base font-semibold truncate">{{ subject || 'New Message' }}</span>
      <button type="button" class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" title="Pop out" @click="toggleFullView">
        <Minimize2 class="size-4" />
      </button>
      <button type="button" class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" title="Close" @click="close">
        <X class="size-4" />
      </button>
    </div>

    <!-- Popup mode title bar -->
    <div v-else-if="!effectivePanelMode" class="flex items-center gap-2 px-4 py-3 cursor-pointer select-none flex-shrink-0" style="border-bottom: 1px solid rgba(128,128,128,0.1);" @click="toggleMinimize">
      <span class="flex-1 text-sm font-semibold text-foreground truncate">{{ subject || 'New Message' }}</span>
      <button type="button" class="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-colors" title="Full view" @click.stop="toggleFullView">
        <Maximize2 class="size-4" />
      </button>
      <button type="button" class="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-colors" title="Minimize" @click.stop="toggleMinimize">
        <Minus class="size-4" />
      </button>
      <button type="button" class="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-colors" title="Close" @click.stop="close">
        <X class="size-4" />
      </button>
    </div>

    <!-- Body -->
    <div
      v-show="effectivePanelMode || !minimized"
      :class="effectivePanelMode ? 'flex flex-col flex-1 overflow-hidden' : 'flex flex-col flex-1 overflow-hidden max-h-[80vh]'"
    >
      <!-- Fields -->
      <div class="flex flex-col border-b border-border flex-shrink-0">

        <!-- To row -->
        <div class="flex items-start border-b border-border min-h-[36px]">
          <span class="px-4 py-2 text-sm text-muted-foreground shrink-0 leading-5">To</span>
          <div class="flex flex-wrap items-center gap-1 flex-1 py-1.5 pr-2 min-w-0">
            <span
              v-for="(tag, i) in toTags" :key="tag"
              class="flex items-center gap-1 bg-muted rounded-full px-2 py-0.5 text-xs text-foreground border border-border"
            >
              {{ tag }}
              <button type="button" @click="toTags.splice(i, 1)" class="hover:text-destructive leading-none"><X :size="10" /></button>
            </span>
            <input
              v-model="toInput"
              placeholder="Add recipient…"
              class="flex-1 min-w-[120px] bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
              style="font-size: 16px;"
              @keydown="toHandlers.onKeydown"
              @blur="toHandlers.onBlur"
              @paste="toHandlers.onPaste"
            />
          </div>
          <div class="flex items-center gap-2 px-3 py-2 shrink-0">
            <button v-if="!showCc" type="button" class="text-xs text-muted-foreground hover:text-foreground transition-colors" @click="showCc = true">Cc</button>
            <button v-if="!showBcc" type="button" class="text-xs text-muted-foreground hover:text-foreground transition-colors" @click="showBcc = true">Bcc</button>
          </div>
        </div>

        <!-- Cc row -->
        <div v-if="showCc" class="flex items-start border-b border-border min-h-[36px]">
          <span class="px-4 py-2 text-sm text-muted-foreground shrink-0 leading-5">Cc</span>
          <div class="flex flex-wrap items-center gap-1 flex-1 py-1.5 pr-2 min-w-0">
            <span
              v-for="(tag, i) in ccTags" :key="tag"
              class="flex items-center gap-1 bg-muted rounded-full px-2 py-0.5 text-xs text-foreground border border-border"
            >
              {{ tag }}
              <button type="button" @click="ccTags.splice(i, 1)" class="hover:text-destructive leading-none"><X :size="10" /></button>
            </span>
            <input
              v-model="ccInput"
              placeholder="Add Cc…"
              class="flex-1 min-w-[120px] bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
              @keydown="ccHandlers.onKeydown"
              @blur="ccHandlers.onBlur"
              @paste="ccHandlers.onPaste"
            />
          </div>
        </div>

        <!-- Bcc row -->
        <div v-if="showBcc" class="flex items-start border-b border-border min-h-[36px]">
          <span class="px-4 py-2 text-sm text-muted-foreground shrink-0 leading-5">Bcc</span>
          <div class="flex flex-wrap items-center gap-1 flex-1 py-1.5 pr-2 min-w-0">
            <span
              v-for="(tag, i) in bccTags" :key="tag"
              class="flex items-center gap-1 bg-muted rounded-full px-2 py-0.5 text-xs text-foreground border border-border"
            >
              {{ tag }}
              <button type="button" @click="bccTags.splice(i, 1)" class="hover:text-destructive leading-none"><X :size="10" /></button>
            </span>
            <input
              v-model="bccInput"
              placeholder="Add Bcc…"
              class="flex-1 min-w-[120px] bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none py-0.5"
              @keydown="bccHandlers.onKeydown"
              @blur="bccHandlers.onBlur"
              @paste="bccHandlers.onPaste"
            />
          </div>
        </div>

        <!-- From row (aliases) -->
        <div v-if="aliases.length" class="flex items-center border-b border-border">
          <span class="px-4 py-2 text-sm text-muted-foreground shrink-0">From</span>
          <select v-model="fromAddress" class="flex-1 px-2 py-2 bg-transparent text-foreground focus:outline-none" style="font-size: 16px;">
            <option :value="store.currentMailbox">{{ store.currentMailbox }}</option>
            <option v-for="alias in aliases" :key="alias" :value="alias">{{ alias }} (alias)</option>
          </select>
        </div>

        <!-- Subject -->
        <input v-model="subject" placeholder="Subject" class="w-full px-4 py-2 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none" style="font-size: 16px;" />
      </div>

      <!-- Editor -->
      <EditorContent :editor="editor" class="compose-editor flex-1" />

      <!-- Attachment list -->
      <div v-if="attachments.length" class="flex flex-wrap gap-1.5 border-t border-border px-4 py-2 bg-muted/30 flex-shrink-0">
        <div v-for="(file, i) in attachments" :key="i" class="flex items-center gap-1 bg-muted text-muted-foreground text-xs rounded px-2 py-1 border border-border">
          <span class="truncate max-w-[140px]">{{ file.name }}</span>
          <span class="text-muted-foreground/60">({{ formatBytes(file.size) }})</span>
          <button type="button" @click="removeAttachment(i)" class="ml-1 hover:text-destructive"><X :size="12" /></button>
        </div>
      </div>

      <div v-if="quotedHtml" class="border-t border-border px-4 py-1.5 text-xs text-muted-foreground flex-shrink-0 select-none">
        Quoted message included
      </div>

      <div v-if="error" class="px-4 py-1 text-xs text-red-500 flex-shrink-0">{{ error }}</div>

      <!-- Formatting Toolbar -->
      <div v-if="showFormatting" class="flex flex-wrap items-center gap-1 border-t border-border bg-muted/30 px-3 py-1.5 flex-shrink-0">
        <select @change="setFont" class="text-xs bg-transparent border-none focus:ring-0 text-foreground cursor-pointer mr-1 max-w-[100px]">
          <option value="">Default Font</option>
          <option v-for="font in fonts" :key="font.value" :value="font.value">{{ font.label }}</option>
        </select>
        <div class="mx-1 h-4 w-px bg-border" />
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('bold') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleBold().run()" title="Bold"><BoldIcon class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('italic') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleItalic().run()" title="Italic"><ItalicIcon class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('underline') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleUnderline().run()" title="Underline"><UnderlineIcon class="size-3.5" /></button>
        <div class="mx-1 h-4 w-px bg-border" />
        <div class="relative group flex items-center p-1 rounded hover:bg-accent cursor-pointer" title="Text Color">
          <Baseline class="size-3.5 text-foreground" />
          <input type="color" @input="setColor" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" />
        </div>
        <div class="relative flex items-center p-1 rounded hover:bg-accent cursor-pointer" title="Background Color">
          <span class="text-xs font-bold leading-none bg-foreground text-background px-0.5 rounded-sm">ab</span>
          <input type="color" @input="setHighlight" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" />
        </div>
        <div class="mx-1 h-4 w-px bg-border" />
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive({ textAlign: 'left' }) ? 'bg-accent' : ''" @click="editor?.chain().focus().setTextAlign('left').run()" title="Align left"><AlignLeftIcon class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive({ textAlign: 'center' }) ? 'bg-accent' : ''" @click="editor?.chain().focus().setTextAlign('center').run()" title="Align center"><AlignCenterIcon class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive({ textAlign: 'right' }) ? 'bg-accent' : ''" @click="editor?.chain().focus().setTextAlign('right').run()" title="Align right"><AlignRightIcon class="size-3.5" /></button>
        <div class="mx-1 h-4 w-px bg-border" />
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('bulletList') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleBulletList().run()" title="Bullet list"><ListIcon class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('orderedList') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleOrderedList().run()" title="Ordered list"><ListOrdered class="size-3.5" /></button>
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" :class="editor?.isActive('blockquote') ? 'bg-accent' : ''" @click="editor?.chain().focus().toggleBlockquote().run()" title="Quote"><QuoteIcon class="size-3.5" /></button>
        <div class="mx-1 h-4 w-px bg-border" />
        <button type="button" class="rounded p-1 hover:bg-accent transition-colors" @click="editor?.chain().focus().unsetAllMarks().clearNodes().run()" title="Remove formatting"><RemoveFormatting class="size-3.5" /></button>
      </div>

      <!-- Bottom Action Bar -->
      <div class="flex items-center justify-between gap-2 border-t border-border px-4 py-2.5 flex-shrink-0">
        <div class="flex items-center gap-1">
          <Button as="button" type="button" size="sm" class="rounded-full px-5 font-semibold tracking-wide" style="background: #FBA612; color: white; box-shadow: 0 2px 10px rgba(251,166,18,0.32); border: none;" @click.prevent="send" :disabled="sending || (!toTags.length && !toInput)">
            {{ sending ? 'Sending…' : 'Send' }}
          </Button>
          <button type="button" class="ml-1 rounded p-1.5 transition-colors" :class="savedDraft ? 'text-green-500' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'" :disabled="savingDraft" title="Save draft" @click="saveDraft">
            <BookmarkCheck class="size-4" />
          </button>
          <div class="relative emoji-picker-wrapper">
            <button type="button" class="rounded p-1.5 transition-colors" :class="showEmojiPicker ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'" @click="openEmojiPicker" title="Insert emoji">
              <Smile class="size-4" />
            </button>
            <div v-if="showEmojiPicker" class="absolute bottom-10 left-0 z-50 shadow-xl rounded-xl overflow-hidden" ref="emojiPickerContainer" />
          </div>
          <button type="button" class="ml-1 rounded p-1.5 hover:bg-accent transition-colors" :class="showFormatting ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'" @click="showFormatting = !showFormatting" title="Formatting options">
            <Type class="size-4" />
          </button>
          <label class="cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" title="Attach files">
            <Paperclip class="size-4" />
            <input type="file" multiple class="hidden" @change="onFileChange" />
          </label>
          <div class="relative">
            <button type="button" class="rounded p-1.5 transition-colors" :class="showLinkPopover ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'" @click="openLinkPopover" title="Insert link">
              <Link2 class="size-4" />
            </button>
            <div v-if="showLinkPopover" class="absolute bottom-10 left-0 z-50 w-72 rounded-lg border border-border bg-background shadow-xl p-3 flex flex-col gap-2">
              <label class="text-xs font-medium text-muted-foreground">Insert link</label>
              <input
                id="compose-link-input"
                v-model="linkInput"
                type="url"
                placeholder="https://example.com"
                class="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                @keydown="onLinkKeydown"
              />
              <div class="flex gap-2 justify-end">
                <button type="button" class="rounded-md px-3 py-1 text-xs text-muted-foreground hover:bg-accent transition-colors" @click="showLinkPopover = false">Cancel</button>
                <button type="button" class="rounded-md px-3 py-1 text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" @click="applyLink">Apply</button>
              </div>
            </div>
          </div>
        </div>
        <button type="button" class="rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" :title="draftId ? 'Delete draft' : 'Discard'" @click="discardDraft">
          <Trash2 class="size-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<style>
.compose-editor {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.compose-editor .tiptap-editor {
  padding: 0.75rem 1rem;
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
  font-size: 0.875rem;
  outline: none;
  line-height: 1.5;
}
.compose-editor .tiptap-editor p {
  margin: 0 0 0.35em;
}
.compose-editor .tiptap-editor p.is-editor-empty:first-child::before {
  content: attr(data-placeholder);
  color: hsl(var(--muted-foreground));
  pointer-events: none;
  float: left;
  height: 0;
}
.compose-editor .tiptap-editor ul,
.compose-editor .tiptap-editor ol {
  padding-left: 1.25rem;
  margin: 0 0 0.35em;
}
.compose-editor .tiptap-editor blockquote {
  border-left: 3px solid hsl(var(--border));
  padding-left: 1rem;
  margin: 0 0 0.35em;
  color: hsl(var(--muted-foreground));
}
.compose-editor .tiptap-editor a {
  color: hsl(var(--primary));
  text-decoration: underline;
  cursor: pointer;
}

.df-compose-popup {
  background: rgba(252, 254, 255, 0.90);
  backdrop-filter: blur(32px) saturate(1.8);
  border: 1px solid rgba(255, 255, 255, 0.38);
  border-radius: 22px;
  box-shadow: 0 20px 52px rgba(0,0,0,0.13), 0 6px 18px rgba(0,0,0,0.07);
}
.dark .df-compose-popup {
  background: rgba(12, 24, 52, 0.92);
  border-color: rgba(255,255,255,0.10);
}
.dark .df-compose-popup select option {
  background: #0f1e3a;
  color: #e8edf5;
}

.compose-pop-enter-active { transition: transform 0.18s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease; }
.compose-pop-leave-active { transition: transform 0.14s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.14s ease; }
.compose-pop-enter-from  { transform: translateY(24px) scale(0.95); opacity: 0; }
.compose-pop-leave-to    { transform: translateY(24px) scale(0.95); opacity: 0; }
</style>
