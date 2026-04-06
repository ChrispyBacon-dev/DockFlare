<script setup lang="ts">
import { computed, ref } from 'vue'
import DOMPurify from 'dompurify'
import { format } from 'date-fns'
import {
  Archive, Trash2, Reply, ReplyAll, Forward,
  MoreVertical, MailOpen, Star,
} from 'lucide-vue-next'
import {
  TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal,
} from 'radix-vue'
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuPortal,
} from 'radix-vue'
import Avatar from '../ui/Avatar.vue'
import Button from '../ui/Button.vue'
import Separator from '../ui/Separator.vue'
import Textarea from '../ui/Textarea.vue'
import AttachmentBar from './AttachmentBar.vue'
import { useMailStore } from '../../stores/mail'
import { mailApi } from '../../api/mail'

const props = defineProps({
  message: { type: Object, default: null },
})

const store = useMailStore()
const replyText = ref('')
const sendingReply = ref(false)

const safeHtml = computed(() => {
  if (!props.message?.html_body) return ''
  return DOMPurify.sanitize(props.message.html_body)
})

const quotedBody = computed(() => {
  if (!props.message) return ''
  const from = props.message.from_address || ''
  const date = props.message.received_at
    ? format(new Date(props.message.received_at), 'PPpp')
    : ''
  const original = props.message.html_body || `<pre>${props.message.text_body || ''}</pre>`
  return `<br><blockquote style="border-left:2px solid #ccc;padding-left:1em;color:#555;margin:1em 0;"><p>On ${date}, ${from} wrote:</p>${original}</blockquote>`
})

const replyTo = () => {
  if (!props.message) return
  store.composeDefaults = {
    to: props.message.from_address,
    subject: props.message.subject?.startsWith('Re:')
      ? props.message.subject
      : `Re: ${props.message.subject || ''}`,
    body: quotedBody.value,
  }
  store.isComposeOpen = true
}

const replyAll = () => {
  if (!props.message) return
  const allAddresses = [
    props.message.from_address,
    ...(JSON.parse(props.message.to_addresses || '[]')),
    ...(JSON.parse(props.message.cc_addresses || '[]')),
  ].filter((a: string) => a && a !== store.currentMailbox)
  store.composeDefaults = {
    to: allAddresses.join(', '),
    subject: props.message.subject?.startsWith('Re:')
      ? props.message.subject
      : `Re: ${props.message.subject || ''}`,
    body: quotedBody.value,
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
    body: quotedBody.value,
  }
  store.isComposeOpen = true
}

const trash = async () => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.deleteMessage(store.currentMailbox, props.message.id)
    store.messages = store.messages.filter((m: any) => m.id !== props.message!.id)
    store.currentMessage = null
  } catch (e) {
    console.error('Failed to trash message', e)
  }
}

const markUnread = async () => {
  if (!props.message || !store.currentMailbox) return
  try {
    await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_read: false })
    const idx = store.messages.findIndex((m: any) => m.id === props.message!.id)
    if (idx !== -1) store.messages[idx] = { ...store.messages[idx], is_read: 0 }
    store.currentMessage = null
  } catch (e) {
    console.error('Failed to mark unread', e)
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
  } catch (e) {
    console.error('Failed to toggle star', e)
  }
}

const sendInlineReply = async () => {
  if (!props.message || !store.currentMailbox || !replyText.value.trim()) return
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
  } catch (e) {
    console.error('Failed to send reply', e)
  } finally {
    sendingReply.value = false
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex items-center p-2">
      <div class="flex items-center gap-2">
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
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              @click="markUnread"
            >
              <MailOpen class="mr-2 size-4" />
              Mark as unread
            </DropdownMenuItem>
            <DropdownMenuItem
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent"
              @click="toggleStar"
            >
              <Star class="mr-2 size-4" />
              {{ message?.is_starred ? 'Unstar' : 'Star' }}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenuPortal>
      </DropdownMenuRoot>
    </div>

    <Separator />

    <template v-if="message">
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
        <div v-if="message.received_at" class="ml-auto text-xs text-muted-foreground">
          {{ format(new Date(message.received_at), 'PPpp') }}
        </div>
      </div>

      <Separator />

      <div class="flex-1 overflow-y-auto whitespace-pre-wrap p-4 text-sm">
        <div v-if="message.html_body" v-html="safeHtml" class="prose max-w-none dark:prose-invert"></div>
        <div v-else>{{ message.text_body }}</div>
      </div>

      <AttachmentBar :attachments="message.attachments" />

      <Separator class="mt-auto" />

      <div class="p-4">
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
