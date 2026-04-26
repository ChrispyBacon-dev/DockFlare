/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { formatDistanceToNow } from 'date-fns';
import { Paperclip, Star, Check } from 'lucide-vue-next';
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue';
import { cn } from '../../lib/utils';
import Badge from '../ui/Badge.vue';
import { useMailStore } from '../../stores/mail';
const props = defineProps({
    message: { type: Object, required: true },
    selected: { type: Boolean, default: false },
    folderColor: { type: String, default: '' },
    bulkSelectMode: { type: Boolean, default: false },
    isChecked: { type: Boolean, default: false },
});
const initials = computed(() => {
    const name = props.message.from_name || props.message.from_address || '?';
    return name.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase();
});
const store = useMailStore();
const timestamp = computed(() => props.message.received_at || props.message.sent_at);
const relativeTime = computed(() => timestamp.value ? formatDistanceToNow(new Date(timestamp.value), { addSuffix: true }) : '');
const exactTime = computed(() => store.formatDate(timestamp.value));
const isSentOrDrafts = computed(() => {
    const name = store.currentFolderObj?.name?.toLowerCase() ?? '';
    return name === 'sent' || name === 'drafts';
});
const recipientLabel = computed(() => {
    if (!isSentOrDrafts.value)
        return null;
    let addrs = [];
    try {
        addrs = JSON.parse(props.message.to_addresses || '[]');
    }
    catch {
        addrs = [];
    }
    if (!addrs.length)
        return null;
    return 'To: ' + addrs.map((a) => {
        const m = a.match(/<([^>]+)>/);
        return m ? m[1] : a;
    }).join(', ');
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['df-msg-item']} */ ;
/** @type {__VLS_StyleScopedClasses['df-msg-item']} */ ;
/** @type {__VLS_StyleScopedClasses['dark']} */ ;
/** @type {__VLS_StyleScopedClasses['df-msg-selected']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: (__VLS_ctx.cn('df-msg-item flex items-start gap-3 rounded-xl p-3 text-left text-sm w-full', __VLS_ctx.selected && 'df-msg-selected')) },
    ...{ style: (__VLS_ctx.folderColor ? `border-left: 3px solid ${__VLS_ctx.folderColor}; border-radius: 12px 0 0 12px;` : '') },
});
if (__VLS_ctx.bulkSelectMode) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-shrink-0 h-5 w-5 rounded border-2 flex items-center justify-center mt-2 transition-all" },
        ...{ class: (__VLS_ctx.isChecked ? 'bg-[#FBA612] border-[#FBA612]' : 'border-muted-foreground/50') },
    });
    if (__VLS_ctx.isChecked) {
        const __VLS_0 = {}.Check;
        /** @type {[typeof __VLS_components.Check, ]} */ ;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
            ...{ class: "size-3 text-white" },
        }));
        const __VLS_2 = __VLS_1({
            ...{ class: "size-3 text-white" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    }
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-[13px] font-semibold text-white select-none mt-0.5" },
    ...{ style: {} },
});
(__VLS_ctx.initials);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col gap-1 min-w-0 flex-1" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-2" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "font-semibold truncate flex-1" },
});
(__VLS_ctx.recipientLabel ?? (__VLS_ctx.message.from_name || __VLS_ctx.message.from_address));
if (!__VLS_ctx.message.is_read) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span)({
        ...{ class: "flex-shrink-0 h-2 w-2 rounded-full bg-[#FBA612]" },
    });
}
if (__VLS_ctx.message.is_starred) {
    const __VLS_4 = {}.Star;
    /** @type {[typeof __VLS_components.Star, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        ...{ class: "flex-shrink-0 size-3 fill-yellow-400 text-yellow-400" },
    }));
    const __VLS_6 = __VLS_5({
        ...{ class: "flex-shrink-0 size-3 fill-yellow-400 text-yellow-400" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
}
if (__VLS_ctx.timestamp) {
    const __VLS_8 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        delayDuration: (300),
    }));
    const __VLS_10 = __VLS_9({
        delayDuration: (300),
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    __VLS_11.slots.default;
    const __VLS_12 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
        asChild: true,
    }));
    const __VLS_14 = __VLS_13({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    __VLS_15.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.cn('flex-shrink-0 text-xs cursor-default', __VLS_ctx.selected ? 'text-foreground' : 'text-muted-foreground')) },
    });
    (__VLS_ctx.relativeTime);
    var __VLS_15;
    const __VLS_16 = {}.TooltipPortal;
    /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({}));
    const __VLS_18 = __VLS_17({}, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    const __VLS_20 = {}.TooltipContent;
    /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md" },
    }));
    const __VLS_22 = __VLS_21({
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    __VLS_23.slots.default;
    (__VLS_ctx.exactTime);
    var __VLS_23;
    var __VLS_19;
    var __VLS_11;
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "text-xs font-medium truncate" },
});
(__VLS_ctx.message.subject);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "line-clamp-1 text-xs text-muted-foreground" },
});
(__VLS_ctx.message.text_body?.substring(0, 200) || 'No content');
if (__VLS_ctx.message.has_attachments) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center gap-1" },
    });
    /** @type {[typeof Badge, typeof Badge, ]} */ ;
    // @ts-ignore
    const __VLS_24 = __VLS_asFunctionalComponent(Badge, new Badge({
        variant: "secondary",
        ...{ class: "gap-1" },
    }));
    const __VLS_25 = __VLS_24({
        variant: "secondary",
        ...{ class: "gap-1" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_24));
    __VLS_26.slots.default;
    const __VLS_27 = {}.Paperclip;
    /** @type {[typeof __VLS_components.Paperclip, ]} */ ;
    // @ts-ignore
    const __VLS_28 = __VLS_asFunctionalComponent(__VLS_27, new __VLS_27({
        ...{ class: "size-3" },
    }));
    const __VLS_29 = __VLS_28({
        ...{ class: "size-3" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_28));
    var __VLS_26;
}
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-2']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['text-white']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[13px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-white']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-[#FBA612]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['fill-yellow-400']} */ ;
/** @type {__VLS_StyleScopedClasses['text-yellow-400']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['line-clamp-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Paperclip: Paperclip,
            Star: Star,
            Check: Check,
            TooltipRoot: TooltipRoot,
            TooltipTrigger: TooltipTrigger,
            TooltipContent: TooltipContent,
            TooltipPortal: TooltipPortal,
            cn: cn,
            Badge: Badge,
            initials: initials,
            timestamp: timestamp,
            relativeTime: relativeTime,
            exactTime: exactTime,
            recipientLabel: recipientLabel,
        };
    },
    props: {
        message: { type: Object, required: true },
        selected: { type: Boolean, default: false },
        folderColor: { type: String, default: '' },
        bulkSelectMode: { type: Boolean, default: false },
        isChecked: { type: Boolean, default: false },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        message: { type: Object, required: true },
        selected: { type: Boolean, default: false },
        folderColor: { type: String, default: '' },
        bulkSelectMode: { type: Boolean, default: false },
        isChecked: { type: Boolean, default: false },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MessageListItem.vue.js.map