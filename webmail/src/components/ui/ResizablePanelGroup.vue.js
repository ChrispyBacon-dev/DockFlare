/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, provide, reactive } from 'vue';
const groupEl = ref(null);
const sizes = reactive([]);
const panelCount = ref(0);
const handleCount = ref(0);
function registerPanel(defaultSize) {
    const idx = panelCount.value++;
    sizes[idx] = defaultSize;
    return idx;
}
function registerHandle() {
    return handleCount.value++;
}
function startResize(handleIdx, startX) {
    const onMove = (e) => {
        if (!groupEl.value)
            return;
        const dx = e.clientX - startX;
        startX = e.clientX;
        const totalW = groupEl.value.offsetWidth;
        const deltaPercent = (dx / totalW) * 100;
        const leftIdx = handleIdx;
        const rightIdx = handleIdx + 1;
        const newLeft = sizes[leftIdx] + deltaPercent;
        const newRight = sizes[rightIdx] - deltaPercent;
        if (newLeft >= 10 && newRight >= 10) {
            sizes[leftIdx] = newLeft;
            sizes[rightIdx] = newRight;
        }
    };
    const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
}
provide('resizableGroup', { sizes, registerPanel, registerHandle, startResize });
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ref: "groupEl",
    ...{ class: "flex h-full w-full overflow-hidden" },
});
/** @type {typeof __VLS_ctx.groupEl} */ ;
var __VLS_0 = {};
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
// @ts-ignore
var __VLS_1 = __VLS_0;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            groupEl: groupEl,
        };
    },
});
const __VLS_component = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
export default {};
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=ResizablePanelGroup.vue.js.map