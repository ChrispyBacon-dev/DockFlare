<script setup lang="ts">
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps<{ hideHeader?: boolean }>()
import { useMailStore } from '@/stores/mail'
import SettingsNotifications from './sections/SettingsNotifications.vue'
import SettingsAppearance    from './sections/SettingsAppearance.vue'
import SettingsAliases       from './sections/SettingsAliases.vue'
import SettingsAutoResponder from './sections/SettingsAutoResponder.vue'
import SettingsSecurity      from './sections/SettingsSecurity.vue'
import SettingsAbout         from './sections/SettingsAbout.vue'
import SettingsHelp          from './sections/SettingsHelp.vue'

const store = useMailStore()

const sectionMap: Record<string, any> = {
  notifications: SettingsNotifications,
  appearance:    SettingsAppearance,
  aliases:       SettingsAliases,
  autoresponder: SettingsAutoResponder,
  security:      SettingsSecurity,
  about:         SettingsAbout,
  help:          SettingsHelp,
}

const currentSection = computed(() => sectionMap[store.settingsCategory] ?? SettingsNotifications)
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Header (hidden on mobile where outer shell provides it) -->
    <div v-if="!props.hideHeader" class="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
      <span class="text-sm font-semibold">Settings</span>
      <button
        class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        @click="store.isSettingsOpen = false"
      >
        <X class="size-4" />
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <component :is="currentSection" />
    </div>
  </div>
</template>
