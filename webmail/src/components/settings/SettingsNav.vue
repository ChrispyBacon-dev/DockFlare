<script setup lang="ts">
import { Bell, Palette, AtSign, Mail, Shield, Info, HelpCircle } from 'lucide-vue-next'
import { useMailStore } from '@/stores/mail'

const store = useMailStore()

const categories = [
  { key: 'notifications', label: 'Notifications', icon: Bell },
  { key: 'appearance',    label: 'Appearance',    icon: Palette },
  { key: 'aliases',       label: 'Aliases',       icon: AtSign },
  { key: 'autoresponder', label: 'Auto-Responder', icon: Mail },
  { key: 'security',      label: 'Security',      icon: Shield },
  { key: 'about',         label: 'About',         icon: Info },
  { key: 'help',          label: 'Help',          icon: HelpCircle },
]
</script>

<template>
  <nav class="flex flex-col gap-0.5 p-3">
    <button
      v-for="cat in categories"
      :key="cat.key"
      class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors text-left"
      :class="store.settingsCategory === cat.key
        ? 'bg-[#FBA612]/10 text-[#FBA612] font-medium'
        : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
      @click="store.settingsCategory = cat.key"
    >
      <component :is="cat.icon" class="size-4 shrink-0" />
      {{ cat.label }}
    </button>
  </nav>
</template>
