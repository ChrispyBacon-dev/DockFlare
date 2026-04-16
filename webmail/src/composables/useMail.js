import { ref } from 'vue';
import { mailApi } from '../api/mail';
import { useMailStore } from '../stores/mail';
import { useAuthStore } from '../stores/auth';
export function useMail() {
    const store = useMailStore();
    const authStore = useAuthStore();
    const loading = ref(false);
    const error = ref('');
    const loadMailboxes = async () => {
        loading.value = true;
        try {
            const decoded = authStore.decodeToken();
            if (decoded?.role === 'user') {
                const addresses = decoded.mailboxes || [];
                store.mailboxes = addresses.map((addr) => ({ address: addr, display_name: addr }));
            }
            else {
                const res = await mailApi.getMailboxes();
                store.mailboxes = res.data;
            }
            if (store.mailboxes.length > 0 && !store.currentMailbox) {
                store.currentMailbox = store.mailboxes[0].address;
            }
        }
        catch (e) {
            error.value = e.message;
        }
        finally {
            loading.value = false;
        }
    };
    return { store, loading, error, loadMailboxes };
}
//# sourceMappingURL=useMail.js.map