<script setup lang="ts">
import { ref } from 'vue'
import { Paperclip, Download } from 'lucide-vue-next'
import { mailApi } from '../../api/mail'
import Button from '../ui/Button.vue'

defineProps({
  attachments: { type: Array, default: () => [] },
})

const downloading = ref<number | null>(null)

const formatSize = (bytes: number) => {
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}

const download = async (att: any) => {
  downloading.value = att.id
  try {
    const blob = await mailApi.downloadAttachment(att.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = att.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Download failed', e)
  } finally {
    downloading.value = null
  }
}
</script>

<template>
  <div v-if="attachments && attachments.length > 0" class="flex flex-wrap gap-2 border-t p-4">
    <div
      v-for="att in (attachments as any[])"
      :key="att.id"
      class="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm"
    >
      <Paperclip class="size-4 text-muted-foreground shrink-0" />
      <span class="truncate max-w-[180px]">{{ att.filename }}</span>
      <span class="text-xs text-muted-foreground whitespace-nowrap">{{ formatSize(att.size_bytes) }}</span>
      <Button
        variant="ghost"
        size="sm"
        class="h-7 w-7 p-0"
        :disabled="downloading === att.id"
        @click="download(att)"
      >
        <Download class="size-4" />
      </Button>
    </div>
  </div>
</template>
