<script setup lang="ts">
import { computed, ref, watch, nextTick, onUnmounted } from 'vue'
import DOMPurify from 'dompurify'
import { format } from 'date-fns'
import {
  Archive, Trash2, Reply, ReplyAll, Forward,
  MoreVertical, MailOpen, Star, Printer, FolderInput,
  ArrowLeft, Columns, Maximize
} from 'lucide-vue-next'
import {
  TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal,
} from 'radix-vue'
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator, DropdownMenuPortal,
  DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent,
} from 'radix-vue'
import Avatar from '../ui/Avatar.vue'
import Button from '../ui/Button.vue'
import Separator from '../ui/Separator.vue'
import Textarea from '../ui/Textarea.vue'
import AttachmentBar from './AttachmentBar.vue'
import { useMailStore } from '../../stores/mail'
import { mailApi } from '../../api/mail'
import type { Message } from '../../types/mail'

const props = defineProps({
  message: { type: Object, default: null },
})

const store = useMailStore()
const replyText = ref('')
const sendingReply = ref(false)

const emailIframe = ref<HTMLIFrameElement | null>(null)

const safeHtml = computed(() => {
  if (!props.message?.html_body) return ''
  const body = DOMPurify.sanitize(props.message.html_body, { USE_PROFILES: { html: true } })
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.5; color: #1a1a1a; word-break: break-word; }
    img { max-width: 100%; height: auto; }
    a { color: #2563eb; }
    pre, code { white-space: pre-wrap; word-break: break-all; }
    table { border-collapse: collapse; }
    /* Let email-internal containers expand to fill available width */
    body > table, body > div, body > center { width: 100% !important; max-width: 100% !important; }
  </style></head><body>${body}</body></html>`
})

const resizeIframe = () => {
  const iframe = emailIframe.value
  if (!iframe) return
  try {
    const doc = iframe.contentDocument || iframe.contentWindow?.document
    if (doc) {
      // Reset first so shrinking also works correctly
      iframe.style.height = '0px'
      iframe.style.height = doc.documentElement.scrollHeight + 'px'
    }
  } catch {}
}

// Re-measure when message changes
watch(() => props.message?.id, async () => {
  await nextTick()
  resizeIframe()
})

// Re-measure whenever the iframe's container is resized (panel drag)
let resizeObserver: ResizeObserver | null = null

watch(emailIframe, (el) => {
  resizeObserver?.disconnect()
  if (!el) return
  resizeObserver = new ResizeObserver(() => resizeIframe())
  // Observe the iframe's parent (the scrollable container) for width changes
  if (el.parentElement) resizeObserver.observe(el.parentElement)
})

onUnmounted(() => resizeObserver?.disconnect())

const displayTimestamp = computed(() => {
  const ts = props.message?.received_at || props.message?.sent_at
  return ts ? format(new Date(ts), 'PPpp') : ''
})

const quotedBody = computed(() => {
  if (!props.message) return ''
  const from = props.message.from_address || ''
  const date = (props.message.received_at || props.message.sent_at)
    ? format(new Date(props.message.received_at || props.message.sent_at), 'PPpp')
    : ''
  const original = props.message.html_body || `<pre>${props.message.text_body || ''}</pre>`
  return `<br><blockquote style="border-left:2px solid #ccc;padding-left:1em;color:#555;margin:1em 0;"><p>On ${date}, ${from} wrote:</p>${original}</blockquote>`
})

const otherFolders = computed(() =>
  store.folders.filter((f: any) => f.name !== store.currentFolder)
)

const replyTo = () => {
  if (!props.message) return
  store.composeDefaults = {
    to: props.message.from_address,
    subject: props.message.subject?.startsWith('Re:')
      ? props.message.subject
      : `Re: ${props.message.subject || ''}`,
    body: '',
    quotedHtml: quotedBody.value,
  }
  store.isComposeOpen = true
}

const replyAll = () => {
  if (!props.message) return
  let toList: string[] = []
  let ccList: string[] = []
  try { toList = JSON.parse(props.message.to_addresses || '[]') } catch { toList = [] }
  try { ccList = JSON.parse(props.message.cc_addresses || '[]') } catch { ccList = [] }
  const allAddresses = [
    props.message.from_address,
    ...toList,
    ...ccList,
  ].filter((a: string) => a && a !== store.currentMailbox)
  store.composeDefaults = {
    to: allAddresses.join(', '),
    subject: props.message.subject?.startsWith('Re:')
      ? props.message.subject
      : `Re: ${props.message.subject || ''}`,
    body: '',
    quotedHtml: quotedBody.value,
  }
  store.isComposeOpen = true
}

const forwardMsg = () => {
  if (!props.message) return
  store.composeDefaults = {
    to: '',
    subject: props.message.subject?.startsWith('Fwd:')
      ? props.message.subject
      : `Fwd: ${props.message.subject || ''}`,
    body: '',
    quotedHtml: quotedBody.value,
  }
  store.isComposeOpen = true
}

const backToList = () => {
  store.currentMessage = null
}

const trash = async () => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.deleteMessage(store.currentMailbox, props.message.id)
    store.messages = store.messages.filter((m: any) => m.id !== props.message!.id)
    store.currentMessage = null
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
  } catch {
    store.showToast('Failed to move message to trash')
  }
}

const markUnread = async () => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_read: false })
    const idx = store.messages.findIndex((m: any) => m.id === props.message!.id)
    if (idx !== -1) store.messages[idx] = { ...store.messages[idx], is_read: 0 }
    store.currentMessage = { ...store.currentMessage!, is_read: 0 } as Message
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
  } catch {
    store.showToast('Failed to mark as unread')
  }
}

const markRead = async () => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_read: true })
    const idx = store.messages.findIndex((m: any) => m.id === props.message!.id)
    if (idx !== -1) store.messages[idx] = { ...store.messages[idx], is_read: 1 }
    store.currentMessage = { ...store.currentMessage!, is_read: 1 } as Message
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
  } catch {
    store.showToast('Failed to mark as read')
  }
}

const toggleStar = async () => {
  if (!props.message || !store.currentMailbox) return
  const newVal = props.message.is_starred ? 0 : 1
  try {
    await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_starred: newVal })
    const idx = store.messages.findIndex((m: any) => m.id === props.message!.id)
    if (idx !== -1) store.messages[idx] = { ...store.messages[idx], is_starred: newVal }
    if (store.currentMessage) store.currentMessage = { ...store.currentMessage, is_starred: newVal }
  } catch {
    store.showToast('Failed to update star')
  }
}

const moveToFolder = async (targetFolder: any) => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.moveMessages(store.currentMailbox, {
      message_ids: [props.message.id],
      folder_id: targetFolder.id,
    })
    store.messages = store.messages.filter((m: any) => m.id !== props.message!.id)
    store.currentMessage = null
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
  } catch {
    store.showToast('Failed to move message')
  }
}

const escapeHtml = (str: string) =>
  str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const printMessage = () => {
  if (!props.message) return

  const from = props.message.from_name ? `${props.message.from_name} <${props.message.from_address}>` : props.message.from_address
  let toRaw: string[] = []
  try { toRaw = JSON.parse(props.message.to_addresses || '[]') } catch { toRaw = [] }
  const to = Array.isArray(toRaw) ? toRaw.join(', ') : String(toRaw)
  const date = displayTimestamp.value
  const subject = props.message.subject || '(No Subject)'
  
  let content = ''
  if (props.message.html_body) {
    content = emailIframe.value?.contentDocument?.body.innerHTML || props.message.html_body
  } else {
    content = `<pre style="white-space: pre-wrap; font-family: inherit;">${props.message.text_body || ''}</pre>`
  }

  const printWindow = window.open('', '_blank')
  if (!printWindow) return

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${subject} - DockFlare Mail</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 40px; line-height: 1.5; color: #000; }
          .header { border-bottom: 1px solid #ccc; padding-bottom: 15px; margin-bottom: 25px; }
          .subject { font-size: 24px; font-weight: bold; margin: 0 0 15px 0; }
          .meta { font-size: 14px; color: #444; margin: 4px 0; display: flex; }
          .label { font-weight: bold; color: #666; width: 60px; flex-shrink: 0; }
          .val { flex: 1; }
          .content { margin-top: 20px; font-size: 14px; }
          img { max-width: 100%; height: auto; }
          a { color: #2563eb; text-decoration: none; }
          @media print {
            body { padding: 0; }
            @page { margin: 1cm; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1 class="subject">${escapeHtml(subject)}</h1>
          <div class="meta"><div class="label">From:</div><div class="val">${escapeHtml(from)}</div></div>
          <div class="meta"><div class="label">To:</div><div class="val">${escapeHtml(to)}</div></div>
          <div class="meta"><div class="label">Date:</div><div class="val">${date}</div></div>
        </div>
        <div class="content">
          ${content}
        </div>
      </body>
    </html>
  `)
  printWindow.document.close()
  
  setTimeout(() => {
    printWindow.focus()
    printWindow.print()
  }, 500)

  printWindow.onafterprint = () => {
    printWindow.close()
  }
}

const sendInlineReply = async () => {
  if (!props.message || !store.currentMailbox || !replyText.value.trim()) return
  if (!props.message.from_address) return
  sendingReply.value = true
  try {
    await mailApi.sendMessage(store.currentMailbox, {
      to: props.message.from_address,
      subject: props.message.subject?.startsWith('Re:')
        ? props.message.subject
        : `Re: ${props.message.subject || ''}`,
      text: replyText.value,
      html: replyText.value.replace(/\n/g, '<br>'),
      in_reply_to: props.message.message_id,
    })
    replyText.value = ''
  } catch {
    store.showToast('Failed to send reply')
  } finally {
    sendingReply.value = false
  }
}
</script>

<template>
  <div class="flex h-full flex-col" id="print-message-area">
    <div class="h-[52px] flex items-center px-2 flex-shrink-0 print-hide">
      <div class="flex items-center gap-2">
        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" @click="backToList">
              <ArrowLeft class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Back to list
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <Separator orientation="vertical" class="mx-1 h-6" />

        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :disabled="!message" @click="trash">
              <Trash2 class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Move to trash
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :disabled="!message" @click="printMessage">
              <Printer class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Print
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" @click="store.toggleViewMode()">
              <Columns v-if="store.viewMode === 'full'" class="size-4" />
              <Maximize v-else class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              {{ store.viewMode === 'full' ? 'Split view' : 'Full view' }}
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <Separator orientation="vertical" class="mx-1 h-6" />
      </div>

      <div class="ml-auto flex items-center gap-2">
        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :disabled="!message" @click="replyTo">
              <Reply class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Reply
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :disabled="!message" @click="replyAll">
              <ReplyAll class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Reply all
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :disabled="!message" @click="forwardMsg">
              <Forward class="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Forward
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>
      </div>

      <Separator orientation="vertical" class="mx-2 h-6" />

      <DropdownMenuRoot>
        <DropdownMenuTrigger as-child>
          <Button variant="ghost" size="icon" :disabled="!message">
            <MoreVertical class="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuPortal>
          <DropdownMenuContent
            align="end"
            class="z-50 min-w-[160px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
          >
            <DropdownMenuItem
              v-if="props.message?.is_read"
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              @click="markUnread"
            >
              <MailOpen class="mr-2 size-4" />
              Mark as unread
            </DropdownMenuItem>
            <DropdownMenuItem
              v-else
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              @click="markRead"
            >
              <MailOpen class="mr-2 size-4" />
              Mark as read
            </DropdownMenuItem>
            <DropdownMenuItem
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              @click="toggleStar"
            >
              <Star class="mr-2 size-4" />
              {{ message?.is_starred ? 'Unstar' : 'Star' }}
            </DropdownMenuItem>
            <DropdownMenuSeparator class="my-1 h-px bg-border" />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger
                class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              >
                <FolderInput class="mr-2 size-4" />
                Move to…
              </DropdownMenuSubTrigger>
              <DropdownMenuPortal>
                <DropdownMenuSubContent
                  class="z-50 min-w-[140px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
                >
                  <DropdownMenuItem
                    v-for="f in otherFolders"
                    :key="f.id"
                    class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
                    @click="moveToFolder(f)"
                  >
                    <span v-if="f.color" class="mr-2 inline-block h-2 w-2 rounded-full flex-shrink-0" :style="`background:${f.color}`" />
                    {{ f.name }}
                  </DropdownMenuItem>
                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenuPortal>
      </DropdownMenuRoot>
    </div>

    <template v-if="message">
      <!-- Print header (only visible when printing) -->
      <div class="print-header hidden print:block p-4 border-b">
        <div class="text-lg font-bold">{{ message.subject }}</div>
        <div class="text-sm text-muted-foreground mt-1">From: {{ message.from_name ? `${message.from_name} <${message.from_address}>` : message.from_address }}</div>
        <div class="text-sm text-muted-foreground">Date: {{ displayTimestamp }}</div>
      </div>

      <div class="flex items-start p-4">
        <div class="flex items-start gap-4 text-sm">
          <Avatar :initials="message.from_name?.[0] || message.from_address?.[0] || '?'" />
          <div class="grid gap-1">
            <div class="font-semibold">{{ message.from_name || message.from_address }}</div>
            <div class="line-clamp-1 text-xs">{{ message.subject }}</div>
            <div class="line-clamp-1 text-xs">
              <span class="font-medium">Reply-To:</span> {{ message.from_address }}
            </div>
          </div>
        </div>
        <div v-if="displayTimestamp" class="ml-auto text-xs text-muted-foreground">
          {{ displayTimestamp }}
        </div>
      </div>

      <Separator />

      <div class="flex-1 overflow-y-auto">
        <iframe
          v-if="message.html_body"
          ref="emailIframe"
          :srcdoc="safeHtml"
          sandbox="allow-same-origin allow-popups"
          referrerpolicy="no-referrer"
          class="w-full border-0 block"
          style="min-height: 200px"
          @load="resizeIframe"
        />
        <div v-else class="p-4 text-sm whitespace-pre-wrap">{{ message.text_body }}</div>
      </div>

      <AttachmentBar :attachments="message.attachments" />

      <Separator class="mt-auto print-hide" />

      <div class="p-4 print-hide">
        <form @submit.prevent="sendInlineReply">
          <div class="grid gap-4">
            <Textarea
              v-model="replyText"
              class="p-4 min-h-[100px]"
              :placeholder="`Reply ${message.from_name || message.from_address}...`"
            />
            <div class="flex items-center">
              <Button
                type="submit"
                size="sm"
                class="ml-auto"
                :disabled="sendingReply || !replyText.trim()"
              >
                {{ sendingReply ? 'Sending...' : 'Send' }}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </template>

    <div v-else class="flex flex-1 items-center justify-center p-8 text-muted-foreground">
      No message selected
    </div>
  </div>
</template>
