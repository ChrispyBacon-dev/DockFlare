<script setup lang="ts">
import SettingsNav from '@/components/settings/SettingsNav.vue'
import SettingsPanel from '@/components/settings/SettingsPanel.vue'
</script>

<template>
  <div class="flex h-full">
    <div class="w-48 border-r border-border overflow-y-auto">
      <SettingsNav />
    </div>
    <div class="flex-1 overflow-hidden">
      <SettingsPanel :hide-header="true" />
    </div>
  </div>
</template>
