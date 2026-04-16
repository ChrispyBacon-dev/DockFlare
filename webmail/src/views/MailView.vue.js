/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useMail } from '../composables/useMail';
import { useMailPolling } from '../composables/useMailPolling';
import { mailApi } from '../api/mail';
import MailLayout from '../components/mail/MailLayout.vue';
const route = useRoute();
const { store, loadMailboxes } = useMail();
useMailPolling();
const loadMessages = async (addr, folder) => {
    if (!addr || !folder)
        return;
    try {
        const mRes = await mailApi.getMessages(addr, { folder, order: store.sortOrder });
        const payload = mRes.data;
        store.messages = Array.isArray(payload) ? payload : payload.items || [];
        store.currentMessage = null;
    }
    catch (e) {
        console.error('Failed to load messages', e);
    }
};
onMounted(async () => {
    await loadMailboxes();
    const mailboxParam = route.query.mailbox;
    if (mailboxParam) {
        const found = store.mailboxes.find((b) => b.address === mailboxParam);
        if (found)
            store.currentMailbox = mailboxParam;
    }
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.addEventListener('message', (ev) => {
            if (ev.data?.type === 'NOTIFICATION_CLICK' && ev.data.mailbox) {
                store.currentMailbox = ev.data.mailbox;
            }
        });
    }
});
watch(() => store.currentMailbox, async (addr) => {
    if (!addr)
        return;
    try {
        const fRes = await mailApi.getFolders(addr);
        store.folders = fRes.data;
        if (store.folders.length > 0) {
            const inbox = store.folders.find((f) => f.name.toLowerCase() === 'inbox');
            store.currentFolder = inbox ? inbox.name : store.folders[0].name;
        }
    }
    catch (e) {
        console.error('Failed to load folders', e);
    }
});
watch(() => [store.currentMailbox, store.currentFolder], ([addr, folder]) => {
    loadMessages(addr, folder);
});
watch(() => store.sortOrder, () => {
    loadMessages(store.currentMailbox, store.currentFolder);
});
watch(() => store.currentMessage, async (msg) => {
    if (!msg || msg.attachments !== undefined)
        return;
    try {
        const res = await mailApi.getMessage(store.currentMailbox, msg.id);
        const fullMsg = res.data;
        store.currentMessage = fullMsg;
        const idx = store.messages.findIndex((m) => m.id === msg.id);
        if (idx !== -1) {
            store.messages[idx] = fullMsg;
        }
        if (!fullMsg.is_read) {
            await mailApi.updateMessage(store.currentMailbox, msg.id, { is_read: true });
            if (idx !== -1) {
                store.messages[idx] = { ...store.messages[idx], is_read: 1 };
            }
            store.currentMessage = { ...store.currentMessage, is_read: 1 };
        }
    }
    catch (e) {
        console.error('Failed to load message', e);
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {[typeof MailLayout, ]} */ ;
// @ts-ignore
const __VLS_0 = __VLS_asFunctionalComponent(MailLayout, new MailLayout({}));
const __VLS_1 = __VLS_0({}, ...__VLS_functionalComponentArgsRest(__VLS_0));
var __VLS_3 = {};
var __VLS_2;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            MailLayout: MailLayout,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MailView.vue.js.map