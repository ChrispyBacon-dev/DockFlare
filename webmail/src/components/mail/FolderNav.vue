<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import {
  Inbox, FileText, Send, Trash2, AlertCircle, Archive, Folder,
  FolderPlus, X,
} from 'lucide-vue-next'
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue'
import { cn } from '../../lib/utils'
import { useMailStore } from '../../stores/mail'
import { mailApi } from '../../api/mail'

defineProps({
  isCollapsed: { type: Boolean, default: false },
})

const store = useMailStore()

const iconMap: Record<string, Component> = {
  Inbox, Drafts: FileText, Sent: Send,
  Trash: Trash2, Spam: AlertCircle, Junk: AlertCircle,
  Archive,
}

const PALETTE = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6',
]

const getIcon = (name: string): Component => iconMap[name] || Folder

const selectFolder = (name: string) => {
  store.currentFolder = name
  store.currentMessage = null
  store.viewMode = 'split'
}

// ── New folder creation ──────────────────────────────────────────────
const showNewFolder = ref(false)
const newFolderName = ref('')
const newFolderColor = ref('')
const creatingFolder = ref(false)

const startNewFolder = () => {
  newFolderName.value = ''
  newFolderColor.value = ''
  showNewFolder.value = true
}

const cancelNewFolder = () => {
  showNewFolder.value = false
}

const confirmNewFolder = async () => {
  const name = newFolderName.value.trim()
  if (!name || !store.currentMailbox) return
  creatingFolder.value = true
  try {
    await mailApi.createFolder(store.currentMailbox, name, newFolderColor.value || undefined)
    const res = await mailApi.getFolders(store.currentMailbox)
    store.folders = res.data
    showNewFolder.value = false
  } catch {
    store.showToast('Failed to create folder')
  } finally {
    creatingFolder.value = false
  }
}

// ── Folder delete ────────────────────────────────────────────────────
const deleteFolder = async (f: any) => {
  if (!store.currentMailbox) return
  if (!confirm(`Delete folder "${f.name}"? All messages inside will be deleted.`)) return
  try {
    await mailApi.deleteFolder(store.currentMailbox, f.id)
    const res = await mailApi.getFolders(store.currentMailbox)
    store.folders = res.data
    if (store.currentFolder === f.name) {
      store.currentFolder = store.folders[0]?.name || ''
    }
  } catch {
    store.showToast('Failed to delete folder')
  }
}

// ── Folder rename / colour edit ──────────────────────────────────────
const editingFolder = ref<any>(null)
const editName = ref('')
const editColor = ref('')

const startEdit = (f: any) => {
  editingFolder.value = f
  editName.value = f.name
  editColor.value = f.color || ''
}

const cancelEdit = () => {
  editingFolder.value = null
}

const confirmEdit = async () => {
  if (!editingFolder.value || !store.currentMailbox) return
  const name = editName.value.trim()
  if (!name) return
  try {
    await mailApi.renameFolder(store.currentMailbox, editingFolder.value.id, name, editColor.value || undefined)
    const res = await mailApi.getFolders(store.currentMailbox)
    store.folders = res.data
    if (store.currentFolder === editingFolder.value.name && name !== editingFolder.value.name) {
      store.currentFolder = name
    }
    editingFolder.value = null
  } catch {
    store.showToast('Failed to rename folder')
  }
}
</script>

