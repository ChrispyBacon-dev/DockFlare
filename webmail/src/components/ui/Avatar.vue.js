/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
const props = defineProps({
    src: { type: String, default: '' },
    initials: { type: String, default: '' },
    class: { type: String, default: '' }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: (['relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-muted', props.class]) },
});
if (__VLS_ctx.src) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.img)({
        src: (__VLS_ctx.src),
        ...{ class: "aspect-square h-full w-full" },
    });
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "flex h-full w-full items-center justify-center rounded-full bg-muted text-muted-foreground" },
    });
    (__VLS_ctx.initials);
}
/** @type {__VLS_StyleScopedClasses['aspect-square']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        src: { type: String, default: '' },
        initials: { type: String, default: '' },
        class: { type: String, default: '' }
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        src: { type: String, default: '' },
        initials: { type: String, default: '' },
        class: { type: String, default: '' }
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Avatar.vue.js.map