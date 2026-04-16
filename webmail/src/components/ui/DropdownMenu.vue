<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  label: { type: String, default: 'Menu' }
})

const open = ref(false)
const toggle = () => open.value = !open.value
</script>

<template>
  <div class="relative inline-block text-left">
    <div @click="toggle">
      <slot name="trigger">
        <button class="inline-flex w-full justify-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50">{{ label }}</button>
      </slot>
    </div>
    <div v-if="open" class="absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none" role="menu">
      <div class="py-1">
        <slot @click="open = false" />
      </div>
    </div>
  </div>
</template>