<template>
  <div
    :data-collapsed="isCollapsed"
    class="group flex flex-1 flex-col justify-between py-2 overflow-y-auto"
  >
    <nav class="grid gap-1 px-2 group-[[data-collapsed=true]]:justify-center group-[[data-collapsed=true]]:px-2">
      <template v-for="f in store.folders" :key="f.name">

        <!-- Collapsed icon-only -->
        <TooltipRoot v-if="isCollapsed" :delay-duration="0">
          <TooltipTrigger as-child>
            <button
              :class="cn(
                'inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                store.currentFolder === f.name
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
                  : 'text-muted-foreground',
              )"
              @click="selectFolder(f.name)"
            >
              <component :is="getIcon(f.name)" class="size-4" :style="f.color && store.currentFolder !== f.name ? `color:${f.color}` : ''" />
              <span class="sr-only">{{ f.name }}</span>
            </button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent
              side="right"
              class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md flex items-center gap-4"
            >
              {{ f.name }}
              <span v-if="f.total_count > 0" class="ml-auto text-muted-foreground flex gap-1">
                <span v-if="f.unread_count" class="font-bold">{{ f.unread_count }} /</span>
                <span>{{ f.total_count }}</span>
              </span>
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <!-- Expanded row — inline edit mode -->
        <div v-else-if="editingFolder?.id === f.id" class="rounded-md border bg-muted p-2 flex flex-col gap-2">
          <input
            v-model="editName"
            class="w-full rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            @keyup.enter="confirmEdit"
            @keyup.escape="cancelEdit"
            autofocus
          />
          <div class="flex gap-1 flex-wrap">
            <button
              v-for="c in PALETTE" :key="c"
              class="h-5 w-5 rounded-full border-2 transition-transform hover:scale-110"
              :style="`background:${c}; border-color:${editColor === c ? '#000' : 'transparent'}`"
              @click="editColor = editColor === c ? '' : c"
            />
            <button
              class="h-5 w-5 rounded-full border-2 text-xs flex items-center justify-center text-muted-foreground hover:bg-accent"
              :style="`border-color:${!editColor ? '#888' : 'transparent'}`"
              title="No colour"
              @click="editColor = ''"
            >✕</button>
          </div>
          <div class="flex gap-1 justify-end">
            <button class="text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground" @click="cancelEdit">Cancel</button>
            <button class="text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90" @click="confirmEdit">Save</button>
          </div>
        </div>

        <!-- Expanded normal row -->
        <div
          v-else
          :class="cn(
            'group/row relative flex items-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
            store.currentFolder === f.name
              ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
              : 'transparent',
          )"
        >
          <button
            class="flex flex-1 items-center gap-3 px-3 py-2 text-left min-w-0"
            @click="selectFolder(f.name)"
          >
            <component :is="getIcon(f.name)" class="size-4 flex-shrink-0" :style="f.color ? `color:${f.color}` : ''" />
            <span class="truncate">{{ f.name }}</span>
            <span
              v-if="f.total_count > 0"
              :class="cn(
                'ml-auto text-xs flex-shrink-0 flex gap-1',
                store.currentFolder === f.name ? 'text-primary-foreground' : 'text-muted-foreground',
              )"
            >
              <span v-if="f.unread_count" class="font-bold">{{ f.unread_count }} /</span>
              <span>{{ f.total_count }}</span>
            </span>
          </button>
          <!-- Custom folder actions — absolutely positioned so they don't affect count alignment -->
          <div
            v-if="!f.system_folder"
            :class="cn(
              'absolute right-1 flex gap-0.5 opacity-0 group-hover/row:opacity-100 transition-opacity rounded px-0.5',
              store.currentFolder === f.name ? 'bg-primary' : 'bg-accent',
            )"
          >
            <button
              class="p-1 rounded hover:bg-accent/80"
              title="Rename / recolour"
              @click.stop="startEdit(f)"
            >
              <svg class="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button
              class="p-1 rounded hover:text-destructive"
              title="Delete folder"
              @click.stop="deleteFolder(f)"
            >
              <Trash2 class="size-3" />
            </button>
          </div>
        </div>
      </template>

      <!-- New folder inline form (expanded only) -->
      <div v-if="showNewFolder && !isCollapsed" class="rounded-md border bg-muted p-2 flex flex-col gap-2 mt-1">
        <input
          v-model="newFolderName"
          placeholder="Folder name"
          class="w-full rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          @keyup.enter="confirmNewFolder"
          @keyup.escape="cancelNewFolder"
          autofocus
        />
        <div class="flex gap-1 flex-wrap">
          <button
            v-for="c in PALETTE" :key="c"
            class="h-5 w-5 rounded-full border-2 transition-transform hover:scale-110"
            :style="`background:${c}; border-color:${newFolderColor === c ? '#000' : 'transparent'}`"
            @click="newFolderColor = newFolderColor === c ? '' : c"
          />
          <button
            class="h-5 w-5 rounded-full border-2 text-xs flex items-center justify-center text-muted-foreground hover:bg-accent"
            :style="`border-color:${!newFolderColor ? '#888' : 'transparent'}`"
            title="No colour"
            @click="newFolderColor = ''"
          >✕</button>
        </div>
        <div class="flex gap-1 justify-end">
          <button class="text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground" @click="cancelNewFolder">Cancel</button>
          <button
            class="text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            :disabled="creatingFolder || !newFolderName.trim()"
            @click="confirmNewFolder"
          >
            {{ creatingFolder ? '…' : 'Create' }}
          </button>
        </div>
      </div>

      <!-- Add folder button (expanded only) -->
      <button
        v-if="!isCollapsed"
        class="flex items-center gap-2 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors mt-1"
        @click="startNewFolder"
      >
        <FolderPlus class="size-3" />
        New folder
      </button>
    </nav>

  </div>
</template>
