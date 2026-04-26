<script setup lang="ts">
import {
  SplitterGroup, SplitterPanel, SplitterResizeHandle,
  TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal,
} from 'radix-vue'
import { ref, watch, computed } from 'vue'
import { PenSquare, Sun, Moon, LogOut, Settings, Columns2, Maximize2, ChevronLeft, Menu, PanelLeftClose, PanelLeftOpen, ArrowLeft } from 'lucide-vue-next'
import MailboxSelector from './MailboxSelector.vue'
import FolderNav from './FolderNav.vue'
import MessageList from './MessageList.vue'
import MessageDisplay from './MessageDisplay.vue'
import ComposeDialog from './ComposeDialog.vue'
import SettingsNav from '../settings/SettingsNav.vue'
import SettingsPanel from '../settings/SettingsPanel.vue'
import { useMailStore } from '../../stores/mail'
import { useAuth } from '../../composables/useAuth'
import { useBreakpoint } from '../../composables/useBreakpoint'

const store = useMailStore()
const { logout } = useAuth()
const { isMobile } = useBreakpoint()

const compose = () => {
  store.composeDefaults = null
  store.isComposeOpen = true
}

// ── Mobile navigation stack ──────────────────────────────────────────
type MobilePanel = 'folders' | 'list' | 'detail'
const mobilePanel = ref<MobilePanel>('list')

