<script setup lang="ts">
import {
  SplitterGroup, SplitterPanel, SplitterResizeHandle,
} from 'radix-vue'
import { TooltipProvider } from 'radix-vue'
import { cn } from '../../lib/utils'
import Separator from '../ui/Separator.vue'
import MailboxSelector from './MailboxSelector.vue'
import FolderNav from './FolderNav.vue'
import MessageList from './MessageList.vue'
import MessageDisplay from './MessageDisplay.vue'
import ComposeDialog from './ComposeDialog.vue'
import { useMailStore } from '../../stores/mail'

const store = useMailStore()

const onCollapse = () => { store.isCollapsed = true }
const onExpand = () => { store.isCollapsed = false }
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
        <MailboxSelector :is-collapsed="store.isCollapsed" />
        <Separator />
        <FolderNav :is-collapsed="store.isCollapsed" />
      </SplitterPanel>

      <SplitterResizeHandle
        id="sidebar-handle"
        class="w-[3px] bg-border hover:bg-primary/50 active:bg-primary/70 transition-colors"
      />

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
        class="w-[3px] bg-border hover:bg-primary/50 active:bg-primary/70 transition-colors"
      />

      <SplitterPanel
        id="mail-display"
        :default-size="45"
        :min-size="30"
        class="flex flex-col overflow-hidden"
      >
        <MessageDisplay :message="store.currentMessage" />
      </SplitterPanel>
    </SplitterGroup>

    <ComposeDialog />
  </TooltipProvider>
</template>
