<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'default' },
  size: { type: String, default: 'default' },
  class: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  as: { type: String, default: 'button' }
})

const baseClass = "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"

const variants = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost: "hover:bg-accent hover:text-accent-foreground",
  link: "text-primary underline-offset-4 hover:underline",
}

const sizes = {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-md px-3",
  lg: "h-11 rounded-md px-8",
  icon: "h-10 w-10",
}

const computedClass = computed(() => {
  return `${baseClass} ${variants[props.variant as keyof typeof variants] || variants.default} ${sizes[props.size as keyof typeof sizes] || sizes.default} ${props.class}`
})
</script>

<template>
  <component :is="as" :class="computedClass" :disabled="as === 'button' ? disabled : undefined" v-bind="$attrs">
    <slot />
  </component>
</template>