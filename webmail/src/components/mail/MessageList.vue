<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import {
  TabsRoot, TabsList, TabsTrigger, TabsContent,
} from 'radix-vue'
import {
  ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb,
} from 'radix-vue'
import { useMailStore } from '../../stores/mail'
import MessageListItem from './MessageListItem.vue'
import Separator from '../ui/Separator.vue'
import Input from '../ui/Input.vue'

const store = useMailStore()
const searchValue = ref('')
let searchTimeout: ReturnType<typeof setTimeout>

const filteredMessages = computed(() => {
  const q = searchValue.value.trim().toLowerCase()
  if (!q) return store.messages
  return store.messages.filter((m: any) =>
    (m.from_name || '').toLowerCase().includes(q) ||
    (m.from_address || '').toLowerCase().includes(q) ||
    (m.subject || '').toLowerCase().includes(q) ||
    (m.text_body || '').toLowerCase().includes(q)
  )
})

const unreadMessages = computed(() =>
  filteredMessages.value.filter((m: any) => !m.is_read)
)

const displayMessages = computed(() =>
  store.activeTab === 'unread' ? unreadMessages.value : filteredMessages.value
)

const selectMessage = (msg: any) => {
  store.currentMessage = msg
}
</script>

<template>
  <TabsRoot v-model="store.activeTab" class="flex h-full flex-col">
    <div class="flex items-center px-4 py-2">
      <h1 class="text-xl font-bold">{{ store.currentFolder || 'Inbox' }}</h1>
      <TabsList class="ml-auto inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground">
        <TabsTrigger
          value="all"
          class="inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow"
        >
          All mail
        </TabsTrigger>
        <TabsTrigger
          value="unread"
          class="inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow"
        >
          Unread
        </TabsTrigger>
      </TabsList>
    </div>
    <Separator />
    <div class="bg-background/95 p-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div class="relative">
        <Search class="absolute left-2 top-2.5 size-4 text-muted-foreground" />
        <Input v-model="searchValue" placeholder="Search" class="pl-8" />
      </div>
    </div>

    <TabsContent value="all" class="m-0 flex-1 overflow-hidden">
      <ScrollAreaRoot class="h-full">
        <ScrollAreaViewport class="h-full">
          <div class="flex flex-col gap-2 p-4 pt-0">
            <TransitionGroup name="list" appear>
              <MessageListItem
                v-for="msg in filteredMessages"
                :key="msg.id"
                :message="msg"
                :selected="store.currentMessage?.id === msg.id"
                @click="selectMessage(msg)"
              />
            </TransitionGroup>
            <div v-if="filteredMessages.length === 0" class="p-8 text-center text-muted-foreground">
              No messages found.
            </div>
          </div>
        </ScrollAreaViewport>
        <ScrollAreaScrollbar orientation="vertical" class="flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5">
          <ScrollAreaThumb class="relative flex-1 rounded-full bg-border" />
        </ScrollAreaScrollbar>
      </ScrollAreaRoot>
    </TabsContent>

    <TabsContent value="unread" class="m-0 flex-1 overflow-hidden">
      <ScrollAreaRoot class="h-full">
        <ScrollAreaViewport class="h-full">
          <div class="flex flex-col gap-2 p-4 pt-0">
            <TransitionGroup name="list" appear>
              <MessageListItem
                v-for="msg in unreadMessages"
                :key="msg.id"
                :message="msg"
                :selected="store.currentMessage?.id === msg.id"
                @click="selectMessage(msg)"
              />
            </TransitionGroup>
            <div v-if="unreadMessages.length === 0" class="p-8 text-center text-muted-foreground">
              No unread messages.
            </div>
          </div>
        </ScrollAreaViewport>
        <ScrollAreaScrollbar orientation="vertical" class="flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5">
          <ScrollAreaThumb class="relative flex-1 rounded-full bg-border" />
        </ScrollAreaScrollbar>
      </ScrollAreaRoot>
    </TabsContent>
  </TabsRoot>
</template>

<style scoped>
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
.list-leave-active {
  position: absolute;
}
</style>
