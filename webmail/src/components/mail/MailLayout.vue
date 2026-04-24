<script setup lang="ts">
import {
  SplitterGroup, SplitterPanel, SplitterResizeHandle,
  TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal,
} from 'radix-vue'
import { defineAsyncComponent, ref, watch, computed } from 'vue'
import { PenSquare, Sun, Moon, LogOut, Settings, Columns2, Maximize2, ChevronLeft, Menu } from 'lucide-vue-next'
import { cn } from '../../lib/utils'
import MailboxSelector from './MailboxSelector.vue'
import FolderNav from './FolderNav.vue'
import MessageList from './MessageList.vue'
import MessageDisplay from './MessageDisplay.vue'
import ComposeDialog from './ComposeDialog.vue'
import { useMailStore } from '../../stores/mail'
import { useAuth } from '../../composables/useAuth'
import { useBreakpoint } from '../../composables/useBreakpoint'

const SettingsDialog = defineAsyncComponent(() => import('./SettingsDialog.vue'))

const store = useMailStore()
const { logout } = useAuth()
const { isMobile } = useBreakpoint()

const onCollapse = () => { store.isCollapsed = true }
const onExpand = () => { store.isCollapsed = false }

const compose = () => {
  store.composeDefaults = null
  store.isComposeOpen = true
}

// ── Mobile navigation stack ──────────────────────────────────────────
type MobilePanel = 'folders' | 'list' | 'detail'
const mobilePanel = ref<MobilePanel>('list')

watch(() => store.currentFolder, () => {
  if (isMobile.value) mobilePanel.value = 'list'
})

watch(() => store.currentMessage, (msg) => {
  if (isMobile.value && msg) mobilePanel.value = 'detail'
})

const goBack = () => {
  if (mobilePanel.value === 'detail') {
    store.currentMessage = null
    mobilePanel.value = 'list'
  } else if (mobilePanel.value === 'list') {
    mobilePanel.value = 'folders'
  }
}

const mobileTitle = computed(() => {
  if (mobilePanel.value === 'folders') return store.currentMailbox || 'Folders'
  if (mobilePanel.value === 'list') return store.currentFolder || 'Inbox'
  return store.currentMessage?.subject || 'Message'
})
</script>

