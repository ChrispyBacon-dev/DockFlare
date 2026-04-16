/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { inject, computed } from 'vue';
const props = defineProps({
    defaultSize: { type: Number, default: 50 },
    minSize: { type: Number, default: 10 },
    class: { type: String, default: '' }
});
const group = inject('resizableGroup');
const idx = group ? group.registerPanel(props.defaultSize) : -1;
const sizeStyle = computed(() => {
    if (!group || idx === -1)
        return { flexBasis: `${props.defaultSize}%`, flexShrink: '0', flexGrow: '0' };
    return { flexBasis: `${group.sizes[idx]}%`, flexShrink: '0', flexGrow: '0' };
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ style: (__VLS_ctx.sizeStyle) },
    ...{ class: (['overflow-auto min-w-0', props.class]) },
});
var __VLS_0 = {};
// @ts-ignore
var __VLS_1 = __VLS_0;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            sizeStyle: sizeStyle,
        };
    },
    props: {
        defaultSize: { type: Number, default: 50 },
        minSize: { type: Number, default: 10 },
        class: { type: String, default: '' }
    },
});
const __VLS_component = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        defaultSize: { type: Number, default: 50 },
        minSize: { type: Number, default: 10 },
        class: { type: String, default: '' }
    },
});
export default {};
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=ResizablePanel.vue.js.map