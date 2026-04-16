/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'
import { setCatchHandler } from 'workbox-routing'
import { getIDBItem } from './lib/idb'

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<{ url: string; revision: string | null }>
}

cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

async function broadcastBadge(count: number) {
  const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
  for (const client of clients) {
    client.postMessage({ type: 'SET_BADGE', count })
  }
}

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {}
  const unreadCount: number = data.unread_count ?? 0

  const notifOptions: NotificationOptions = {
    body: data.subject ?? 'New message',
    icon: '/favicon/android-chrome-192x192.png',
    badge: '/favicon/favicon-32x32.png',
    tag: String(data.message_id ?? Date.now()),
    data: { messageId: data.message_id, mailbox: data.mailbox, unreadCount },
    actions: [{ action: 'mark-read', title: 'Mark as Read' }],
  }

  event.waitUntil(
    self.registration
      .showNotification(data.mailbox ?? 'DockFlare Mail', notifOptions)
      .then(() => broadcastBadge(unreadCount))
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const { messageId, mailbox, unreadCount } = event.notification.data ?? {}

  if (event.action === 'mark-read' && messageId && mailbox) {
    event.waitUntil(
      (async () => {
        const token = await getIDBItem('jwt_token')
        if (token) {
          try {
            await fetch(`/api/v1/mailboxes/${mailbox}/messages/${messageId}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ is_read: true }),
            })
          } catch { /* ignore */ }
        }
        await broadcastBadge(Math.max(0, (unreadCount ?? 1) - 1))
      })()
    )
    return
  }

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        for (const client of clients) {
          if ('focus' in client) {
            client.postMessage({ type: 'NOTIFICATION_CLICK', messageId, mailbox })
            return (client as WindowClient).focus()
          }
        }
        const url = mailbox
          ? `/?mailbox=${encodeURIComponent(mailbox)}&message=${encodeURIComponent(messageId ?? '')}`
          : '/'
        return self.clients.openWindow(url)
      })
  )
})

setCatchHandler(async ({ request }) => {
  if (request.destination === 'document') {
    return (await caches.match('/offline.html')) ?? Response.error()
  }
  return Response.error()
})
