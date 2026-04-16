<script setup lang="ts">
import { computed } from 'vue'
import { Mail, ChevronDown, Check } from 'lucide-vue-next'
import {
  SelectRoot, SelectTrigger, SelectValue, SelectContent,
  SelectItem, SelectItemText, SelectItemIndicator,
  SelectPortal, SelectViewport,
} from 'radix-vue'
import { cn } from '../../lib/utils'
import { useMailStore } from '../../stores/mail'

defineProps({
  isCollapsed: { type: Boolean, default: false },
})

const store = useMailStore()

const selected = computed({
  get: () => store.currentMailbox,
  set: (val) => { store.currentMailbox = val },
})

const currentDisplay = computed(() => {
  const mb = store.mailboxes.find((m: any) => m.address === store.currentMailbox)
  return mb?.display_name || store.currentMailbox
})
</script>

<template>
  <div class="flex min-w-0">
    <SelectRoot v-model="selected">
      <SelectTrigger
        :class="cn(
          'flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring [&>span]:line-clamp-1 [&>span]:flex [&>span]:w-full [&>span]:items-center [&>span]:gap-2 [&>span]:truncate',
          isCollapsed ? 'h-9 w-9 shrink-0 justify-center p-0 [&>span]:w-auto' : 'w-full',
        )"
      >
        <SelectValue :placeholder="isCollapsed ? '' : 'Select account'">
          <div class="flex items-center gap-2">
            <Mail class="size-4 shrink-0" />
            <span v-if="!isCollapsed" class="truncate">{{ currentDisplay }}</span>
          </div>
        </SelectValue>
      </SelectTrigger>
      <SelectPortal>
        <SelectContent
          class="z-50 min-w-[220px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
          position="popper"
          :side-offset="4"
        >
          <SelectViewport>
            <SelectItem
              v-for="mb in store.mailboxes"
              :key="mb.address"
              :value="mb.address"
              class="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent focus:bg-accent"
            >
              <SelectItemIndicator class="absolute left-2">
                <Check class="size-4" />
              </SelectItemIndicator>
              <SelectItemText class="pl-6">
                <div class="flex items-center gap-2">
                  <Mail class="size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <div>{{ mb.display_name || mb.address }}</div>
                    <div class="text-xs text-muted-foreground">{{ mb.address }}</div>
                  </div>
                </div>
              </SelectItemText>
            </SelectItem>
          </SelectViewport>
        </SelectContent>
      </SelectPortal>
    </SelectRoot>
  </div>
</template>
