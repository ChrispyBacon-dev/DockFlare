<script setup lang="ts">
import { computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { Paperclip, Star, Check } from 'lucide-vue-next'
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue'
import { cn } from '../../lib/utils'
import Badge from '../ui/Badge.vue'
import { useMailStore } from '../../stores/mail'

const props = defineProps({
  message: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  folderColor: { type: String, default: '' },
  bulkSelectMode: { type: Boolean, default: false },
  isChecked: { type: Boolean, default: false },
})

const initials = computed(() => {
  const name = props.message.from_name || props.message.from_address || '?'
  return name.split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()
})

const store = useMailStore()

const timestamp = computed(() => props.message.received_at || props.message.sent_at)
const relativeTime = computed(() =>
  timestamp.value ? formatDistanceToNow(new Date(timestamp.value), { addSuffix: true }) : ''
)
const exactTime = computed(() => store.formatDate(timestamp.value))

const isSentOrDrafts = computed(() => {
  const name = store.currentFolderObj?.name?.toLowerCase() ?? ''
  return name === 'sent' || name === 'drafts'
})

const recipientLabel = computed(() => {
  if (!isSentOrDrafts.value) return null
  let addrs: string[] = []
  try { addrs = JSON.parse(props.message.to_addresses || '[]') } catch { addrs = [] }
  if (!addrs.length) return null
  return 'To: ' + addrs.map((a: string) => {
    const m = a.match(/<([^>]+)>/)
    return m ? m[1] : a
  }).join(', ')
})
</script>

<template>
  <button
    :class="cn(
      'df-msg-item flex items-start gap-3 rounded-xl p-3 text-left text-sm w-full',
      selected && 'df-msg-selected',
    )"
    :style="folderColor ? `border-left: 3px solid ${folderColor}; border-radius: 12px 0 0 12px;` : ''"
  >
    <!-- Bulk select checkbox -->
    <div
      v-if="bulkSelectMode"
      class="flex-shrink-0 h-5 w-5 rounded border-2 flex items-center justify-center mt-2 transition-all"
      :class="isChecked ? 'bg-[#FBA612] border-[#FBA612]' : 'border-muted-foreground/50'"
    >
      <Check v-if="isChecked" class="size-3 text-white" />
    </div>

    <!-- Avatar -->
    <div
      class="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-[13px] font-semibold text-white select-none mt-0.5"
      style="background: #194466; box-shadow: 0 2px 8px rgba(0,0,0,0.18);"
    >{{ initials }}</div>

    <!-- Content -->
    <div class="flex flex-col gap-1 min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <div class="font-semibold truncate flex-1">{{ recipientLabel ?? (message.from_name || message.from_address) }}</div>
        <span v-if="!message.is_read" class="flex-shrink-0 h-2 w-2 rounded-full bg-[#FBA612]" />
        <Star v-if="message.is_starred" class="flex-shrink-0 size-3 fill-yellow-400 text-yellow-400" />
        <TooltipRoot v-if="timestamp" :delay-duration="300">
          <TooltipTrigger as-child>
            <div :class="cn('flex-shrink-0 text-xs cursor-default', selected ? 'text-foreground' : 'text-muted-foreground')">
              {{ relativeTime }}
            </div>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent class="z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md">
              {{ exactTime }}
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>
      </div>
      <div class="text-xs font-medium truncate">{{ message.subject }}</div>
      <div class="line-clamp-1 text-xs text-muted-foreground">
        {{ message.text_body?.substring(0, 200) || 'No content' }}
      </div>
      <div v-if="message.has_attachments" class="flex items-center gap-1">
        <Badge variant="secondary" class="gap-1">
          <Paperclip class="size-3" />
          Attachment
        </Badge>
      </div>
    </div>
  </button>
</template>

<style scoped>
.df-msg-item {
  background: transparent;
  transition: background 0.14s, box-shadow 0.14s, transform 0.14s;
}
.df-msg-item:hover {
  background: rgba(255,255,255,0.82);
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
.dark .df-msg-item:hover {
  background: rgba(94, 177, 229, 0.08);
}
.df-msg-selected {
  background: rgba(255,255,255,0.96);
  box-shadow: 0 4px 18px rgba(0,0,0,0.10), 0 1px 5px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
.dark .df-msg-selected {
  background: rgba(94, 177, 229, 0.12);
}
</style>
