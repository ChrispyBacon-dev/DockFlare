/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
const props = defineProps({
    variant: { type: String, default: 'default' },
    size: { type: String, default: 'default' },
    class: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
    as: { type: String, default: 'button' }
});
const baseClass = "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";
const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    ghost: "hover:bg-accent hover:text-accent-foreground",
    link: "text-primary underline-offset-4 hover:underline",
};
const sizes = {
    default: "h-10 px-4 py-2",
    sm: "h-9 rounded-md px-3",
    lg: "h-11 rounded-md px-8",
    icon: "h-10 w-10",
};
const computedClass = computed(() => {
    return `${baseClass} ${variants[props.variant] || variants.default} ${sizes[props.size] || sizes.default} ${props.class}`;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = ((__VLS_ctx.as));
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: (__VLS_ctx.computedClass) },
    disabled: (__VLS_ctx.as === 'button' ? __VLS_ctx.disabled : undefined),
}));
const __VLS_2 = __VLS_1({
    ...{ class: (__VLS_ctx.computedClass) },
    disabled: (__VLS_ctx.as === 'button' ? __VLS_ctx.disabled : undefined),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
var __VLS_5 = {};
var __VLS_3;
// @ts-ignore
var __VLS_6 = __VLS_5;
[__VLS_dollars.$attrs,];
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            computedClass: computedClass,
        };
    },
    props: {
        variant: { type: String, default: 'default' },
        size: { type: String, default: 'default' },
        class: { type: String, default: '' },
        disabled: { type: Boolean, default: false },
        as: { type: String, default: 'button' }
    },
});
const __VLS_component = (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        variant: { type: String, default: 'default' },
        size: { type: String, default: 'default' },
        class: { type: String, default: '' },
        disabled: { type: Boolean, default: false },
        as: { type: String, default: 'button' }
    },
});
export default {};
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Button.vue.js.map