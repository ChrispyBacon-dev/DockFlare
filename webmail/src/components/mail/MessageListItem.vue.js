/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { formatDistanceToNow, format } from 'date-fns';
import { Paperclip, Star } from 'lucide-vue-next';
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue';
import { cn } from '../../lib/utils';
import Badge from '../ui/Badge.vue';
const props = defineProps({
    message: { type: Object, required: true },
    selected: { type: Boolean, default: false },
    folderColor: { type: String, default: '' },
});
const timestamp = computed(() => props.message.received_at || props.message.sent_at);
const relativeTime = computed(() => timestamp.value ? formatDistanceToNow(new Date(timestamp.value), { addSuffix: true }) : '');
const exactTime = computed(() => timestamp.value ? format(new Date(timestamp.value), 'PPpp') : '');
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ class: (__VLS_ctx.cn('flex flex-col items-start gap-2 rounded-lg border p-3 text-left text-sm transition-all hover:bg-accent w-full', __VLS_ctx.selected && 'bg-muted')) },
    ...{ style: (__VLS_ctx.folderColor ? `border-left: 3px solid ${__VLS_ctx.folderColor}` : '') },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex w-full flex-col gap-1" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-2" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "font-semibold" },
});
(__VLS_ctx.message.from_name || __VLS_ctx.message.from_address);
if (!__VLS_ctx.message.is_read) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span)({
        ...{ class: "flex h-2 w-2 rounded-full bg-primary" },
    });
}
if (__VLS_ctx.message.is_starred) {
    const __VLS_0 = {}.Star;
    /** @type {[typeof __VLS_components.Star, ]} */ ;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        ...{ class: "size-3 fill-yellow-400 text-yellow-400" },
    }));
    const __VLS_2 = __VLS_1({
        ...{ class: "size-3 fill-yellow-400 text-yellow-400" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
if (__VLS_ctx.timestamp) {
    const __VLS_4 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        delayDuration: (300),
    }));
    const __VLS_6 = __VLS_5({
        delayDuration: (300),
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
    __VLS_7.slots.default;
    const __VLS_8 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        asChild: true,
    }));
    const __VLS_10 = __VLS_9({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    __VLS_11.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.cn('ml-auto text-xs cursor-default', __VLS_ctx.selected ? 'text-foreground' : 'text-muted-foreground')) },
    });
    (__VLS_ctx.relativeTime);
    var __VLS_11;
    const __VLS_12 = {}.TooltipPortal;
    /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({}));
    const __VLS_14 = __VLS_13({}, ...__VLS_functionalComponentArgsRest(__VLS_13));
    __VLS_15.slots.default;
    const __VLS_16 = {}.TooltipContent;
    /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md" },
    }));
    const __VLS_18 = __VLS_17({
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    (__VLS_ctx.exactTime);
    var __VLS_19;
    var __VLS_15;
    var __VLS_7;
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "text-xs font-medium" },
});
(__VLS_ctx.message.subject);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "line-clamp-2 text-xs text-muted-foreground" },
});
(__VLS_ctx.message.text_body?.substring(0, 300) || 'No content');
if (__VLS_ctx.message.has_attachments) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center gap-1" },
    });
    /** @type {[typeof Badge, typeof Badge, ]} */ ;
    // @ts-ignore
    const __VLS_20 = __VLS_asFunctionalComponent(Badge, new Badge({
        variant: "secondary",
        ...{ class: "gap-1" },
    }));
    const __VLS_21 = __VLS_20({
        variant: "secondary",
        ...{ class: "gap-1" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_20));
    __VLS_22.slots.default;
    const __VLS_23 = {}.Paperclip;
    /** @type {[typeof __VLS_components.Paperclip, ]} */ ;
    // @ts-ignore
    const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({
        ...{ class: "size-3" },
    }));
    const __VLS_25 = __VLS_24({
        ...{ class: "size-3" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_24));
    var __VLS_22;
}
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
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
/** @type {__VLS_StyleScopedClasses['line-clamp-2']} */ ;
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
            TooltipRoot: TooltipRoot,
            TooltipTrigger: TooltipTrigger,
            TooltipContent: TooltipContent,
            TooltipPortal: TooltipPortal,
            cn: cn,
            Badge: Badge,
            timestamp: timestamp,
            relativeTime: relativeTime,
            exactTime: exactTime,
        };
    },
    props: {
        message: { type: Object, required: true },
        selected: { type: Boolean, default: false },
        folderColor: { type: String, default: '' },
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
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MessageListItem.vue.js.map