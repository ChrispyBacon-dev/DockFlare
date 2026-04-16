/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
const props = defineProps({
    orientation: { type: String, default: 'horizontal' },
    class: { type: String, default: '' }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
    ...{ class: (['shrink-0 bg-border', __VLS_ctx.orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]', props.class]) },
});
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        orientation: { type: String, default: 'horizontal' },
        class: { type: String, default: '' }
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        orientation: { type: String, default: 'horizontal' },
        class: { type: String, default: '' }
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Separator.vue.js.map