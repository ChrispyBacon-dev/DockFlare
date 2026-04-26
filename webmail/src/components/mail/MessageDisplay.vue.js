/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed, ref, watch, nextTick, onUnmounted } from 'vue';
import DOMPurify from 'dompurify';
import { Trash2, Reply, ReplyAll, Forward, MoreVertical, MailOpen, Star, Printer, FolderInput, ArrowLeft, Columns, Maximize } from 'lucide-vue-next';
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal, } from 'radix-vue';
import { DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuPortal, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent, } from 'radix-vue';
import Avatar from '../ui/Avatar.vue';
import Button from '../ui/Button.vue';
import Separator from '../ui/Separator.vue';
import Textarea from '../ui/Textarea.vue';
import AttachmentBar from './AttachmentBar.vue';
import { useMailStore } from '../../stores/mail';
import { mailApi } from '../../api/mail';
const props = defineProps({
    message: { type: Object, default: null },
});
const store = useMailStore();
const replyText = ref('');
const sendingReply = ref(false);
const emailIframe = ref(null);
const safeHtml = computed(() => {
    if (!props.message?.html_body)
        return '';
    const body = DOMPurify.sanitize(props.message.html_body, { USE_PROFILES: { html: true } });
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.5; color: #1a1a1a; word-break: break-word; }
    img { max-width: 100%; height: auto; }
    a { color: #2563eb; }
    pre, code { white-space: pre-wrap; word-break: break-all; }
    table { border-collapse: collapse; }
    /* Let email-internal containers expand to fill available width */
    body > table, body > div, body > center { width: 100% !important; max-width: 100% !important; }
  </style></head><body>${body}</body></html>`;
});
const resizeIframe = () => {
    const iframe = emailIframe.value;
    if (!iframe)
        return;
    try {
        const doc = iframe.contentDocument || iframe.contentWindow?.document;
        if (doc) {
            // Reset first so shrinking also works correctly
            iframe.style.height = '0px';
            iframe.style.height = doc.documentElement.scrollHeight + 'px';
        }
    }
    catch { }
};
// Re-measure when message changes
watch(() => props.message?.id, async () => {
    await nextTick();
    resizeIframe();
});
// Re-measure whenever the iframe's container is resized (panel drag)
let resizeObserver = null;
watch(emailIframe, (el) => {
    resizeObserver?.disconnect();
    if (!el)
        return;
    resizeObserver = new ResizeObserver(() => resizeIframe());
    // Observe the iframe's parent (the scrollable container) for width changes
    if (el.parentElement)
        resizeObserver.observe(el.parentElement);
});
onUnmounted(() => resizeObserver?.disconnect());
const parseAddrs = (raw) => {
    let addrs = [];
    try {
        addrs = JSON.parse(raw || '[]');
    }
    catch {
        addrs = [];
    }
    return addrs.map((a) => { const m = a.match(/<([^>]+)>/); return m ? m[1] : a; }).join(', ');
};
const toDisplay = computed(() => parseAddrs(props.message?.to_addresses));
const ccDisplay = computed(() => parseAddrs(props.message?.cc_addresses));
const bccDisplay = computed(() => parseAddrs(props.message?.bcc_addresses));
const displayTimestamp = computed(() => store.formatDate(props.message?.received_at || props.message?.sent_at));
const quotedBody = computed(() => {
    if (!props.message)
        return '';
    const from = props.message.from_address || '';
    const date = store.formatDate(props.message.received_at || props.message.sent_at);
    const original = props.message.html_body || `<pre>${props.message.text_body || ''}</pre>`;
    return `<br><blockquote style="border-left:2px solid #ccc;padding-left:1em;color:#555;margin:1em 0;"><p>On ${date}, ${from} wrote:</p>${original}</blockquote>`;
});
const otherFolders = computed(() => store.folders.filter((f) => f.name !== store.currentFolder));
const replyTo = () => {
    if (!props.message)
        return;
    store.composeDefaults = {
        to: props.message.from_address,
        from: props.message.received_via_alias || undefined,
        subject: props.message.subject?.startsWith('Re:')
            ? props.message.subject
            : `Re: ${props.message.subject || ''}`,
        body: '',
        quotedHtml: quotedBody.value,
    };
    store.isComposeOpen = true;
};
const replyAll = () => {
    if (!props.message)
        return;
    let toList = [];
    let ccList = [];
    try {
        toList = JSON.parse(props.message.to_addresses || '[]');
    }
    catch {
        toList = [];
    }
    try {
        ccList = JSON.parse(props.message.cc_addresses || '[]');
    }
    catch {
        ccList = [];
    }
    const allAddresses = [
        props.message.from_address,
        ...toList,
        ...ccList,
    ].filter((a) => a && a !== store.currentMailbox);
    store.composeDefaults = {
        to: allAddresses.join(', '),
        from: props.message.received_via_alias || undefined,
        subject: props.message.subject?.startsWith('Re:')
            ? props.message.subject
            : `Re: ${props.message.subject || ''}`,
        body: '',
        quotedHtml: quotedBody.value,
    };
    store.isComposeOpen = true;
};
const forwardMsg = () => {
    if (!props.message)
        return;
    store.composeDefaults = {
        to: '',
        subject: props.message.subject?.startsWith('Fwd:')
            ? props.message.subject
            : `Fwd: ${props.message.subject || ''}`,
        body: '',
        quotedHtml: quotedBody.value,
    };
    store.isComposeOpen = true;
};
const backToList = () => {
    store.currentMessage = null;
};
const trash = async () => {
    if (!props.message || !store.currentMailbox)
        return;
    try {
        await mailApi.deleteMessage(store.currentMailbox, props.message.id);
        store.messages = store.messages.filter((m) => m.id !== props.message.id);
        store.currentMessage = null;
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
    }
    catch {
        store.showToast('Failed to move message to trash');
    }
};
const markUnread = async () => {
    if (!props.message || !store.currentMailbox)
        return;
    try {
        await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_read: false });
        const idx = store.messages.findIndex((m) => m.id === props.message.id);
        if (idx !== -1)
            store.messages[idx] = { ...store.messages[idx], is_read: 0 };
        store.currentMessage = { ...store.currentMessage, is_read: 0 };
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
    }
    catch {
        store.showToast('Failed to mark as unread');
    }
};
const markRead = async () => {
    if (!props.message || !store.currentMailbox)
        return;
    try {
        await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_read: true });
        const idx = store.messages.findIndex((m) => m.id === props.message.id);
        if (idx !== -1)
            store.messages[idx] = { ...store.messages[idx], is_read: 1 };
        store.currentMessage = { ...store.currentMessage, is_read: 1 };
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
    }
    catch {
        store.showToast('Failed to mark as read');
    }
};
const toggleStar = async () => {
    if (!props.message || !store.currentMailbox)
        return;
    const newVal = props.message.is_starred ? 0 : 1;
    try {
        await mailApi.updateMessage(store.currentMailbox, props.message.id, { is_starred: newVal });
        const idx = store.messages.findIndex((m) => m.id === props.message.id);
        if (idx !== -1)
            store.messages[idx] = { ...store.messages[idx], is_starred: newVal };
        if (store.currentMessage)
            store.currentMessage = { ...store.currentMessage, is_starred: newVal };
    }
    catch {
        store.showToast('Failed to update star');
    }
};
const moveToFolder = async (targetFolder) => {
    if (!props.message || !store.currentMailbox)
        return;
    try {
        await mailApi.moveMessages(store.currentMailbox, {
            message_ids: [props.message.id],
            folder_id: targetFolder.id,
        });
        store.messages = store.messages.filter((m) => m.id !== props.message.id);
        store.currentMessage = null;
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
    }
    catch {
        store.showToast('Failed to move message');
    }
};
const escapeHtml = (str) => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const printMessage = () => {
    if (!props.message)
        return;
    const from = props.message.from_name ? `${props.message.from_name} <${props.message.from_address}>` : props.message.from_address;
    let toRaw = [];
    try {
        toRaw = JSON.parse(props.message.to_addresses || '[]');
    }
    catch {
        toRaw = [];
    }
    const to = Array.isArray(toRaw) ? toRaw.join(', ') : String(toRaw);
    const date = displayTimestamp.value;
    const subject = props.message.subject || '(No Subject)';
    let content = '';
    if (props.message.html_body) {
        content = emailIframe.value?.contentDocument?.body.innerHTML || props.message.html_body;
    }
    else {
        content = `<pre style="white-space: pre-wrap; font-family: inherit;">${props.message.text_body || ''}</pre>`;
    }
    const printWindow = window.open('', '_blank');
    if (!printWindow)
        return;
    printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${subject} - DockFlare Mail</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 40px; line-height: 1.5; color: #000; }
          .header { border-bottom: 1px solid #ccc; padding-bottom: 15px; margin-bottom: 25px; }
          .subject { font-size: 24px; font-weight: bold; margin: 0 0 15px 0; }
          .meta { font-size: 14px; color: #444; margin: 4px 0; display: flex; }
          .label { font-weight: bold; color: #666; width: 60px; flex-shrink: 0; }
          .val { flex: 1; }
          .content { margin-top: 20px; font-size: 14px; }
          img { max-width: 100%; height: auto; }
          a { color: #2563eb; text-decoration: none; }
          @media print {
            body { padding: 0; }
            @page { margin: 1cm; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1 class="subject">${escapeHtml(subject)}</h1>
          <div class="meta"><div class="label">From:</div><div class="val">${escapeHtml(from)}</div></div>
          <div class="meta"><div class="label">To:</div><div class="val">${escapeHtml(to)}</div></div>
          <div class="meta"><div class="label">Date:</div><div class="val">${date}</div></div>
        </div>
        <div class="content">
          ${content}
        </div>
      </body>
    </html>
  `);
    printWindow.document.close();
    setTimeout(() => {
        printWindow.focus();
        printWindow.print();
    }, 500);
    printWindow.onafterprint = () => {
        printWindow.close();
    };
};
const sendInlineReply = async () => {
    if (!props.message || !store.currentMailbox || !replyText.value.trim())
        return;
    if (!props.message.from_address)
        return;
    sendingReply.value = true;
    try {
        await mailApi.sendMessage(store.currentMailbox, {
            to: props.message.from_address,
            subject: props.message.subject?.startsWith('Re:')
                ? props.message.subject
                : `Re: ${props.message.subject || ''}`,
            text: replyText.value,
            html: replyText.value.replace(/\n/g, '<br>'),
            in_reply_to: props.message.message_id,
        });
        replyText.value = '';
    }
    catch {
        store.showToast('Failed to send reply');
    }
    finally {
        sendingReply.value = false;
    }
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex h-full flex-col" },
    id: "print-message-area",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "h-[52px] flex items-center px-2 flex-shrink-0 print-hide" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-2" },
});
const __VLS_0 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    delayDuration: (0),
}));
const __VLS_2 = __VLS_1({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
const __VLS_4 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    asChild: true,
}));
const __VLS_6 = __VLS_5({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
__VLS_7.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_8 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
}));
const __VLS_9 = __VLS_8({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
}, ...__VLS_functionalComponentArgsRest(__VLS_8));
let __VLS_11;
let __VLS_12;
let __VLS_13;
const __VLS_14 = {
    onClick: (__VLS_ctx.backToList)
};
__VLS_10.slots.default;
const __VLS_15 = {}.ArrowLeft;
/** @type {[typeof __VLS_components.ArrowLeft, ]} */ ;
// @ts-ignore
const __VLS_16 = __VLS_asFunctionalComponent(__VLS_15, new __VLS_15({
    ...{ class: "size-4" },
}));
const __VLS_17 = __VLS_16({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_16));
var __VLS_10;
var __VLS_7;
const __VLS_19 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_20 = __VLS_asFunctionalComponent(__VLS_19, new __VLS_19({}));
const __VLS_21 = __VLS_20({}, ...__VLS_functionalComponentArgsRest(__VLS_20));
__VLS_22.slots.default;
const __VLS_23 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_25 = __VLS_24({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_24));
__VLS_26.slots.default;
var __VLS_26;
var __VLS_22;
var __VLS_3;
/** @type {[typeof Separator, ]} */ ;
// @ts-ignore
const __VLS_27 = __VLS_asFunctionalComponent(Separator, new Separator({
    orientation: "vertical",
    ...{ class: "mx-1 h-6" },
}));
const __VLS_28 = __VLS_27({
    orientation: "vertical",
    ...{ class: "mx-1 h-6" },
}, ...__VLS_functionalComponentArgsRest(__VLS_27));
const __VLS_30 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_31 = __VLS_asFunctionalComponent(__VLS_30, new __VLS_30({
    delayDuration: (0),
}));
const __VLS_32 = __VLS_31({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_31));
__VLS_33.slots.default;
const __VLS_34 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_35 = __VLS_asFunctionalComponent(__VLS_34, new __VLS_34({
    asChild: true,
}));
const __VLS_36 = __VLS_35({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_35));
__VLS_37.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_38 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_39 = __VLS_38({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_38));
let __VLS_41;
let __VLS_42;
let __VLS_43;
const __VLS_44 = {
    onClick: (__VLS_ctx.trash)
};
__VLS_40.slots.default;
const __VLS_45 = {}.Trash2;
/** @type {[typeof __VLS_components.Trash2, ]} */ ;
// @ts-ignore
const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
    ...{ class: "size-4" },
}));
const __VLS_47 = __VLS_46({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_46));
var __VLS_40;
var __VLS_37;
const __VLS_49 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({}));
const __VLS_51 = __VLS_50({}, ...__VLS_functionalComponentArgsRest(__VLS_50));
__VLS_52.slots.default;
const __VLS_53 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_55 = __VLS_54({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_54));
__VLS_56.slots.default;
var __VLS_56;
var __VLS_52;
var __VLS_33;
const __VLS_57 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
    delayDuration: (0),
}));
const __VLS_59 = __VLS_58({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_58));
__VLS_60.slots.default;
const __VLS_61 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_62 = __VLS_asFunctionalComponent(__VLS_61, new __VLS_61({
    asChild: true,
}));
const __VLS_63 = __VLS_62({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_62));
__VLS_64.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_65 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_66 = __VLS_65({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_65));
let __VLS_68;
let __VLS_69;
let __VLS_70;
const __VLS_71 = {
    onClick: (__VLS_ctx.printMessage)
};
__VLS_67.slots.default;
const __VLS_72 = {}.Printer;
/** @type {[typeof __VLS_components.Printer, ]} */ ;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
    ...{ class: "size-4" },
}));
const __VLS_74 = __VLS_73({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
var __VLS_67;
var __VLS_64;
const __VLS_76 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({}));
const __VLS_78 = __VLS_77({}, ...__VLS_functionalComponentArgsRest(__VLS_77));
__VLS_79.slots.default;
const __VLS_80 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_82 = __VLS_81({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_81));
__VLS_83.slots.default;
var __VLS_83;
var __VLS_79;
var __VLS_60;
const __VLS_84 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
    delayDuration: (0),
}));
const __VLS_86 = __VLS_85({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_85));
__VLS_87.slots.default;
const __VLS_88 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
    asChild: true,
}));
const __VLS_90 = __VLS_89({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_89));
__VLS_91.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_92 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
}));
const __VLS_93 = __VLS_92({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
}, ...__VLS_functionalComponentArgsRest(__VLS_92));
let __VLS_95;
let __VLS_96;
let __VLS_97;
const __VLS_98 = {
    onClick: (...[$event]) => {
        __VLS_ctx.store.toggleViewMode();
    }
};
__VLS_94.slots.default;
if (__VLS_ctx.store.viewMode === 'full') {
    const __VLS_99 = {}.Columns;
    /** @type {[typeof __VLS_components.Columns, ]} */ ;
    // @ts-ignore
    const __VLS_100 = __VLS_asFunctionalComponent(__VLS_99, new __VLS_99({
        ...{ class: "size-4" },
    }));
    const __VLS_101 = __VLS_100({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_100));
}
else {
    const __VLS_103 = {}.Maximize;
    /** @type {[typeof __VLS_components.Maximize, ]} */ ;
    // @ts-ignore
    const __VLS_104 = __VLS_asFunctionalComponent(__VLS_103, new __VLS_103({
        ...{ class: "size-4" },
    }));
    const __VLS_105 = __VLS_104({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_104));
}
var __VLS_94;
var __VLS_91;
const __VLS_107 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_108 = __VLS_asFunctionalComponent(__VLS_107, new __VLS_107({}));
const __VLS_109 = __VLS_108({}, ...__VLS_functionalComponentArgsRest(__VLS_108));
__VLS_110.slots.default;
const __VLS_111 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_112 = __VLS_asFunctionalComponent(__VLS_111, new __VLS_111({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_113 = __VLS_112({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_112));
__VLS_114.slots.default;
(__VLS_ctx.store.viewMode === 'full' ? 'Split view' : 'Full view');
var __VLS_114;
var __VLS_110;
var __VLS_87;
/** @type {[typeof Separator, ]} */ ;
// @ts-ignore
const __VLS_115 = __VLS_asFunctionalComponent(Separator, new Separator({
    orientation: "vertical",
    ...{ class: "mx-1 h-6" },
}));
const __VLS_116 = __VLS_115({
    orientation: "vertical",
    ...{ class: "mx-1 h-6" },
}, ...__VLS_functionalComponentArgsRest(__VLS_115));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "ml-auto flex items-center gap-2" },
});
const __VLS_118 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_119 = __VLS_asFunctionalComponent(__VLS_118, new __VLS_118({
    delayDuration: (0),
}));
const __VLS_120 = __VLS_119({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_119));
__VLS_121.slots.default;
const __VLS_122 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_123 = __VLS_asFunctionalComponent(__VLS_122, new __VLS_122({
    asChild: true,
}));
const __VLS_124 = __VLS_123({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_123));
__VLS_125.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_126 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_127 = __VLS_126({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_126));
let __VLS_129;
let __VLS_130;
let __VLS_131;
const __VLS_132 = {
    onClick: (__VLS_ctx.replyTo)
};
__VLS_128.slots.default;
const __VLS_133 = {}.Reply;
/** @type {[typeof __VLS_components.Reply, ]} */ ;
// @ts-ignore
const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
    ...{ class: "size-4" },
}));
const __VLS_135 = __VLS_134({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_134));
var __VLS_128;
var __VLS_125;
const __VLS_137 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_138 = __VLS_asFunctionalComponent(__VLS_137, new __VLS_137({}));
const __VLS_139 = __VLS_138({}, ...__VLS_functionalComponentArgsRest(__VLS_138));
__VLS_140.slots.default;
const __VLS_141 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_142 = __VLS_asFunctionalComponent(__VLS_141, new __VLS_141({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_143 = __VLS_142({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_142));
__VLS_144.slots.default;
var __VLS_144;
var __VLS_140;
var __VLS_121;
const __VLS_145 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_146 = __VLS_asFunctionalComponent(__VLS_145, new __VLS_145({
    delayDuration: (0),
}));
const __VLS_147 = __VLS_146({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_146));
__VLS_148.slots.default;
const __VLS_149 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_150 = __VLS_asFunctionalComponent(__VLS_149, new __VLS_149({
    asChild: true,
}));
const __VLS_151 = __VLS_150({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_150));
__VLS_152.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_153 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_154 = __VLS_153({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_153));
let __VLS_156;
let __VLS_157;
let __VLS_158;
const __VLS_159 = {
    onClick: (__VLS_ctx.replyAll)
};
__VLS_155.slots.default;
const __VLS_160 = {}.ReplyAll;
/** @type {[typeof __VLS_components.ReplyAll, ]} */ ;
// @ts-ignore
const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
    ...{ class: "size-4" },
}));
const __VLS_162 = __VLS_161({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_161));
var __VLS_155;
var __VLS_152;
const __VLS_164 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({}));
const __VLS_166 = __VLS_165({}, ...__VLS_functionalComponentArgsRest(__VLS_165));
__VLS_167.slots.default;
const __VLS_168 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_170 = __VLS_169({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_169));
__VLS_171.slots.default;
var __VLS_171;
var __VLS_167;
var __VLS_148;
const __VLS_172 = {}.TooltipRoot;
/** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
// @ts-ignore
const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
    delayDuration: (0),
}));
const __VLS_174 = __VLS_173({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_173));
__VLS_175.slots.default;
const __VLS_176 = {}.TooltipTrigger;
/** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
// @ts-ignore
const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
    asChild: true,
}));
const __VLS_178 = __VLS_177({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_177));
__VLS_179.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_180 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_181 = __VLS_180({
    ...{ 'onClick': {} },
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_180));
let __VLS_183;
let __VLS_184;
let __VLS_185;
const __VLS_186 = {
    onClick: (__VLS_ctx.forwardMsg)
};
__VLS_182.slots.default;
const __VLS_187 = {}.Forward;
/** @type {[typeof __VLS_components.Forward, ]} */ ;
// @ts-ignore
const __VLS_188 = __VLS_asFunctionalComponent(__VLS_187, new __VLS_187({
    ...{ class: "size-4" },
}));
const __VLS_189 = __VLS_188({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_188));
var __VLS_182;
var __VLS_179;
const __VLS_191 = {}.TooltipPortal;
/** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
// @ts-ignore
const __VLS_192 = __VLS_asFunctionalComponent(__VLS_191, new __VLS_191({}));
const __VLS_193 = __VLS_192({}, ...__VLS_functionalComponentArgsRest(__VLS_192));
__VLS_194.slots.default;
const __VLS_195 = {}.TooltipContent;
/** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
// @ts-ignore
const __VLS_196 = __VLS_asFunctionalComponent(__VLS_195, new __VLS_195({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}));
const __VLS_197 = __VLS_196({
    ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_196));
__VLS_198.slots.default;
var __VLS_198;
var __VLS_194;
var __VLS_175;
/** @type {[typeof Separator, ]} */ ;
// @ts-ignore
const __VLS_199 = __VLS_asFunctionalComponent(Separator, new Separator({
    orientation: "vertical",
    ...{ class: "mx-2 h-6" },
}));
const __VLS_200 = __VLS_199({
    orientation: "vertical",
    ...{ class: "mx-2 h-6" },
}, ...__VLS_functionalComponentArgsRest(__VLS_199));
const __VLS_202 = {}.DropdownMenuRoot;
/** @type {[typeof __VLS_components.DropdownMenuRoot, typeof __VLS_components.DropdownMenuRoot, ]} */ ;
// @ts-ignore
const __VLS_203 = __VLS_asFunctionalComponent(__VLS_202, new __VLS_202({}));
const __VLS_204 = __VLS_203({}, ...__VLS_functionalComponentArgsRest(__VLS_203));
__VLS_205.slots.default;
const __VLS_206 = {}.DropdownMenuTrigger;
/** @type {[typeof __VLS_components.DropdownMenuTrigger, typeof __VLS_components.DropdownMenuTrigger, ]} */ ;
// @ts-ignore
const __VLS_207 = __VLS_asFunctionalComponent(__VLS_206, new __VLS_206({
    asChild: true,
}));
const __VLS_208 = __VLS_207({
    asChild: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_207));
