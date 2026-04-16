<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowDownUp, Trash2 } from 'lucide-vue-next'
import {
  TabsRoot, TabsList, TabsTrigger, TabsContent,
} from 'radix-vue'
import {
  ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb,
} from 'radix-vue'
import { useMailStore } from '../../stores/mail'
import { mailApi } from '../../api/mail'
import MessageListItem from './MessageListItem.vue'
import SearchBar from './SearchBar.vue'
import Dialog from '../ui/Dialog.vue'
import Button from '../ui/Button.vue'

const store = useMailStore()
const showTrashConfirm = ref(false)

const folderColor = computed(() => store.currentFolderObj?.color || '')

const unreadMessages = computed(() =>
  store.messages.filter((m: any) => !m.is_read)
)

const starredMessages = computed(() =>
  store.messages.filter((m: any) => m.is_starred)
)

const displayMessages = computed(() => {
  let msgs = store.messages as any[]
  if (store.activeTab === 'unread') msgs = unreadMessages.value
  else if (store.activeTab === 'starred') msgs = starredMessages.value

  return [...msgs].sort((a: any, b: any) => {
    const tA = new Date(a.received_at || a.sent_at || 0).getTime()
    const tB = new Date(b.received_at || b.sent_at || 0).getTime()
    return store.sortOrder === 'desc' ? tB - tA : tA - tB
  })
})

const toggleSort = () => {
  store.sortOrder = store.sortOrder === 'desc' ? 'asc' : 'desc'
}

const selectMessage = (msg: any) => {
  if (msg.is_draft) {
    let parsed = msg.to_addresses
    if (typeof parsed === 'string') {
      try { parsed = JSON.parse(parsed) } catch { parsed = [parsed] }
    }
    const toAddr = Array.isArray(parsed) ? parsed.join(', ') : (parsed || '')
    store.composeDefaults = {
      draftId: msg.id,
      to: toAddr,
      subject: msg.subject || '',
      body: msg.html_body || msg.text_body || '',
    }
    store.isComposeOpen = true
    return
  }
  store.currentMessage = msg
}

const emptyTrash = () => {
  if (store.currentFolderObj && store.currentFolderObj.name === 'Trash') {
    showTrashConfirm.value = true
  }
}

const performEmptyTrash = async () => {
  if (!store.currentFolderObj) return
  try {
    await mailApi.emptyFolder(store.currentMailbox, store.currentFolderObj.id)
    store.messages = []
    store.currentMessage = null
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
  } catch {
    store.showToast('Failed to empty trash')
  } finally {
    showTrashConfirm.value = false
  }
}
</script>

