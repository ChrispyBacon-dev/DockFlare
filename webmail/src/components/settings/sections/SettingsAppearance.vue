<script setup lang="ts">
import { useMailStore } from '@/stores/mail'
import type { DateFormatKey } from '@/stores/mail'

const mailStore = useMailStore()

const DATE_FORMAT_OPTIONS: { key: DateFormatKey; label: string; example: string; description: string }[] = [
  { key: 'us',  label: 'US',       example: 'Apr 24, 2026, 4:31:48 PM',  description: '12-hour clock, month first' },
  { key: 'eu',  label: 'European', example: '24.04.2026, 16:31:48',       description: '24-hour clock, day first (CH/DE/FR)' },
  { key: 'iso', label: 'ISO 8601', example: '2026-04-24 16:31:48',        description: 'Sortable international standard' },
]
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-base font-semibold">Appearance</h2>
      <p class="text-sm text-muted-foreground mt-1">Customise how information is displayed in the app.</p>
    </div>

    <div class="rounded-lg border p-4 space-y-4">
      <div>
        <p class="text-sm font-medium">Date &amp; Time Format</p>
        <p class="text-xs text-muted-foreground mt-0.5">Applied to all timestamps throughout the app.</p>
      </div>
      <div class="flex flex-col gap-2">
        <label
          v-for="opt in DATE_FORMAT_OPTIONS"
          :key="opt.key"
          class="flex items-center gap-4 cursor-pointer rounded-lg px-3 py-3 hover:bg-accent/50 transition-colors border border-transparent"
          :class="mailStore.dateFormat === opt.key ? 'border-[#FBA612]/40 bg-[#FBA612]/5' : ''"
        >
          <input
            type="radio"
            name="dateFormat"
            :value="opt.key"
            :checked="mailStore.dateFormat === opt.key"
            class="accent-[#FBA612]"
            @change="mailStore.setDateFormat(opt.key)"
          />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium">{{ opt.label }}</p>
            <p class="text-xs text-muted-foreground">{{ opt.description }}</p>
          </div>
          <span class="text-xs text-muted-foreground font-mono shrink-0">{{ opt.example }}</span>
        </label>
      </div>
    </div>
  </div>
</template>
