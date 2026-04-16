/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { inject } from 'vue';
const group = inject('resizableGroup');
const handleIdx = group ? group.registerHandle() : -1;
function onPointerDown(e) {
    if (!group || handleIdx === -1)
        return;
    e.preventDefault();
    e.target.setPointerCapture(e.pointerId);
    group.startResize(handleIdx, e.clientX);
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
    ...{ onPointerdown: (__VLS_ctx.onPointerDown) },
    ...{ class: "w-1 bg-border cursor-col-resize hover:bg-primary/50 active:bg-primary/70 transition-colors hidden md:flex items-center justify-center flex-shrink-0 select-none" },
});
/** @type {__VLS_StyleScopedClasses['w-1']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-col-resize']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/50']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-primary/70']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['md:flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            onPointerDown: onPointerDown,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=ResizableHandle.vue.js.map