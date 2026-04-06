<script setup lang="ts">
import { formatDistanceToNow } from 'date-fns'
import { Paperclip } from 'lucide-vue-next'
import { cn } from '../../lib/utils'
import Badge from '../ui/Badge.vue'

defineProps({
  message: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})
</script>

<template>
  <button
    :class="cn(
      'flex flex-col items-start gap-2 rounded-lg border p-3 text-left text-sm transition-all hover:bg-accent',
      selected && 'bg-muted',
    )"
  >
    <div class="flex w-full flex-col gap-1">
      <div class="flex items-center">
        <div class="flex items-center gap-2">
          <div class="font-semibold">{{ message.from_name || message.from_address }}</div>
          <span v-if="!message.is_read" class="flex h-2 w-2 rounded-full bg-blue-600" />
        </div>
        <div
          :class="cn(
            'ml-auto text-xs',
            selected ? 'text-foreground' : 'text-muted-foreground',
          )"
          v-if="message.received_at"
        >
          {{ formatDistanceToNow(new Date(message.received_at), { addSuffix: true }) }}
        </div>
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