__VLS_209.slots.default;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_210 = __VLS_asFunctionalComponent(Button, new Button({
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}));
const __VLS_211 = __VLS_210({
    variant: "ghost",
    size: "icon",
    disabled: (!__VLS_ctx.message),
}, ...__VLS_functionalComponentArgsRest(__VLS_210));
__VLS_212.slots.default;
const __VLS_213 = {}.MoreVertical;
/** @type {[typeof __VLS_components.MoreVertical, ]} */ ;
// @ts-ignore
const __VLS_214 = __VLS_asFunctionalComponent(__VLS_213, new __VLS_213({
    ...{ class: "size-4" },
}));
const __VLS_215 = __VLS_214({
    ...{ class: "size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_214));
var __VLS_212;
var __VLS_209;
const __VLS_217 = {}.DropdownMenuPortal;
/** @type {[typeof __VLS_components.DropdownMenuPortal, typeof __VLS_components.DropdownMenuPortal, ]} */ ;
// @ts-ignore
const __VLS_218 = __VLS_asFunctionalComponent(__VLS_217, new __VLS_217({}));
const __VLS_219 = __VLS_218({}, ...__VLS_functionalComponentArgsRest(__VLS_218));
__VLS_220.slots.default;
const __VLS_221 = {}.DropdownMenuContent;
/** @type {[typeof __VLS_components.DropdownMenuContent, typeof __VLS_components.DropdownMenuContent, ]} */ ;
// @ts-ignore
const __VLS_222 = __VLS_asFunctionalComponent(__VLS_221, new __VLS_221({
    align: "end",
    ...{ class: "z-50 min-w-[160px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
}));
const __VLS_223 = __VLS_222({
    align: "end",
    ...{ class: "z-50 min-w-[160px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_222));
__VLS_224.slots.default;
if (props.message?.is_read) {
    const __VLS_225 = {}.DropdownMenuItem;
    /** @type {[typeof __VLS_components.DropdownMenuItem, typeof __VLS_components.DropdownMenuItem, ]} */ ;
    // @ts-ignore
    const __VLS_226 = __VLS_asFunctionalComponent(__VLS_225, new __VLS_225({
        ...{ 'onClick': {} },
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }));
    const __VLS_227 = __VLS_226({
        ...{ 'onClick': {} },
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_226));
    let __VLS_229;
    let __VLS_230;
    let __VLS_231;
    const __VLS_232 = {
        onClick: (__VLS_ctx.markUnread)
    };
    __VLS_228.slots.default;
    const __VLS_233 = {}.MailOpen;
    /** @type {[typeof __VLS_components.MailOpen, ]} */ ;
    // @ts-ignore
    const __VLS_234 = __VLS_asFunctionalComponent(__VLS_233, new __VLS_233({
        ...{ class: "mr-2 size-4" },
    }));
    const __VLS_235 = __VLS_234({
        ...{ class: "mr-2 size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_234));
    var __VLS_228;
}
else {
    const __VLS_237 = {}.DropdownMenuItem;
    /** @type {[typeof __VLS_components.DropdownMenuItem, typeof __VLS_components.DropdownMenuItem, ]} */ ;
    // @ts-ignore
    const __VLS_238 = __VLS_asFunctionalComponent(__VLS_237, new __VLS_237({
        ...{ 'onClick': {} },
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }));
    const __VLS_239 = __VLS_238({
        ...{ 'onClick': {} },
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_238));
    let __VLS_241;
    let __VLS_242;
    let __VLS_243;
    const __VLS_244 = {
        onClick: (__VLS_ctx.markRead)
    };
    __VLS_240.slots.default;
    const __VLS_245 = {}.MailOpen;
    /** @type {[typeof __VLS_components.MailOpen, ]} */ ;
    // @ts-ignore
    const __VLS_246 = __VLS_asFunctionalComponent(__VLS_245, new __VLS_245({
        ...{ class: "mr-2 size-4" },
    }));
    const __VLS_247 = __VLS_246({
        ...{ class: "mr-2 size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_246));
    var __VLS_240;
}
const __VLS_249 = {}.DropdownMenuItem;
/** @type {[typeof __VLS_components.DropdownMenuItem, typeof __VLS_components.DropdownMenuItem, ]} */ ;
// @ts-ignore
const __VLS_250 = __VLS_asFunctionalComponent(__VLS_249, new __VLS_249({
    ...{ 'onClick': {} },
    ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
}));
const __VLS_251 = __VLS_250({
    ...{ 'onClick': {} },
    ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
}, ...__VLS_functionalComponentArgsRest(__VLS_250));
let __VLS_253;
let __VLS_254;
let __VLS_255;
const __VLS_256 = {
    onClick: (__VLS_ctx.toggleStar)
};
__VLS_252.slots.default;
const __VLS_257 = {}.Star;
/** @type {[typeof __VLS_components.Star, ]} */ ;
// @ts-ignore
const __VLS_258 = __VLS_asFunctionalComponent(__VLS_257, new __VLS_257({
    ...{ class: "mr-2 size-4" },
}));
const __VLS_259 = __VLS_258({
    ...{ class: "mr-2 size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_258));
(__VLS_ctx.message?.is_starred ? 'Unstar' : 'Star');
var __VLS_252;
const __VLS_261 = {}.DropdownMenuSeparator;
/** @type {[typeof __VLS_components.DropdownMenuSeparator, ]} */ ;
// @ts-ignore
const __VLS_262 = __VLS_asFunctionalComponent(__VLS_261, new __VLS_261({
    ...{ class: "my-1 h-px bg-border" },
}));
const __VLS_263 = __VLS_262({
    ...{ class: "my-1 h-px bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_262));
const __VLS_265 = {}.DropdownMenuSub;
/** @type {[typeof __VLS_components.DropdownMenuSub, typeof __VLS_components.DropdownMenuSub, ]} */ ;
// @ts-ignore
const __VLS_266 = __VLS_asFunctionalComponent(__VLS_265, new __VLS_265({}));
const __VLS_267 = __VLS_266({}, ...__VLS_functionalComponentArgsRest(__VLS_266));
__VLS_268.slots.default;
const __VLS_269 = {}.DropdownMenuSubTrigger;
/** @type {[typeof __VLS_components.DropdownMenuSubTrigger, typeof __VLS_components.DropdownMenuSubTrigger, ]} */ ;
// @ts-ignore
const __VLS_270 = __VLS_asFunctionalComponent(__VLS_269, new __VLS_269({
    ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
}));
const __VLS_271 = __VLS_270({
    ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
}, ...__VLS_functionalComponentArgsRest(__VLS_270));
__VLS_272.slots.default;
const __VLS_273 = {}.FolderInput;
/** @type {[typeof __VLS_components.FolderInput, ]} */ ;
// @ts-ignore
const __VLS_274 = __VLS_asFunctionalComponent(__VLS_273, new __VLS_273({
    ...{ class: "mr-2 size-4" },
}));
const __VLS_275 = __VLS_274({
    ...{ class: "mr-2 size-4" },
}, ...__VLS_functionalComponentArgsRest(__VLS_274));
var __VLS_272;
const __VLS_277 = {}.DropdownMenuPortal;
/** @type {[typeof __VLS_components.DropdownMenuPortal, typeof __VLS_components.DropdownMenuPortal, ]} */ ;
// @ts-ignore
const __VLS_278 = __VLS_asFunctionalComponent(__VLS_277, new __VLS_277({}));
const __VLS_279 = __VLS_278({}, ...__VLS_functionalComponentArgsRest(__VLS_278));
__VLS_280.slots.default;
const __VLS_281 = {}.DropdownMenuSubContent;
/** @type {[typeof __VLS_components.DropdownMenuSubContent, typeof __VLS_components.DropdownMenuSubContent, ]} */ ;
// @ts-ignore
const __VLS_282 = __VLS_asFunctionalComponent(__VLS_281, new __VLS_281({
    ...{ class: "z-50 min-w-[140px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
}));
const __VLS_283 = __VLS_282({
    ...{ class: "z-50 min-w-[140px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
}, ...__VLS_functionalComponentArgsRest(__VLS_282));
__VLS_284.slots.default;
for (const [f] of __VLS_getVForSourceType((__VLS_ctx.otherFolders))) {
    const __VLS_285 = {}.DropdownMenuItem;
    /** @type {[typeof __VLS_components.DropdownMenuItem, typeof __VLS_components.DropdownMenuItem, ]} */ ;
    // @ts-ignore
    const __VLS_286 = __VLS_asFunctionalComponent(__VLS_285, new __VLS_285({
        ...{ 'onClick': {} },
        key: (f.id),
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }));
    const __VLS_287 = __VLS_286({
        ...{ 'onClick': {} },
        key: (f.id),
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_286));
    let __VLS_289;
    let __VLS_290;
    let __VLS_291;
    const __VLS_292 = {
        onClick: (...[$event]) => {
            __VLS_ctx.moveToFolder(f);
        }
    };
    __VLS_288.slots.default;
    if (f.color) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span)({
            ...{ class: "mr-2 inline-block h-2 w-2 rounded-full flex-shrink-0" },
            ...{ style: (`background:${f.color}`) },
        });
    }
    (f.name);
    var __VLS_288;
}
var __VLS_284;
var __VLS_280;
var __VLS_268;
var __VLS_224;
var __VLS_220;
var __VLS_205;
if (__VLS_ctx.message) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "print-header hidden print:block p-4 border-b" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "text-lg font-bold" },
    });
    (__VLS_ctx.message.subject);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "text-sm text-muted-foreground mt-1" },
    });
    (__VLS_ctx.message.from_name ? `${__VLS_ctx.message.from_name} <${__VLS_ctx.message.from_address}>` : __VLS_ctx.message.from_address);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "text-sm text-muted-foreground" },
    });
    (__VLS_ctx.displayTimestamp);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-start p-4" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-start gap-4 text-sm" },
    });
    /** @type {[typeof Avatar, ]} */ ;
    // @ts-ignore
    const __VLS_293 = __VLS_asFunctionalComponent(Avatar, new Avatar({
        initials: (__VLS_ctx.message.from_name?.[0] || __VLS_ctx.message.from_address?.[0] || '?'),
    }));
    const __VLS_294 = __VLS_293({
        initials: (__VLS_ctx.message.from_name?.[0] || __VLS_ctx.message.from_address?.[0] || '?'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_293));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "grid gap-1" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "font-semibold" },
    });
    (__VLS_ctx.message.from_name || __VLS_ctx.message.from_address);
    if (__VLS_ctx.toDisplay) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "line-clamp-1 text-xs" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-medium" },
        });
        (__VLS_ctx.toDisplay);
    }
    if (__VLS_ctx.ccDisplay) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "line-clamp-1 text-xs" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-medium" },
        });
        (__VLS_ctx.ccDisplay);
    }
    if (__VLS_ctx.bccDisplay) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "line-clamp-1 text-xs" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-medium" },
        });
        (__VLS_ctx.bccDisplay);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "line-clamp-1 text-xs" },
    });
    (__VLS_ctx.message.subject);
    if (__VLS_ctx.displayTimestamp) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "ml-auto text-xs text-muted-foreground" },
        });
        (__VLS_ctx.displayTimestamp);
    }
    /** @type {[typeof Separator, ]} */ ;
    // @ts-ignore
    const __VLS_296 = __VLS_asFunctionalComponent(Separator, new Separator({}));
    const __VLS_297 = __VLS_296({}, ...__VLS_functionalComponentArgsRest(__VLS_296));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-1 overflow-y-auto" },
    });
    if (__VLS_ctx.message.html_body) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.iframe)({
            ...{ onLoad: (__VLS_ctx.resizeIframe) },
            ref: "emailIframe",
            srcdoc: (__VLS_ctx.safeHtml),
            sandbox: "allow-same-origin allow-popups",
            referrerpolicy: "no-referrer",
            ...{ class: "w-full border-0 block" },
            ...{ style: {} },
        });
        /** @type {typeof __VLS_ctx.emailIframe} */ ;
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "p-4 text-sm whitespace-pre-wrap" },
        });
        (__VLS_ctx.message.text_body);
    }
    /** @type {[typeof AttachmentBar, ]} */ ;
    // @ts-ignore
    const __VLS_299 = __VLS_asFunctionalComponent(AttachmentBar, new AttachmentBar({
        attachments: (__VLS_ctx.message.attachments),
    }));
    const __VLS_300 = __VLS_299({
        attachments: (__VLS_ctx.message.attachments),
    }, ...__VLS_functionalComponentArgsRest(__VLS_299));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "p-4 print-hide" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.form, __VLS_intrinsicElements.form)({
        ...{ onSubmit: (__VLS_ctx.sendInlineReply) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "grid gap-3" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "df-reply-wrapper rounded-2xl p-3" },
    });
    /** @type {[typeof Textarea, ]} */ ;
    // @ts-ignore
    const __VLS_302 = __VLS_asFunctionalComponent(Textarea, new Textarea({
        modelValue: (__VLS_ctx.replyText),
        ...{ class: "p-2 min-h-[80px] bg-transparent border-0 shadow-none focus-visible:ring-0" },
        placeholder: (`Reply ${__VLS_ctx.message.from_name || __VLS_ctx.message.from_address}...`),
    }));
    const __VLS_303 = __VLS_302({
        modelValue: (__VLS_ctx.replyText),
        ...{ class: "p-2 min-h-[80px] bg-transparent border-0 shadow-none focus-visible:ring-0" },
        placeholder: (`Reply ${__VLS_ctx.message.from_name || __VLS_ctx.message.from_address}...`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_302));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center" },
    });
    /** @type {[typeof Button, typeof Button, ]} */ ;
    // @ts-ignore
    const __VLS_305 = __VLS_asFunctionalComponent(Button, new Button({
        type: "submit",
        size: "sm",
        ...{ class: "ml-auto" },
        disabled: (__VLS_ctx.sendingReply || !__VLS_ctx.replyText.trim()),
    }));
    const __VLS_306 = __VLS_305({
        type: "submit",
        size: "sm",
        ...{ class: "ml-auto" },
        disabled: (__VLS_ctx.sendingReply || !__VLS_ctx.replyText.trim()),
    }, ...__VLS_functionalComponentArgsRest(__VLS_305));
    __VLS_307.slots.default;
    (__VLS_ctx.sendingReply ? 'Sending...' : 'Send');
    var __VLS_307;
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex flex-1 items-center justify-center p-8 text-muted-foreground" },
    });
}
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[52px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['print-hide']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-6']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-6']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-2']} */ ;
/** @type {__VLS_StyleScopedClasses['h-6']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-[160px]']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['my-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-[140px]']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-2']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-block']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['print-header']} */ ;
/** @type {__VLS_StyleScopedClasses['hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['print:block']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['text-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-start']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-start']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['line-clamp-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['line-clamp-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['line-clamp-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['line-clamp-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-0']} */ ;
/** @type {__VLS_StyleScopedClasses['block']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-pre-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['print-hide']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['df-reply-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-2xl']} */ ;
/** @type {__VLS_StyleScopedClasses['p-3']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[80px]']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['border-0']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-8']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Trash2: Trash2,
            Reply: Reply,
            ReplyAll: ReplyAll,
            Forward: Forward,
            MoreVertical: MoreVertical,
            MailOpen: MailOpen,
            Star: Star,
            Printer: Printer,
            FolderInput: FolderInput,
            ArrowLeft: ArrowLeft,
            Columns: Columns,
            Maximize: Maximize,
            TooltipRoot: TooltipRoot,
            TooltipTrigger: TooltipTrigger,
            TooltipContent: TooltipContent,
            TooltipPortal: TooltipPortal,
            DropdownMenuRoot: DropdownMenuRoot,
            DropdownMenuTrigger: DropdownMenuTrigger,
            DropdownMenuContent: DropdownMenuContent,
            DropdownMenuItem: DropdownMenuItem,
            DropdownMenuSeparator: DropdownMenuSeparator,
            DropdownMenuPortal: DropdownMenuPortal,
            DropdownMenuSub: DropdownMenuSub,
            DropdownMenuSubTrigger: DropdownMenuSubTrigger,
            DropdownMenuSubContent: DropdownMenuSubContent,
            Avatar: Avatar,
            Button: Button,
            Separator: Separator,
            Textarea: Textarea,
            AttachmentBar: AttachmentBar,
            store: store,
            replyText: replyText,
            sendingReply: sendingReply,
            emailIframe: emailIframe,
            safeHtml: safeHtml,
            resizeIframe: resizeIframe,
            toDisplay: toDisplay,
            ccDisplay: ccDisplay,
            bccDisplay: bccDisplay,
            displayTimestamp: displayTimestamp,
            otherFolders: otherFolders,
            replyTo: replyTo,
            replyAll: replyAll,
            forwardMsg: forwardMsg,
            backToList: backToList,
            trash: trash,
            markUnread: markUnread,
            markRead: markRead,
            toggleStar: toggleStar,
            moveToFolder: moveToFolder,
            printMessage: printMessage,
            sendInlineReply: sendInlineReply,
        };
    },
    props: {
        message: { type: Object, default: null },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        message: { type: Object, default: null },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MessageDisplay.vue.js.map