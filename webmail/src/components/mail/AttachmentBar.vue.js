/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref } from 'vue';
import { Paperclip, Download } from 'lucide-vue-next';
import { mailApi } from '../../api/mail';
import Button from '../ui/Button.vue';
const __VLS_props = defineProps({
    attachments: { type: Array, default: () => [] },
});
const downloading = ref(null);
const formatSize = (bytes) => {
    if (bytes >= 1_048_576)
        return `${(bytes / 1_048_576).toFixed(1)} MB`;
    if (bytes >= 1024)
        return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
};
const download = async (att) => {
    downloading.value = att.id;
    try {
        const blob = await mailApi.downloadAttachment(att.id);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = att.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    catch (e) {
        console.error('Download failed', e);
    }
    finally {
        downloading.value = null;
    }
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
if (__VLS_ctx.attachments && __VLS_ctx.attachments.length > 0) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex flex-wrap gap-2 border-t p-4" },
    });
    for (const [att] of __VLS_getVForSourceType(__VLS_ctx.attachments)) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            key: (att.id),
            ...{ class: "flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm" },
        });
        const __VLS_0 = {}.Paperclip;
        /** @type {[typeof __VLS_components.Paperclip, ]} */ ;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
            ...{ class: "size-4 text-muted-foreground shrink-0" },
        }));
        const __VLS_2 = __VLS_1({
            ...{ class: "size-4 text-muted-foreground shrink-0" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "truncate max-w-[180px]" },
        });
        (att.filename);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-xs text-muted-foreground whitespace-nowrap" },
        });
        (__VLS_ctx.formatSize(att.size_bytes));
        /** @type {[typeof Button, typeof Button, ]} */ ;
        // @ts-ignore
        const __VLS_4 = __VLS_asFunctionalComponent(Button, new Button({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
            ...{ class: "h-7 w-7 p-0" },
            disabled: (__VLS_ctx.downloading === att.id),
        }));
        const __VLS_5 = __VLS_4({
            ...{ 'onClick': {} },
            variant: "ghost",
            size: "sm",
            ...{ class: "h-7 w-7 p-0" },
            disabled: (__VLS_ctx.downloading === att.id),
        }, ...__VLS_functionalComponentArgsRest(__VLS_4));
        let __VLS_7;
        let __VLS_8;
        let __VLS_9;
        const __VLS_10 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.attachments && __VLS_ctx.attachments.length > 0))
                    return;
                __VLS_ctx.download(att);
            }
        };
        __VLS_6.slots.default;
        const __VLS_11 = {}.Download;
        /** @type {[typeof __VLS_components.Download, ]} */ ;
        // @ts-ignore
        const __VLS_12 = __VLS_asFunctionalComponent(__VLS_11, new __VLS_11({
            ...{ class: "size-4" },
        }));
        const __VLS_13 = __VLS_12({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_12));
        var __VLS_6;
    }
}
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted/40']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['max-w-[180px]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['h-7']} */ ;
/** @type {__VLS_StyleScopedClasses['w-7']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Paperclip: Paperclip,
            Download: Download,
            Button: Button,
            downloading: downloading,
            formatSize: formatSize,
            download: download,
        };
    },
    props: {
        attachments: { type: Array, default: () => [] },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        attachments: { type: Array, default: () => [] },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=AttachmentBar.vue.js.map