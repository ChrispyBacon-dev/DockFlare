<script setup lang="ts">
import { computed, type Component } from 'vue'
import {
  Inbox, FileText, Send, Trash2, AlertCircle, Archive, Folder,
  PenSquare, LogOut,
} from 'lucide-vue-next'
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue'
import { cn } from '../../lib/utils'
import { useMailStore } from '../../stores/mail'
import { useAuth } from '../../composables/useAuth'
import Button from '../ui/Button.vue'
import Separator from '../ui/Separator.vue'

defineProps({
  isCollapsed: { type: Boolean, default: false },
})

const store = useMailStore()
const { logout } = useAuth()

const iconMap: Record<string, Component> = {
  Inbox, Drafts: FileText, Sent: Send,
  Trash: Trash2, Spam: AlertCircle, Junk: AlertCircle,
  Archive,
}

const getIcon = (name: string): Component => iconMap[name] || Folder

const selectFolder = (name: string) => {
  store.currentFolder = name
}

const compose = () => {
  store.composeDefaults = null
  store.isComposeOpen = true
}
</script>

<template>
  <div
    :data-collapsed="isCollapsed"
    class="group flex flex-1 flex-col justify-between py-2"
  >
    <nav class="grid gap-1 px-2 group-[[data-collapsed=true]]:justify-center group-[[data-collapsed=true]]:px-2">
      <template v-for="f in store.folders" :key="f.name">
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
              <component :is="getIcon(f.name)" class="size-4" />
              <span class="sr-only">{{ f.name }}</span>
            </button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent
              side="right"
              class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md flex items-center gap-4"
            >
              {{ f.name }}
              <span v-if="f.unread_count" class="ml-auto text-muted-foreground">
                {{ f.unread_count }}
              </span>
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>

        <button
          v-else
          :class="cn(
            'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground justify-start',
            store.currentFolder === f.name
              ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
              : 'transparent',
          )"
          @click="selectFolder(f.name)"
        >
          <component :is="getIcon(f.name)" class="size-4" />
          {{ f.name }}
          <span
            v-if="f.unread_count"
            :class="cn(
              'ml-auto text-xs',
              store.currentFolder === f.name ? 'text-primary-foreground' : 'text-muted-foreground',
            )"
          >
            {{ f.unread_count }}
          </span>
        </button>
      </template>
    </nav>

    <div class="grid gap-1 px-2 group-[[data-collapsed=true]]:justify-center group-[[data-collapsed=true]]:px-2">
      <Separator class="my-2" />
      <template v-if="isCollapsed">
        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <button
              class="inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90"
              @click="compose"
            >
              <PenSquare class="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Compose
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>
        <TooltipRoot :delay-duration="0">
          <TooltipTrigger as-child>
            <button
              class="inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              @click="logout"
            >
              <LogOut class="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipPortal>
            <TooltipContent side="right" class="z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md">
              Logout
            </TooltipContent>
          </TooltipPortal>
        </TooltipRoot>
      </template>
      <template v-else>
        <Button class="justify-start gap-2" size="sm" @click="compose">
          <PenSquare class="size-4" />
          Compose
        </Button>
        <Button variant="ghost" class="justify-start gap-2" size="sm" @click="logout">
          <LogOut class="size-4" />
          Logout
        </Button>
      </template>
    </div>
  </div>
</template>
