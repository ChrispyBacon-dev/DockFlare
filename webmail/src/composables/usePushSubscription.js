import { ref } from 'vue';
import apiClient from '@/api/client';
const isSupported = typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window;
function urlBase64ToUint8Array(base64) {
    const padding = '='.repeat((4 - (base64.length % 4)) % 4);
    const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++)
        bytes[i] = raw.charCodeAt(i);
    return bytes;
}
export function usePushSubscription() {
    const isSubscribed = ref(false);
    const isLoading = ref(false);
    const checkSubscription = async () => {
        if (!isSupported)
            return;
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        isSubscribed.value = !!sub;
    };
    const subscribe = async (mailboxAddress) => {
        if (!isSupported)
            return;
        isLoading.value = true;
        try {
            const { data } = await apiClient.get('/notifications/vapid-key');
            const reg = await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(data.public_key),
            });
            const subJson = sub.toJSON();
            await apiClient.post('/notifications/subscribe', {
                endpoint: subJson.endpoint,
                keys: subJson.keys,
                mailbox_address: mailboxAddress,
            });
            isSubscribed.value = true;
        }
        finally {
            isLoading.value = false;
        }
    };
    const unsubscribe = async () => {
        if (!isSupported)
            return;
        isLoading.value = true;
        try {
            const reg = await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.getSubscription();
            if (sub) {
                await apiClient.delete('/notifications/subscribe', {
                    data: { endpoint: sub.endpoint },
                });
                await sub.unsubscribe();
            }
            isSubscribed.value = false;
        }
        finally {
            isLoading.value = false;
        }
    };
    checkSubscription();
    return { isSubscribed, isLoading, isSupported, subscribe, unsubscribe };
}
//# sourceMappingURL=usePushSubscription.js.map