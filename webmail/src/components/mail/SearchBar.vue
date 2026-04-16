<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSearch } from '../../composables/useSearch'
import { useMailStore } from '../../stores/mail'

const searchVal = ref('')
const { search, results, loading } = useSearch()
const store = useMailStore()

let timeout: any

watch(searchVal, (val) => {
  clearTimeout(timeout)
  timeout = setTimeout(() => {
    if (store.currentMailbox) search(store.currentMailbox, val)
  }, 300)
})

const selectResult = (msg: any) => {
  store.currentMessage = msg
  searchVal.value = ''
}
</script>

<template>
  <div class="relative w-full px-4 py-2 border-b">
    <input v-model="searchVal" type="search" placeholder="Search..." class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
    <div v-if="searchVal && results.length > 0" class="absolute left-0 right-0 top-full z-10 mt-1 max-h-[300px] overflow-y-auto rounded-md border bg-background p-1 shadow-md">
      <div v-for="res in results" :key="res.id" @click="selectResult(res)" class="cursor-pointer rounded-sm px-2 py-1 text-sm hover:bg-accent">
        <div class="font-semibold">{{ res.subject }}</div>
        <div class="text-xs text-muted-foreground">{{ res.from_address }}</div>
      </div>
    </div>
    <div v-else-if="searchVal && !loading" class="absolute left-0 right-0 top-full z-10 mt-1 rounded-md border bg-background p-4 text-center text-sm text-muted-foreground shadow-md">
      No results found.
    </div>
  </div>
</template>