<template>
  <TooltipProvider :delay-duration="0">

    <!-- ══════════════════════════════════════════════════════════
         MOBILE LAYOUT  (< 768px)
    ══════════════════════════════════════════════════════════ -->
    <div v-if="isMobile" class="flex flex-col h-[100dvh] w-screen bg-background overflow-hidden">

      <!-- Top bar -->
      <div class="h-14 flex items-center gap-2 px-3 border-b border-border flex-shrink-0 bg-background">
        <button
          v-if="mobilePanel !== 'folders'"
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0"
          @click="goBack"
        >
          <ChevronLeft class="size-5" />
        </button>
        <button
          v-else
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0"
          @click="store.isSettingsOpen = true"
        >
          <Settings class="size-4" />
        </button>

        <span class="flex-1 text-base font-semibold truncate">{{ mobileTitle }}</span>

        <button
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0"
          @click="store.toggleTheme()"
        >
          <Sun v-if="store.isDark" class="size-4" />
          <Moon v-else class="size-4" />
        </button>

        <button
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0"
          @click="logout"
        >
          <LogOut class="size-4" />
        </button>
      </div>

      <!-- Panel content -->
      <div class="flex-1 min-h-0 overflow-hidden">

        <!-- Folders panel -->
        <div v-if="mobilePanel === 'folders'" class="h-full flex flex-col overflow-y-auto">
          <div class="px-3 py-3 border-b border-border">
            <MailboxSelector :is-collapsed="false" />
          </div>
          <FolderNav :is-collapsed="false" />
        </div>

        <!-- Message list panel -->
        <div v-else-if="mobilePanel === 'list'" class="h-full flex flex-col overflow-hidden">
          <MessageList />
        </div>

        <!-- Message detail panel -->
        <div v-else-if="mobilePanel === 'detail'" class="h-full flex flex-col overflow-hidden">
          <MessageDisplay :message="store.currentMessage ?? undefined" />
        </div>
      </div>

      <!-- Bottom nav bar -->
      <div class="h-16 flex items-center justify-around border-t border-border flex-shrink-0 bg-background pb-safe">
        <button
          class="flex flex-col items-center gap-0.5 px-4 py-2 rounded-lg transition-colors"
          :class="mobilePanel === 'folders' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'"
          @click="mobilePanel = 'folders'"
        >
          <Menu class="size-5" />
          <span class="text-[10px] font-medium">Folders</span>
        </button>

        <button
          class="flex items-center justify-center h-12 w-12 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors"
          @click="compose"
        >
          <PenSquare class="size-5" />
        </button>

        <button
          class="flex flex-col items-center gap-0.5 px-4 py-2 rounded-lg transition-colors"
          :class="mobilePanel === 'list' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'"
          @click="mobilePanel = 'list'"
        >
          <Columns2 class="size-5" />
          <span class="text-[10px] font-medium">Mail</span>
        </button>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════
         DESKTOP LAYOUT  (≥ 768px)  — unchanged
    ══════════════════════════════════════════════════════════ -->
    <SplitterGroup
      v-else
      id="mail-layout"
      direction="horizontal"
      class="h-screen w-screen items-stretch"
    >
      <SplitterPanel
        id="sidebar"
        :default-size="20"
        :collapsed-size="4"
        collapsible
        :min-size="15"
        :max-size="22"
        :class="cn(
          'flex flex-col',
          store.isCollapsed && 'min-w-[50px] transition-all duration-300 ease-in-out',
        )"
        @collapse="onCollapse"
        @expand="onExpand"
      >
        <div
          :class="cn(
            'h-[52px] flex items-center gap-1 px-2 flex-shrink-0',
            store.isCollapsed ? 'flex-col justify-center py-1' : 'flex-row',
          )"
        >
          <template v-if="!store.isCollapsed">
            <div class="flex-1 min-w-0">
              <MailboxSelector :is-collapsed="false" />
            </div>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button
                  class="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex-shrink-0"
                  @click="compose"
                >
                  <PenSquare class="size-4" />
                  Compose
                </button>
              </TooltipTrigger>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button
                  class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0"
                  @click="store.toggleViewMode()"
                >
                  <Columns2 v-if="store.viewMode === 'full'" class="size-4" />
                  <Maximize2 v-else class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="bottom" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
                  {{ store.viewMode === 'full' ? 'Split view' : 'Full view' }}
                </TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button
                  class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0"
                  @click="store.toggleTheme()"
                >
                  <Sun v-if="store.isDark" class="size-4" />
                  <Moon v-else class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="bottom" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
                  {{ store.isDark ? 'Light mode' : 'Dark mode' }}
                </TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button
                  class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0"
                  @click="store.isSettingsOpen = true"
                >
                  <Settings class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="bottom" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
                  Settings
                </TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button
                  class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0"
                  @click="logout"
                >
                  <LogOut class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="bottom" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
                  Logout
                </TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
          </template>

          <template v-else>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" @click="compose">
                  <PenSquare class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Compose</TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" @click="store.toggleTheme()">
                  <Sun v-if="store.isDark" class="size-4" />
                  <Moon v-else class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">{{ store.isDark ? 'Light mode' : 'Dark mode' }}</TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" @click="store.isSettingsOpen = true">
                  <Settings class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Settings</TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" @click="logout">
                  <LogOut class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Logout</TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
            <MailboxSelector :is-collapsed="true" />
          </template>
        </div>

        <FolderNav :is-collapsed="store.isCollapsed" />
      </SplitterPanel>

      <SplitterResizeHandle
        id="sidebar-handle"
        class="self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors"
      />

      <template v-if="store.viewMode === 'split'">
        <SplitterPanel
          id="mail-list"
          :default-size="35"
          :min-size="25"
          class="flex flex-col overflow-hidden"
        >
          <MessageList />
        </SplitterPanel>

        <SplitterResizeHandle
          id="display-handle"
          class="self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors"
        />

        <SplitterPanel
          id="mail-display"
          :default-size="45"
          :min-size="30"
          class="flex flex-col overflow-hidden"
        >
          <ComposeDialog v-if="store.isComposeOpen && store.isComposeFullView" :panel-mode="true" />
          <MessageDisplay v-else :message="store.currentMessage ?? undefined" />
        </SplitterPanel>
      </template>

      <template v-else>
        <SplitterPanel
          id="mail-content"
          :default-size="80"
          :min-size="30"
          class="flex flex-col overflow-hidden"
        >
          <template v-if="store.isComposeOpen && store.isComposeFullView">
            <ComposeDialog :panel-mode="true" />
          </template>
          <template v-else>
            <MessageList v-if="!store.currentMessage" />
            <MessageDisplay v-else :message="store.currentMessage ?? undefined" />
          </template>
        </SplitterPanel>
      </template>
    </SplitterGroup>

    <!-- Floating compose (desktop only) + settings dialog -->
    <template v-if="!isMobile">
      <ComposeDialog />
    </template>
    <Teleport v-else to="body">
      <div v-if="store.isComposeOpen" class="fixed inset-0 z-50 flex flex-col bg-background">
        <ComposeDialog :panel-mode="true" />
      </div>
    </Teleport>
    <SettingsDialog />
  </TooltipProvider>
</template>
