import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNotificationsStore = defineStore('notifications', () => {
  const permission = ref<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'denied'
  )

  const isGranted = computed(() => permission.value === 'granted')
  const isDenied = computed(() => permission.value === 'denied')

  async function requestPermission() {
    if (typeof Notification === 'undefined') return
    const result = await Notification.requestPermission()
    permission.value = result
  }

  return { permission, isGranted, isDenied, requestPermission }
})
