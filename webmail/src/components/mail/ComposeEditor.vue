<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMailStore } from '../../stores/mail'

const props = defineProps({
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])
const store = useMailStore()

const text = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  text.value = val
  store.composeBody = val
})

const onInput = (e: Event) => {
  const val = (e.target as HTMLTextAreaElement).value
  text.value = val
  store.composeBody = val
  emit('update:modelValue', val)
}

const getHTML = () => text.value
defineExpose({ getHTML })
</script>

<template>
  <div class="flex flex-col border rounded-md overflow-hidden">
    <textarea
      :value="text"
      @input="onInput"
      placeholder="Write your message..."
      class="flex-1 p-4 text-sm resize-none focus:outline-none min-h-[160px]"
    />
  </div>
</template>
