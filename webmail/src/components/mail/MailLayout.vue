<script setup lang="ts">
import {
  SplitterGroup, SplitterPanel, SplitterResizeHandle,
  TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal,
} from 'radix-vue'
import { defineAsyncComponent } from 'vue'
import { PenSquare, Sun, Moon, LogOut, Settings, Columns2, Maximize2 } from 'lucide-vue-next'
import { cn } from '../../lib/utils'
import Separator from '../ui/Separator.vue'
import MailboxSelector from './MailboxSelector.vue'
import FolderNav from './FolderNav.vue'
import MessageList from './MessageList.vue'
import MessageDisplay from './MessageDisplay.vue'
import ComposeDialog from './ComposeDialog.vue'
import { useMailStore } from '../../stores/mail'
import { useAuth } from '../../composables/useAuth'

const SettingsDialog = defineAsyncComponent(() => import('./SettingsDialog.vue'))

const store = useMailStore()
const { logout } = useAuth()

const onCollapse = () => { store.isCollapsed = true }
const onExpand = () => { store.isCollapsed = false }

const compose = () => {
  store.composeDefaults = null
  store.isComposeOpen = true
}
</script>

<template>
  <TooltipProvider :delay-duration="0">
    <SplitterGroup
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
        <!-- ── Single header row (same height as middle + right panel headers) ── -->
        <div
          :class="cn(
            'h-[52px] flex items-center gap-1 px-2 flex-shrink-0',
            store.isCollapsed ? 'flex-col justify-center py-1' : 'flex-row',
          )"
        >
          <template v-if="!store.isCollapsed">
            <!-- Mailbox selector fills available space -->
            <div class="flex-1 min-w-0">
              <MailboxSelector :is-collapsed="false" />
            </div>
            <!-- Compose -->
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
            <!-- View Mode toggle -->
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
            <!-- Theme toggle -->
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
            <!-- Settings -->
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
            <!-- Logout -->
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

          <!-- Collapsed: stacked icon buttons -->
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
            <!-- Collapsed mailbox icon below -->
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

    <ComposeDialog />
    <SettingsDialog />
  </TooltipProvider>
</template>