watch(() => store.currentFolder, () => {
  store.isSettingsOpen = false
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
    <div v-if="isMobile" class="flex flex-col h-[100dvh] w-screen overflow-hidden overscroll-none" style="background: var(--df-pane-bg); backdrop-filter: blur(12px);">

      <!-- Top bar — safe area aware -->
      <div
        class="flex items-end gap-2 px-3 pb-2 border-b border-border flex-shrink-0 pt-safe"
        style="background: var(--df-sidebar-bg); backdrop-filter: var(--df-sidebar-blur); min-height: calc(52px + env(safe-area-inset-top, 0px));"
      >
        <!-- Left: back or wordmark -->
        <button
          v-if="mobilePanel !== 'folders'"
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0"
          @click="goBack"
        >
          <ChevronLeft class="size-5" />
        </button>
        <span v-else class="font-['Outfit'] font-extrabold text-[19px] tracking-[-0.01em] leading-none select-none h-10 flex items-center px-1">
          <span class="text-[#194466] dark:text-[#5EB1E5]">Dock</span><span class="text-[#FBA612]">Flare</span>
        </span>

        <!-- Center: title (only for list/detail, not folders since wordmark is there) -->
        <span v-if="mobilePanel !== 'folders'" class="flex-1 text-[15px] font-semibold truncate pb-0.5">{{ mobileTitle }}</span>
        <div v-else class="flex-1" />

        <!-- Right: contextual actions -->
        <button
          v-if="mobilePanel === 'folders'"
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0"
          @click="store.toggleTheme()"
        >
          <Sun v-if="store.isDark" class="size-4" />
          <Moon v-else class="size-4" />
        </button>
        <button
          v-if="mobilePanel === 'folders'"
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0"
          @click="store.isSettingsOpen = true"
        >
          <Settings class="size-4" />
        </button>
        <button
          v-if="mobilePanel === 'folders'"
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0"
          @click="logout"
        >
          <LogOut class="size-4" />
        </button>
      </div>

      <!-- Panel content -->
      <div class="flex-1 min-h-0 overflow-hidden">

        <!-- Folders panel -->
        <div v-if="mobilePanel === 'folders'" class="h-full flex flex-col overflow-y-auto overscroll-none">
          <div v-if="store.mailboxes.length > 1" class="px-3 py-3 border-b border-border">
            <MailboxSelector :is-collapsed="false" />
          </div>
          <FolderNav :is-collapsed="false" />
        </div>

        <!-- Message list panel -->
        <div v-else-if="mobilePanel === 'list'" class="h-full flex flex-col overflow-hidden">
          <MessageList :hide-title="true" />
        </div>

        <!-- Message detail panel -->
        <div v-else-if="mobilePanel === 'detail'" class="h-full flex flex-col overflow-hidden">
          <MessageDisplay :message="store.currentMessage ?? undefined" />
        </div>
      </div>

      <!-- Bottom nav bar -->
      <div
        class="flex items-center justify-around border-t border-border flex-shrink-0 pb-safe"
        style="background: var(--df-sidebar-bg); backdrop-filter: var(--df-sidebar-blur); min-height: 60px;"
      >
        <button
          class="flex flex-col items-center gap-1 px-6 py-2 rounded-xl transition-colors min-h-[44px] justify-center"
          :class="mobilePanel === 'folders' ? '' : 'text-muted-foreground'"
          :style="mobilePanel === 'folders' ? 'color: #FBA612;' : ''"
          @click="mobilePanel = 'folders'"
        >
          <Menu class="size-5" />
          <span class="text-[10px] font-medium">Folders</span>
        </button>

        <button
          class="flex items-center justify-center h-12 w-12 rounded-full shadow-lg transition-colors flex-shrink-0"
          style="background: #FBA612; color: white; box-shadow: 0 2px 10px rgba(251,166,18,0.38);"
          @click="compose"
        >
          <PenSquare class="size-5" />
        </button>

        <button
          class="flex flex-col items-center gap-1 px-6 py-2 rounded-xl transition-colors min-h-[44px] justify-center"
          :class="mobilePanel === 'list' ? '' : 'text-muted-foreground'"
          :style="mobilePanel === 'list' ? 'color: #FBA612;' : ''"
          @click="mobilePanel = 'list'"
        >
          <Columns2 class="size-5" />
          <span class="text-[10px] font-medium">Mail</span>
        </button>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════
         DESKTOP LAYOUT  (≥ 768px)
    ══════════════════════════════════════════════════════════ -->
    <div v-else class="h-screen w-screen overflow-hidden flex flex-row">

      <!-- Sidebar — plain CSS div so we can programmatically collapse/expand -->
      <div
        class="df-sidebar flex flex-col flex-shrink-0 relative overflow-hidden"
        :style="{
          width: store.isCollapsed ? '52px' : '220px',
          background: 'var(--df-sidebar-bg)',
          backdropFilter: 'var(--df-sidebar-blur)',
          boxShadow: '2px 0 12px rgba(0,0,0,0.04)',
        }"
      >

        <!-- Header: wordmark + collapse toggle -->
        <div class="h-[54px] flex items-center justify-center px-[14px] flex-shrink-0">
          <template v-if="!store.isCollapsed">
            <img src="/logo.gif" alt="DockFlare" class="h-7 w-auto select-none" draggable="false" />
          </template>
          <template v-else>
            <span class="font-['Outfit'] font-extrabold text-[15px] leading-none select-none mx-auto">
              <span class="text-[#194466] dark:text-[#5EB1E5]">D</span><span class="text-[#FBA612]">F</span>
            </span>
          </template>
        </div>

        <!-- Mailbox selector — only when multiple mailboxes -->
        <div v-if="store.mailboxes.length > 1 && !store.isCollapsed" class="px-3 pb-2 flex-shrink-0">
          <MailboxSelector :is-collapsed="false" />
        </div>
        <div v-else-if="store.mailboxes.length > 1 && store.isCollapsed" class="flex justify-center pb-2 flex-shrink-0">
          <MailboxSelector :is-collapsed="true" />
        </div>

        <!-- Compose button -->
        <div class="px-3 pb-3 flex-shrink-0">
          <button
            v-if="!store.isCollapsed"
            class="df-compose-btn w-full flex items-center justify-center gap-2 rounded-xl py-2 text-sm font-semibold transition-all"
            @click="compose"
          >
            <PenSquare class="size-4" />
            Compose
          </button>
          <TooltipRoot v-else :delay-duration="0">
            <TooltipTrigger as-child>
              <button class="df-compose-btn inline-flex h-[34px] w-[34px] items-center justify-center rounded-full transition-all mx-auto" @click="compose">
                <PenSquare class="size-4" />
              </button>
            </TooltipTrigger>
            <TooltipPortal>
              <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Compose</TooltipContent>
            </TooltipPortal>
          </TooltipRoot>
        </div>

        <!-- Folder nav -->
        <FolderNav :is-collapsed="store.isCollapsed" />

        <!-- Bottom actions -->
        <div
          :class="store.isCollapsed
            ? 'flex flex-col items-center gap-1 px-2 py-3 flex-shrink-0'
            : 'px-3 py-3 flex-shrink-0 space-y-0.5'"
        >
          <template v-if="!store.isCollapsed">
            <button
              class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors"
              @click="store.isCollapsed = true"
            >
              <PanelLeftClose class="size-4" />
              Collapse sidebar
            </button>
            <button
              class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors"
              @click="store.toggleTheme()"
            >
              <Sun v-if="store.isDark" class="size-4" />
              <Moon v-else class="size-4" />
              {{ store.isDark ? 'Light mode' : 'Dark mode' }}
            </button>
            <button
              class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors"
              @click="store.isSettingsOpen = true"
            >
              <Settings class="size-4" />
              Settings
            </button>
            <button
              class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors"
              @click="logout"
            >
              <LogOut class="size-4" />
              Sign out
            </button>
          </template>
          <template v-else>
            <TooltipRoot :delay-duration="0">
              <TooltipTrigger as-child>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" @click="store.isCollapsed = false">
                  <PanelLeftOpen class="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Expand sidebar</TooltipContent>
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
                <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">Sign out</TooltipContent>
              </TooltipPortal>
            </TooltipRoot>
          </template>
        </div>
      </div>

      <!-- Inline settings panel -->
      <template v-if="store.isSettingsOpen">
        <div
          class="flex-none h-full overflow-y-auto border-r border-border"
          style="width: 200px; background: var(--df-list-bg);"
        >
          <SettingsNav />
        </div>
        <div class="flex-1 h-full overflow-hidden" style="background: var(--df-pane-bg);">
          <SettingsPanel />
        </div>
      </template>

      <!-- Splitter for message list + display panels -->
      <SplitterGroup
        v-else
        id="mail-layout"
        direction="horizontal"
        class="flex-1 h-full items-stretch"
      >
        <template v-if="store.viewMode === 'split'">
          <SplitterPanel
            id="mail-list"
            :default-size="35"
            :min-size="25"
            class="flex flex-col overflow-hidden"
            style="background: var(--df-list-bg); backdrop-filter: var(--df-list-blur);"
          >
            <MessageList />
          </SplitterPanel>

          <SplitterResizeHandle
            id="display-handle"
            class="self-stretch w-px bg-transparent hover:bg-border/30 active:bg-border/60 transition-colors"
          />

          <SplitterPanel
            id="mail-display"
            :default-size="65"
            :min-size="30"
            class="flex flex-col overflow-hidden"
            style="background: var(--df-pane-bg); backdrop-filter: var(--df-pane-blur);"
          >
            <ComposeDialog v-if="store.isComposeOpen && store.isComposeFullView" :panel-mode="true" />
            <MessageDisplay v-else :message="store.currentMessage ?? undefined" />
          </SplitterPanel>
        </template>

        <template v-else>
          <SplitterPanel
            id="mail-content"
            :default-size="100"
            :min-size="30"
            class="flex flex-col overflow-hidden"
            style="background: var(--df-pane-bg); backdrop-filter: var(--df-pane-blur);"
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
    </div><!-- end desktop layout -->

    <!-- Floating compose (desktop only) -->
    <template v-if="!isMobile">
      <ComposeDialog />
    </template>
    <Teleport v-else to="body">
      <div v-if="store.isComposeOpen" class="fixed inset-0 z-50 flex flex-col pt-safe" style="background: var(--df-pane-bg); backdrop-filter: blur(12px);">
        <ComposeDialog :panel-mode="true" />
      </div>
      <!-- Mobile settings fullscreen -->
      <div v-if="store.isSettingsOpen" class="fixed inset-0 z-50 flex flex-col pt-safe" style="background: var(--df-pane-bg);">
        <div class="flex items-center gap-2 px-3 pb-2 border-b border-border flex-shrink-0" style="min-height: calc(52px + env(safe-area-inset-top, 0px)); background: var(--df-sidebar-bg);">
          <button
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors"
            @click="store.isSettingsOpen = false"
          >
            <ArrowLeft class="size-5" />
          </button>
          <span class="text-[15px] font-semibold">Settings</span>
        </div>
        <div class="flex flex-1 min-h-0 overflow-hidden">
          <div class="w-44 flex-shrink-0 border-r border-border overflow-y-auto" style="background: var(--df-list-bg);">
            <SettingsNav />
          </div>
          <div class="flex-1 overflow-hidden" style="background: var(--df-pane-bg);">
            <SettingsPanel :hide-header="true" />
          </div>
        </div>
      </div>
    </Teleport>
  </TooltipProvider>
</template>

<style scoped>
.df-sidebar {
  transition: width 0.22s ease;
}
.df-compose-btn {
  background: #FBA612;
  color: white;
  box-shadow: 0 2px 10px rgba(251,166,18,0.32);
}
.df-compose-btn:hover {
  box-shadow: 0 4px 16px rgba(251,166,18,0.45);
}
</style>
