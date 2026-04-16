<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue'
import {
  Paperclip, X, Bold as BoldIcon, Italic as ItalicIcon, Link2, List as ListIcon, ListOrdered, Minus,
  Underline as UnderlineIcon, AlignLeft as AlignLeftIcon, AlignCenter as AlignCenterIcon, AlignRight as AlignRightIcon, AlignJustify as AlignJustifyIcon,
  Quote as QuoteIcon, RemoveFormatting, Baseline, Trash2, Strikethrough as StrikethroughIcon, Type, BookmarkCheck, Maximize2, Minimize2
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

defineProps({ panelMode: { type: Boolean, default: false } })

const store = useMailStore()

const to = ref('')
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

const reset = () => {
  to.value = ''
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

watch(() => store.isComposeOpen, async (open) => {
  if (open && store.composeDefaults) {
    to.value = store.composeDefaults.to || ''
    subject.value = store.composeDefaults.subject || ''
    quotedHtml.value = store.composeDefaults.quotedHtml || ''
    if (store.composeDefaults.draftId) {
      draftId.value = store.composeDefaults.draftId
    }
    minimized.value = false
    await nextTick()
    if (store.composeDefaults.body) {
      editor.value?.commands.setContent(store.composeDefaults.body)
    } else {
      editor.value?.commands.clearContent()
    }
  } else if (!open) {
    reset()
  }
}, { immediate: true })

watch(to, (val) => {
  if (store.composeDefaults !== null) {
    store.composeDefaults = { ...store.composeDefaults, to: val }
  }
})

watch(subject, (val) => {
  if (store.composeDefaults !== null) {
    store.composeDefaults = { ...store.composeDefaults, subject: val }
  }
})

watch(quotedHtml, (val) => {
  if (store.composeDefaults !== null) {
    store.composeDefaults = { ...store.composeDefaults, quotedHtml: val }
  }
})

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

const setLink = () => {
  const prev = editor.value?.getAttributes('link').href || ''
  const url = window.prompt('Enter URL', prev)
  if (url === null) return
  if (url === '') {
    editor.value?.chain().focus().unsetLink().run()
  } else {
    editor.value?.chain().focus().setLink({ href: url }).run()
  }
}

const saveDraft = async () => {
  if (!store.currentMailbox || !editor.value) return
  savingDraft.value = true
  error.value = ''
  try {
    const payload = {
      to: to.value ? to.value.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
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
    formData.append('to', to.value)
    formData.append('subject', subject.value)
    formData.append('html', html)
    formData.append('text', text)
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
</script>

<template>
  <div
    v-if="store.isComposeOpen && (panelMode || !store.isComposeFullView)"
    :class="panelMode
      ? 'flex flex-col h-full w-full bg-background'
      : 'fixed bottom-0 right-6 z-50 flex flex-col rounded-t-xl shadow-2xl border border-border bg-background'"
    :style="!panelMode ? (minimized ? 'width:320px' : 'width:560px') : ''"
  >
    <!-- Panel mode title bar -->
    <div v-if="panelMode" class="h-[52px] flex items-center gap-2 px-4 border-b border-border flex-shrink-0">
      <span class="flex-1 text-base font-semibold truncate">{{ subject || 'New Message' }}</span>
      <button type="button" class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" title="Pop out" @click="toggleFullView">
        <Minimize2 class="size-4" />
      </button>
      <button type="button" class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" title="Close" @click="close">
        <X class="size-4" />
      </button>
    </div>

    <!-- Popup mode title bar -->
    <div v-else class="flex items-center gap-2 rounded-t-xl bg-primary px-4 py-2.5 cursor-pointer select-none" @click="toggleMinimize">
      <span class="flex-1 text-sm font-semibold text-primary-foreground truncate">{{ subject || 'New Message' }}</span>
      <button type="button" class="rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" title="Full view" @click.stop="toggleFullView">
        <Maximize2 class="size-4" />
      </button>
      <button type="button" class="rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" title="Minimize" @click.stop="toggleMinimize">
        <Minus class="size-4" />
      </button>
      <button type="button" class="rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" title="Close" @click.stop="close">
        <X class="size-4" />
      </button>
    </div>

    <!-- Body — always visible in panel mode, hidden when minimized in popup mode -->
    <div
      v-show="panelMode || !minimized"
      :class="panelMode ? 'flex flex-col flex-1 overflow-hidden' : 'flex flex-col flex-1 overflow-hidden max-h-[80vh]'"
    >
      <!-- Fields -->
      <div class="flex flex-col border-b border-border flex-shrink-0">
        <input v-model="to" placeholder="To" class="w-full border-b border-border px-4 py-2 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none" />
        <input v-model="subject" placeholder="Subject" class="w-full px-4 py-2 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none" />
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

      <!-- Formatting Toolbar (Collapsible) -->
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
      <div class="flex items-center justify-between gap-2 border-t border-border px-4 py-2.5 flex-shrink-0 bg-background">
        <div class="flex items-center gap-1">
          <Button as="button" type="button" size="sm" class="rounded-full px-5 font-semibold tracking-wide" @click.prevent="send" :disabled="sending || !to">
            {{ sending ? 'Sending…' : 'Send' }}
          </Button>
          <button type="button" class="ml-1 rounded p-1.5 transition-colors" :class="savedDraft ? 'text-green-500' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'" :disabled="savingDraft" title="Save draft" @click="saveDraft">
            <BookmarkCheck class="size-4" />
          </button>
          <button type="button" class="ml-1 rounded p-1.5 hover:bg-accent transition-colors" :class="showFormatting ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'" @click="showFormatting = !showFormatting" title="Formatting options">
            <Type class="size-4" />
          </button>
          <label class="cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" title="Attach files">
            <Paperclip class="size-4" />
            <input type="file" multiple class="hidden" @change="onFileChange" />
          </label>
          <button type="button" class="rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" @click="setLink" title="Insert link">
            <Link2 class="size-4" />
          </button>
        </div>
        <button type="button" class="rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" :title="draftId ? 'Delete draft' : 'Discard'" @click="discardDraft">
          <Trash2 class="size-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<style>
/* Tiptap editor inside compose */
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

/* Pop-up animation */
.compose-pop-enter-active { transition: transform 0.18s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease; }
.compose-pop-leave-active { transition: transform 0.14s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.14s ease; }
.compose-pop-enter-from  { transform: translateY(24px) scale(0.95); opacity: 0; }
.compose-pop-leave-to    { transform: translateY(24px) scale(0.95); opacity: 0; }
</style>
