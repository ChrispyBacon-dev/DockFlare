import { onUnmounted, ref, watch } from 'vue';
import { mailApi } from '@/api/mail';
import { useNotificationsStore } from '@/stores/notifications';
import { useMailStore } from '@/stores/mail';
export function useMailPolling() {
    const notificationsStore = useNotificationsStore();
    const mailStore = useMailStore();
    const lastSeen = ref({});
    const initialized = ref(false);
    const poll = async () => {
        if (mailStore.mailboxes.length === 0)
            return;
        try {
            const res = await mailApi.getMailboxStatus();
            const statuses = res.data;
            if (!initialized.value) {
                for (const s of statuses) {
                    lastSeen.value[s.address] = s.latest_received_at;
                }
                initialized.value = true;
                return;
            }
            if (!notificationsStore.isGranted)
                return;
            for (const s of statuses) {
                const prev = lastSeen.value[s.address];
                if (s.latest_received_at &&
                    (prev === undefined || prev === null || s.latest_received_at > prev)) {
                    lastSeen.value[s.address] = s.latest_received_at;
                    fireNotification(s.address, s.unread_count);
                }
            }
        }
        catch {
            // network error — skip
        }
    };
    const fireNotification = (address, unreadCount) => {
        const n = new Notification(address, {
            body: `${unreadCount} unread message${unreadCount !== 1 ? 's' : ''}`,
            icon: '/favicon/android-chrome-192x192.png',
            tag: address,
            data: { mailbox: address },
        });
        n.onclick = () => {
            window.focus();
            mailStore.currentMailbox = address;
            n.close();
        };
    };
    watch(() => mailStore.mailboxes, (boxes) => {
        if (boxes.length > 0 && !initialized.value)
            poll();
    }, { immediate: true });
    const interval = setInterval(poll, 60_000);
    onUnmounted(() => clearInterval(interval));
}
//# sourceMappingURL=useMailPolling.js.map