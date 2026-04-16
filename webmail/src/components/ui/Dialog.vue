<script setup lang="ts">
defineProps({
  open: { type: Boolean, default: false }
})
defineEmits(['update:open'])
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" @click="$emit('update:open', false)">
    <div class="fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg max-h-[90vh] overflow-y-auto" @click.stop>
      <slot />
    </div>
  </div>
</template>