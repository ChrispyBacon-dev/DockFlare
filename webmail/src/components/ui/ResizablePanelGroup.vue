<script setup lang="ts">
import { ref, provide, reactive } from 'vue'

const groupEl = ref<HTMLElement | null>(null)
const sizes = reactive<number[]>([])
const panelCount = ref(0)
const handleCount = ref(0)

function registerPanel(defaultSize: number): number {
  const idx = panelCount.value++
  sizes[idx] = defaultSize
  return idx
}

function registerHandle(): number {
  return handleCount.value++
}

function startResize(handleIdx: number, startX: number) {
  const onMove = (e: PointerEvent) => {
    if (!groupEl.value) return
    const dx = e.clientX - startX
    startX = e.clientX
    const totalW = groupEl.value.offsetWidth
    const deltaPercent = (dx / totalW) * 100
    const leftIdx = handleIdx
    const rightIdx = handleIdx + 1
    const newLeft = sizes[leftIdx] + deltaPercent
    const newRight = sizes[rightIdx] - deltaPercent
    if (newLeft >= 10 && newRight >= 10) {
      sizes[leftIdx] = newLeft
      sizes[rightIdx] = newRight
    }
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

provide('resizableGroup', { sizes, registerPanel, registerHandle, startResize })
</script>

<template>
  <div ref="groupEl" class="flex h-full w-full overflow-hidden">
    <slot />
  </div>
</template>
