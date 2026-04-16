<script setup lang="ts">
import { inject, computed } from 'vue'

const props = defineProps({
  defaultSize: { type: Number, default: 50 },
  minSize: { type: Number, default: 10 },
  class: { type: String, default: '' }
})

const group = inject<any>('resizableGroup')
const idx = group ? group.registerPanel(props.defaultSize) : -1

const sizeStyle = computed(() => {
  if (!group || idx === -1) return { flexBasis: `${props.defaultSize}%`, flexShrink: '0', flexGrow: '0' }
  return { flexBasis: `${group.sizes[idx]}%`, flexShrink: '0', flexGrow: '0' }
})
</script>

<template>
  <div :style="sizeStyle" :class="['overflow-auto min-w-0', props.class]">
    <slot />
  </div>
</template>
