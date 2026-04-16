<script setup lang="ts">
const props = defineProps({
  orientation: { type: String, default: 'horizontal' },
  class: { type: String, default: '' }
})
</script>

<template>
  <div :class="['shrink-0 bg-border', orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]', props.class]" />
</template>