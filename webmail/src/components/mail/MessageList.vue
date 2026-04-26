<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ArrowDownUp, Trash2, Square, CheckSquare, FolderInput } from 'lucide-vue-next'
import {
  TabsRoot, TabsList, TabsTrigger, TabsContent,
} from 'radix-vue'
import {
  ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb,
} from 'radix-vue'
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuPortal,
} from 'radix-vue'
import { useMailStore } from '../../stores/mail'
import { mailApi } from '../../api/mail'
import MessageListItem from './MessageListItem.vue'
import SearchBar from './SearchBar.vue'
import Dialog from '../ui/Dialog.vue'
import Button from '../ui/Button.vue'

const props = defineProps({
  hideTitle: { type: Boolean, default: false },
})

const store = useMailStore()
const showTrashConfirm = ref(false)

const bulkSelectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const isBulkLoading = ref(false)

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

const trashFolder = computed(() => store.folders.find((f: any) => f.name === 'Trash'))
const otherFolders = computed(() => store.folders.filter((f: any) => f.name !== store.currentFolder))
const hasSelection = computed(() => selectedIds.value.size > 0)
const allSelected = computed(() =>
  displayMessages.value.length > 0 && selectedIds.value.size === displayMessages.value.length
)

watch(() => store.activeTab, () => {
  selectedIds.value = new Set()
})

const toggleSort = () => {
  store.sortOrder = store.sortOrder === 'desc' ? 'asc' : 'desc'
}

function toggleBulkSelect() {
  bulkSelectMode.value = !bulkSelectMode.value
  if (!bulkSelectMode.value) {
    selectedIds.value = new Set()
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(displayMessages.value.map((m: any) => m.id))
  }
}

function toggleMessageSelection(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

const selectMessage = (msg: any) => {
  if (bulkSelectMode.value) {
    toggleMessageSelection(msg.id)
    return
  }
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

async function bulkMoveToTrash() {
  if (!hasSelection.value || !trashFolder.value) return
  isBulkLoading.value = true
  try {
    await mailApi.moveMessages(store.currentMailbox, {
      message_ids: [...selectedIds.value],
      folder_id: trashFolder.value.id,
    })
    store.messages = (store.messages as any[]).filter((m: any) => !selectedIds.value.has(m.id)) as any
    selectedIds.value = new Set()
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
    store.showToast('Messages moved to Trash', 'success')
  } catch {
    store.showToast('Failed to move messages to Trash')
  } finally {
    isBulkLoading.value = false
  }
}

async function bulkMoveToFolder(folderId: number, folderName: string) {
  if (!hasSelection.value) return
  isBulkLoading.value = true
  try {
    await mailApi.moveMessages(store.currentMailbox, {
      message_ids: [...selectedIds.value],
      folder_id: folderId,
    })
    store.messages = (store.messages as any[]).filter((m: any) => !selectedIds.value.has(m.id)) as any
    selectedIds.value = new Set()
    const fRes = await mailApi.getFolders(store.currentMailbox)
    store.folders = fRes.data
    store.showToast(`Messages moved to ${folderName}`, 'success')
  } catch {
    store.showToast('Failed to move messages')
  } finally {
    isBulkLoading.value = false
  }
}
</script>

<template>
  <TabsRoot v-model="store.activeTab" class="flex h-full flex-col">
    <div class="flex items-center px-4 flex-shrink-0" :class="hideTitle ? 'h-[44px]' : 'h-[52px]'">
      <h1 v-if="!hideTitle" class="text-xl font-bold">{{ store.currentFolder || 'Inbox' }}</h1>
      <div class="flex items-center gap-1" :class="hideTitle ? 'w-full justify-between' : 'ml-auto'">

        <!-- Bulk action controls (visible when bulkSelectMode active) -->
        <template v-if="bulkSelectMode">
          <!-- Select all -->
          <button
            class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            :title="allSelected ? 'Deselect all' : 'Select all'"
            @click="toggleSelectAll"
          >
            <CheckSquare v-if="allSelected" class="size-4" />
            <Square v-else class="size-4" />
          </button>

          <!-- Move to trash (hidden when already in Trash) -->
          <button
            v-if="store.currentFolder !== 'Trash'"
            class="inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors"
            :class="hasSelection && !isBulkLoading
              ? 'text-muted-foreground hover:bg-destructive hover:text-destructive-foreground'
              : 'text-muted-foreground/30 cursor-not-allowed'"
            :disabled="!hasSelection || isBulkLoading"
            title="Move to Trash"
            @click="bulkMoveToTrash"
          >
            <Trash2 class="size-4" />
          </button>

          <!-- Move to folder dropdown -->
          <DropdownMenuRoot>
            <DropdownMenuTrigger as-child>
              <button
                class="inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors"
                :class="hasSelection && !isBulkLoading
                  ? 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  : 'text-muted-foreground/30 cursor-not-allowed'"
                :disabled="!hasSelection || isBulkLoading"
                title="Move to folder"
              >
                <FolderInput class="size-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuPortal>
              <DropdownMenuContent
                align="end"
                :side-offset="4"
                class="z-50 min-w-[160px] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
              >
                <DropdownMenuItem
                  v-for="folder in otherFolders"
                  :key="folder.id"
                  class="relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                  @click="bulkMoveToFolder(folder.id, folder.name)"
                >
                  <span
                    v-if="folder.color"
                    class="h-2 w-2 rounded-full flex-shrink-0"
                    :style="`background: ${folder.color}`"
                  />
                  {{ folder.name }}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenuPortal>
          </DropdownMenuRoot>
        </template>

        <!-- Empty trash (only outside bulk mode) -->
        <button
          v-if="store.currentFolder === 'Trash' && store.messages.length > 0 && !bulkSelectMode"
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors"
          title="Empty Trash"
          @click="emptyTrash"
        >
          <Trash2 class="size-4" />
        </button>

        <!-- Checkbox toggle (always visible) -->
        <button
          class="inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors"
          :class="bulkSelectMode
            ? 'bg-accent text-[#FBA612]'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'"
          title="Select messages"
          @click="toggleBulkSelect"
        >
          <CheckSquare v-if="bulkSelectMode" class="size-4" />
          <Square v-else class="size-4" />
        </button>

        <!-- Sort -->
        <button
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          :title="store.sortOrder === 'desc' ? 'Oldest first' : 'Newest first'"
          @click="toggleSort"
        >
          <ArrowDownUp class="size-4" :class="store.sortOrder === 'asc' ? 'rotate-180' : ''" />
        </button>

        <TabsList class="inline-flex h-9 items-center gap-1 bg-transparent">
          <TabsTrigger
            value="all"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]"
            :style="store.activeTab === 'all' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : ''"
          >All</TabsTrigger>
          <TabsTrigger
            value="unread"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]"
            :style="store.activeTab === 'unread' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : ''"
          >Unread</TabsTrigger>
          <TabsTrigger
            value="starred"
            class="inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]"
            :style="store.activeTab === 'starred' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : ''"
          >Starred</TabsTrigger>
        </TabsList>
      </div>
    </div>
    <div class="px-[10px] pb-2">
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
                  :bulk-select-mode="bulkSelectMode"
                  :is-checked="selectedIds.has(msg.id)"
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
                  :bulk-select-mode="bulkSelectMode"
                  :is-checked="selectedIds.has(msg.id)"
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
                  :bulk-select-mode="bulkSelectMode"
                  :is-checked="selectedIds.has(msg.id)"
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
