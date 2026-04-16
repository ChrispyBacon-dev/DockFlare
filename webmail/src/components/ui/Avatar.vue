<script setup lang="ts">
const props = defineProps({
  src: { type: String, default: '' },
  initials: { type: String, default: '' },
  class: { type: String, default: '' }
})
</script>

<template>
  <span :class="['relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-muted', props.class]">
    <img v-if="src" :src="src" class="aspect-square h-full w-full" />
    <span v-else class="flex h-full w-full items-center justify-center rounded-full bg-muted text-muted-foreground">{{ initials }}</span>
  </span>
</template>