<template>
  <TabsRoot v-model="store.activeTab" class="flex h-full flex-col">
    <div class="h-[52px] flex items-center px-4 flex-shrink-0">
      <h1 class="text-xl font-bold">{{ store.currentFolder || 'Inbox' }}</h1>
      <div class="ml-auto flex items-center gap-1">
        <button
          v-if="store.currentFolder === 'Trash' && store.messages.length > 0"
          class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors"
          title="Empty Trash"
          @click="emptyTrash"
        >
          <Trash2 class="size-4" />
        </button>
        <button
          class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          :title="store.sortOrder === 'desc' ? 'Oldest first' : 'Newest first'"
          @click="toggleSort"
        >
          <ArrowDownUp class="size-4" :class="store.sortOrder === 'asc' ? 'rotate-180' : ''" />
        </button>
        <TabsList class="inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground">
          <TabsTrigger
            value="all"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow"
          >
            All
          </TabsTrigger>
          <TabsTrigger
            value="unread"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow"
          >
            Unread
          </TabsTrigger>
          <TabsTrigger
            value="starred"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow"
          >
            Starred
          </TabsTrigger>
        </TabsList>
      </div>
    </div>
    <div class="bg-background/95 p-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <SearchBar />
    </div>

    <TabsContent value="all" class="m-0 flex-1 overflow-hidden">
      <ScrollAreaRoot class="h-full">
        <ScrollAreaViewport class="h-full">
          <div class="flex flex-col gap-2 p-4 pt-0">
            <template v-if="store.messagesLoading">
              <div v-for="n in 6" :key="n" class="h-16 rounded-lg bg-muted animate-pulse" />
            </template>
            <template v-else>
              <TransitionGroup name="list" appear>
                <MessageListItem
                  v-for="msg in displayMessages"
                  :key="msg.id"
                  :message="msg"
                  :selected="store.currentMessage?.id === msg.id"
                  :folder-color="folderColor"
                  @click="selectMessage(msg)"
                />
              </TransitionGroup>
              <div v-if="displayMessages.length === 0" class="p-8 text-center text-muted-foreground">
                No messages found.
              </div>
              <button
                v-if="store.hasMoreMessages && !store.messagesLoading"
                class="w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                :disabled="store.isFetchingNextPage"
                @click="store.loadMore()"
              >
                {{ store.isFetchingNextPage ? 'Loading…' : 'Load more' }}
              </button>
            </template>
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
            <template v-if="store.messagesLoading">
              <div v-for="n in 6" :key="n" class="h-16 rounded-lg bg-muted animate-pulse" />
            </template>
            <template v-else>
              <TransitionGroup name="list" appear>
                <MessageListItem
                  v-for="msg in displayMessages"
                  :key="msg.id"
                  :message="msg"
                  :selected="store.currentMessage?.id === msg.id"
                  :folder-color="folderColor"
                  @click="selectMessage(msg)"
                />
              </TransitionGroup>
              <div v-if="displayMessages.length === 0" class="p-8 text-center text-muted-foreground">
                No unread messages.
              </div>
              <button
                v-if="store.hasMoreMessages && !store.messagesLoading"
                class="w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                :disabled="store.isFetchingNextPage"
                @click="store.loadMore()"
              >
                {{ store.isFetchingNextPage ? 'Loading…' : 'Load more' }}
              </button>
            </template>
          </div>
        </ScrollAreaViewport>
        <ScrollAreaScrollbar orientation="vertical" class="flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5">
          <ScrollAreaThumb class="relative flex-1 rounded-full bg-border" />
        </ScrollAreaScrollbar>
      </ScrollAreaRoot>
    </TabsContent>

    <TabsContent value="starred" class="m-0 flex-1 overflow-hidden">
      <ScrollAreaRoot class="h-full">
        <ScrollAreaViewport class="h-full">
          <div class="flex flex-col gap-2 p-4 pt-0">
            <template v-if="store.messagesLoading">
              <div v-for="n in 6" :key="n" class="h-16 rounded-lg bg-muted animate-pulse" />
            </template>
            <template v-else>
              <TransitionGroup name="list" appear>
                <MessageListItem
                  v-for="msg in displayMessages"
                  :key="msg.id"
                  :message="msg"
                  :selected="store.currentMessage?.id === msg.id"
                  :folder-color="folderColor"
                  @click="selectMessage(msg)"
                />
              </TransitionGroup>
              <div v-if="displayMessages.length === 0" class="p-8 text-center text-muted-foreground">
                No starred messages.
              </div>
              <button
                v-if="store.hasMoreMessages && !store.messagesLoading"
                class="w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                :disabled="store.isFetchingNextPage"
                @click="store.loadMore()"
              >
                {{ store.isFetchingNextPage ? 'Loading…' : 'Load more' }}
              </button>
            </template>
          </div>
        </ScrollAreaViewport>
        <ScrollAreaScrollbar orientation="vertical" class="flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5">
          <ScrollAreaThumb class="relative flex-1 rounded-full bg-border" />
        </ScrollAreaScrollbar>
      </ScrollAreaRoot>
    </TabsContent>
  </TabsRoot>

  <Dialog v-model:open="showTrashConfirm">
    <div class="space-y-4">
      <h3 class="text-lg font-semibold leading-none tracking-tight">Empty Trash</h3>
      <p class="text-sm text-muted-foreground">
        Are you sure you want to empty the trash? All messages inside will be permanently deleted.
      </p>
      <div class="flex justify-end gap-2 pt-4">
        <Button variant="outline" @click="showTrashConfirm = false">Cancel</Button>
        <Button variant="destructive" @click="performEmptyTrash">Empty Trash</Button>
      </div>
    </div>
  </Dialog>
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
