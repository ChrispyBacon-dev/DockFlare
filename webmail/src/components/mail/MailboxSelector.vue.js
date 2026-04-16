/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { Mail, Check } from 'lucide-vue-next';
import { SelectRoot, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectItemText, SelectItemIndicator, SelectPortal, SelectViewport, } from 'radix-vue';
import { cn } from '../../lib/utils';
import { useMailStore } from '../../stores/mail';
const __VLS_props = defineProps({
    isCollapsed: { type: Boolean, default: false },
});
const store = useMailStore();
const selected = computed({
    get: () => store.currentMailbox,
    set: (val) => { store.currentMailbox = val; },
});
const currentDisplay = computed(() => {
    const mb = store.mailboxes.find((m) => m.address === store.currentMailbox);
    return mb?.display_name || store.currentMailbox;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex min-w-0" },
});
const __VLS_0 = {}.SelectRoot;
/** @type {[typeof __VLS_components.SelectRoot, typeof __VLS_components.SelectRoot, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    modelValue: (__VLS_ctx.selected),
}));
const __VLS_2 = __VLS_1({
    modelValue: (__VLS_ctx.selected),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
const __VLS_4 = {}.SelectTrigger;
/** @type {[typeof __VLS_components.SelectTrigger, typeof __VLS_components.SelectTrigger, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    ...{ class: (__VLS_ctx.cn('flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring [&>span]:line-clamp-1 [&>span]:flex [&>span]:w-full [&>span]:items-center [&>span]:gap-2 [&>span]:truncate', __VLS_ctx.isCollapsed ? 'h-9 w-9 shrink-0 justify-center p-0 [&>span]:w-auto' : 'w-full')) },
}));
const __VLS_6 = __VLS_5({
    ...{ class: (__VLS_ctx.cn('flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring [&>span]:line-clamp-1 [&>span]:flex [&>span]:w-full [&>span]:items-center [&>span]:gap-2 [&>span]:truncate', __VLS_ctx.isCollapsed ? 'h-9 w-9 shrink-0 justify-center p-0 [&>span]:w-auto' : 'w-full')) },
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
__VLS_7.slots.default;
const __VLS_8 = {}.SelectValue;
/** @type {[typeof __VLS_components.SelectValue, typeof __VLS_components.SelectValue, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    placeholder: (__VLS_ctx.isCollapsed ? '' : 'Select account'),
}));
const __VLS_10 = __VLS_9({
    placeholder: (__VLS_ctx.isCollapsed ? '' : 'Select account'),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-2" },
});
const __VLS_12 = {}.Mail;
/** @type {[typeof __VLS_components.Mail, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    ...{ class: "size-4 shrink-0" },
}));
const __VLS_14 = __VLS_13({
    ...{ class: "size-4 shrink-0" },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
if (!__VLS_ctx.isCollapsed) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "truncate" },
    });
    (__VLS_ctx.currentDisplay);
}
var __VLS_11;
var __VLS_7;
const __VLS_16 = {}.SelectPortal;
/** @type {[typeof __VLS_components.SelectPortal, typeof __VLS_components.SelectPortal, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({}));
const __VLS_18 = __VLS_17({}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_19.slots.default;
const __VLS_20 = {}.SelectContent;
/** @type {[typeof __VLS_components.SelectContent, typeof __VLS_components.SelectContent, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    ...{ class: "z-50 min-w-[220px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
    position: "popper",
    sideOffset: (4),
}));
const __VLS_22 = __VLS_21({
    ...{ class: "z-50 min-w-[220px] rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
    position: "popper",
    sideOffset: (4),
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
const __VLS_24 = {}.SelectViewport;
/** @type {[typeof __VLS_components.SelectViewport, typeof __VLS_components.SelectViewport, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({}));
const __VLS_26 = __VLS_25({}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
for (const [mb] of __VLS_getVForSourceType((__VLS_ctx.store.mailboxes))) {
    const __VLS_28 = {}.SelectItem;
    /** @type {[typeof __VLS_components.SelectItem, typeof __VLS_components.SelectItem, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
        key: (mb.address),
        value: (mb.address),
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent focus:bg-accent" },
    }));
    const __VLS_30 = __VLS_29({
        key: (mb.address),
        value: (mb.address),
        ...{ class: "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent focus:bg-accent" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
    __VLS_31.slots.default;
    const __VLS_32 = {}.SelectItemIndicator;
    /** @type {[typeof __VLS_components.SelectItemIndicator, typeof __VLS_components.SelectItemIndicator, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        ...{ class: "absolute left-2" },
    }));
    const __VLS_34 = __VLS_33({
        ...{ class: "absolute left-2" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    __VLS_35.slots.default;
    const __VLS_36 = {}.Check;
    /** @type {[typeof __VLS_components.Check, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        ...{ class: "size-4" },
    }));
    const __VLS_38 = __VLS_37({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    var __VLS_35;
    const __VLS_40 = {}.SelectItemText;
    /** @type {[typeof __VLS_components.SelectItemText, typeof __VLS_components.SelectItemText, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        ...{ class: "pl-6" },
    }));
    const __VLS_42 = __VLS_41({
        ...{ class: "pl-6" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center gap-2" },
    });
    const __VLS_44 = {}.Mail;
    /** @type {[typeof __VLS_components.Mail, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        ...{ class: "size-4 shrink-0 text-muted-foreground" },
    }));
    const __VLS_46 = __VLS_45({
        ...{ class: "size-4 shrink-0 text-muted-foreground" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    (mb.display_name || mb.address);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "text-xs text-muted-foreground" },
    });
    (mb.address);
    var __VLS_43;
    var __VLS_31;
}
var __VLS_27;
var __VLS_23;
var __VLS_19;
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-[220px]']} */ ;
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
/** @type {__VLS_StyleScopedClasses['focus:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['absolute']} */ ;
/** @type {__VLS_StyleScopedClasses['left-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['pl-6']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Mail: Mail,
            Check: Check,
            SelectRoot: SelectRoot,
            SelectTrigger: SelectTrigger,
            SelectValue: SelectValue,
            SelectContent: SelectContent,
            SelectItem: SelectItem,
            SelectItemText: SelectItemText,
            SelectItemIndicator: SelectItemIndicator,
            SelectPortal: SelectPortal,
            SelectViewport: SelectViewport,
            cn: cn,
            store: store,
            selected: selected,
            currentDisplay: currentDisplay,
        };
    },
    props: {
        isCollapsed: { type: Boolean, default: false },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        isCollapsed: { type: Boolean, default: false },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MailboxSelector.vue.js.map