<script setup lang="ts">
import { computed } from 'vue'
import { formatDistanceToNow, format } from 'date-fns'
import { Paperclip, Star } from 'lucide-vue-next'
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue'
import { cn } from '../../lib/utils'
import Badge from '../ui/Badge.vue'

const props = defineProps({
  message: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  folderColor: { type: String, default: '' },
})

const timestamp = computed(() => props.message.received_at || props.message.sent_at)
const relativeTime = computed(() =>
  timestamp.value ? formatDistanceToNow(new Date(timestamp.value), { addSuffix: true }) : ''
)
const exactTime = computed(() =>
  timestamp.value ? format(new Date(timestamp.value), 'PPpp') : ''
)
</script>

<template>
  <button
    :class="cn(
      'flex flex-col items-start gap-2 rounded-lg border p-3 text-left text-sm transition-all hover:bg-accent w-full',
      selected && 'bg-muted',
    )"
    :style="folderColor ? `border-left: 3px solid ${folderColor}` : ''"
  >
    <div class="flex w-full flex-col gap-1">
      <div class="flex items-center">
        <div class="flex items-center gap-2">
          <div class="font-semibold">{{ message.from_name || message.from_address }}</div>
          <span v-if="!message.is_read" class="flex h-2 w-2 rounded-full bg-primary" />
          <Star v-if="message.is_starred" class="size-3 fill-yellow-400 text-yellow-400" />
        </div>
        <TooltipRoot v-if="timestamp" :delay-duration="300">
          <TooltipTrigger as-child>
            <div
              :class="cn(
                'ml-auto text-xs cursor-default',
                selected ? 'text-foreground' : 'text-muted-foreground',
              )"
            >
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
      <div class="text-xs font-medium">{{ message.subject }}</div>
    </div>
    <div class="line-clamp-2 text-xs text-muted-foreground">
      {{ message.text_body?.substring(0, 300) || 'No content' }}
    </div>
    <div v-if="message.has_attachments" class="flex items-center gap-1">
      <Badge variant="secondary" class="gap-1">
        <Paperclip class="size-3" />
        Attachment
      </Badge>
    </div>
  </button>
</template>
