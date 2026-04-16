/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
const props = defineProps({
    variant: { type: String, default: 'default' },
    class: { type: String, default: '' }
});
const variants = {
    default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
    secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
    outline: "text-foreground",
};
const computedClass = computed(() => {
    return `inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${variants[props.variant] || variants.default} ${props.class}`;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: (__VLS_ctx.computedClass) },
});
var __VLS_0 = {};
// @ts-ignore
var __VLS_1 = __VLS_0;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            computedClass: computedClass,
        };
    },
    props: {
        variant: { type: String, default: 'default' },
        class: { type: String, default: '' }
    },
});
const __VLS_component = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        variant: { type: String, default: 'default' },
        class: { type: String, default: '' }
    },
});
export default {};
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Badge.vue.js.map