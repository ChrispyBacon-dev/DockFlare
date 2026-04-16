<script setup lang="ts">
import { inject } from 'vue'

const group = inject<any>('resizableGroup')
const handleIdx = group ? group.registerHandle() : -1

function onPointerDown(e: PointerEvent) {
  if (!group || handleIdx === -1) return
  e.preventDefault()
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  group.startResize(handleIdx, e.clientX)
}
</script>

<template>
  <div
    class="w-1 bg-border cursor-col-resize hover:bg-primary/50 active:bg-primary/70 transition-colors hidden md:flex items-center justify-center flex-shrink-0 select-none"
    @pointerdown="onPointerDown"
  />
</template>
