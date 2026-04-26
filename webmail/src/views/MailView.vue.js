/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useMail } from '../composables/useMail';
import { useMailPolling } from '../composables/useMailPolling';
import { useNotificationsStore } from '../stores/notifications';
import { mailApi } from '../api/mail';
import MailLayout from '../components/mail/MailLayout.vue';
const route = useRoute();
const { store, loadMailboxes } = useMail();
const mailStore = store;
const notificationsStore = useNotificationsStore();
useMailPolling();
const showNotifPrompt = ref(false);
let mailboxLoadSeq = 0;
const loadMessages = async (addr, folder, page = 1) => {
    if (!addr || !folder)
        return;
    if (page === 1) {
        store.messagesLoading = true;
        store.messages = [];
        store.messagesPage = 1;
    }
    else {
        store.isFetchingNextPage = true;
    }
    try {
        const mRes = await mailApi.getMessages(addr, { folder, order: store.sortOrder, page, per_page: 50 });
        const payload = mRes.data;
        const items = Array.isArray(payload) ? payload : payload.items || [];
        store.messages = page === 1 ? items : [...store.messages, ...items];
        store.totalMessages = payload.total ?? items.length;
        store.messagesPage = page;
        store.hasMoreMessages = items.length === 50;
        if (page === 1)
            store.currentMessage = null;
    }
    catch {
        store.showToast('Failed to load messages');
    }
    finally {
        store.messagesLoading = false;
        store.isFetchingNextPage = false;
    }
};
store.registerLoadMore(() => {
    if (store.hasMoreMessages && !store.isFetchingNextPage) {
        loadMessages(store.currentMailbox, store.currentFolder, store.messagesPage + 1);
    }
});
async function enableNotifications() {
    await notificationsStore.requestPermission();
    showNotifPrompt.value = false;
    localStorage.setItem('notif_prompted', '1');
    if (notificationsStore.isGranted) {
        mailStore.isSettingsOpen = true;
    }
}
function dismissPrompt() {
    showNotifPrompt.value = false;
    localStorage.setItem('notif_prompted', '1');
}
onMounted(async () => {
    await loadMailboxes();
    const mailboxParam = route.query.mailbox;
    if (mailboxParam) {
        const found = store.mailboxes.find((b) => b.address === mailboxParam);
        if (found)
            store.currentMailbox = mailboxParam;
    }
    if (Notification.permission === 'default' && !localStorage.getItem('notif_prompted')) {
        showNotifPrompt.value = true;
    }
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.addEventListener('message', (ev) => {
            if (ev.data?.type === 'NOTIFICATION_CLICK' && ev.data.mailbox) {
                store.currentMailbox = ev.data.mailbox;
            }
            if (ev.data?.type === 'SET_BADGE') {
                const count = ev.data.count ?? 0;
                if ('setAppBadge' in navigator) {
                    if (count > 0) {
                        navigator.setAppBadge(count).catch(() => { });
                    }
                    else {
                        navigator.clearAppBadge().catch(() => { });
                    }
                }
            }
        });
    }
});
watch(() => store.currentMailbox, async (addr) => {
    if (!addr)
        return;
    const seq = ++mailboxLoadSeq;
    try {
        const fRes = await mailApi.getFolders(addr);
        if (seq !== mailboxLoadSeq)
            return;
        store.folders = fRes.data;
        if (store.folders.length > 0) {
            const inbox = store.folders.find((f) => f.name.toLowerCase() === 'inbox');
            store.currentFolder = inbox ? inbox.name : store.folders[0].name;
        }
    }
    catch {
        if (seq !== mailboxLoadSeq)
            return;
        store.showToast('Failed to load folders');
    }
});
watch(() => [store.currentMailbox, store.currentFolder], ([addr, folder]) => {
    loadMessages(addr, folder);
});
watch(() => store.sortOrder, () => {
    loadMessages(store.currentMailbox, store.currentFolder);
});
let openedMessageId = null;
watch(() => store.currentMessage, async (msg) => {
    if (!msg)
        return;
    try {
        const idx = store.messages.findIndex((m) => m.id === msg.id);
        let fullMsg = msg;
        const isUserOpen = msg.attachments === undefined || msg.id !== openedMessageId;
        if (msg.attachments === undefined) {
            const res = await mailApi.getMessage(store.currentMailbox, msg.id);
            fullMsg = res.data;
            store.currentMessage = fullMsg;
            if (idx !== -1)
                store.messages[idx] = fullMsg;
        }
        if (!fullMsg.is_read && isUserOpen) {
            openedMessageId = msg.id;
            await mailApi.updateMessage(store.currentMailbox, msg.id, { is_read: true });
            if (idx !== -1) {
                store.messages[idx] = { ...store.messages[idx], is_read: 1 };
            }
            store.currentMessage = { ...store.currentMessage, is_read: 1 };
            const fRes = await mailApi.getFolders(store.currentMailbox);
            store.folders = fRes.data;
        }
        else {
            openedMessageId = msg.id;
        }
    }
    catch {
        store.showToast('Failed to load message');
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "relative h-full" },
});
/** @type {[typeof MailLayout, ]} */ ;
// @ts-ignore
const __VLS_0 = __VLS_asFunctionalComponent(MailLayout, new MailLayout({}));
const __VLS_1 = __VLS_0({}, ...__VLS_functionalComponentArgsRest(__VLS_0));
const __VLS_3 = {}.Transition;
/** @type {[typeof __VLS_components.Transition, typeof __VLS_components.Transition, ]} */ ;
// @ts-ignore
const __VLS_4 = __VLS_asFunctionalComponent(__VLS_3, new __VLS_3({
    name: "slide-up",
}));
const __VLS_5 = __VLS_4({
    name: "slide-up",
}, ...__VLS_functionalComponentArgsRest(__VLS_4));
__VLS_6.slots.default;
if (__VLS_ctx.showNotifPrompt) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-xl border bg-background shadow-lg px-5 py-3.5 text-sm" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "text-muted-foreground" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.enableNotifications) },
        ...{ class: "inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.dismissPrompt) },
        ...{ class: "text-muted-foreground hover:text-foreground transition-colors" },
    });
}
var __VLS_6;
const __VLS_7 = {}.Transition;
/** @type {[typeof __VLS_components.Transition, typeof __VLS_components.Transition, ]} */ ;
// @ts-ignore
const __VLS_8 = __VLS_asFunctionalComponent(__VLS_7, new __VLS_7({
    name: "slide-up",
}));
const __VLS_9 = __VLS_8({
    name: "slide-up",
}, ...__VLS_functionalComponentArgsRest(__VLS_8));
__VLS_10.slots.default;
if (__VLS_ctx.store.toast) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-xl border px-5 py-3.5 text-sm shadow-lg" },
        ...{ class: (__VLS_ctx.store.toast.type === 'error'
                ? 'bg-destructive text-destructive-foreground border-destructive'
                : __VLS_ctx.store.toast.type === 'success'
                    ? 'bg-green-600 text-white border-green-700'
                    : 'bg-background text-foreground border-border') },
    });
    (__VLS_ctx.store.toast.message);
}
var __VLS_10;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['bottom-4']} */ ;
/** @type {__VLS_StyleScopedClasses['left-1/2']} */ ;
/** @type {__VLS_StyleScopedClasses['-translate-x-1/2']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-4']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['px-5']} */ ;
/** @type {__VLS_StyleScopedClasses['py-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['bottom-4']} */ ;
/** @type {__VLS_StyleScopedClasses['right-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['px-5']} */ ;
/** @type {__VLS_StyleScopedClasses['py-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-lg']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            MailLayout: MailLayout,
            store: store,
            showNotifPrompt: showNotifPrompt,
            enableNotifications: enableNotifications,
            dismissPrompt: dismissPrompt,
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