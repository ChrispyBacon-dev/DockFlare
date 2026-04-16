/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
const props = defineProps({
    modelValue: { type: [String, Number], default: '' },
    class: { type: String, default: '' },
    type: { type: String, default: 'text' }
});
const emit = defineEmits(['update:modelValue']);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
    ...{ onInput: (...[$event]) => {
            __VLS_ctx.emit('update:modelValue', $event.target.value);
        } },
    type: (__VLS_ctx.type),
    value: (__VLS_ctx.modelValue),
    ...{ class: (['flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50', props.class]) },
});
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            emit: emit,
        };
    },
    emits: {},
    props: {
        modelValue: { type: [String, Number], default: '' },
        class: { type: String, default: '' },
        type: { type: String, default: 'text' }
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    emits: {},
    props: {
        modelValue: { type: [String, Number], default: '' },
        class: { type: String, default: '' },
        type: { type: String, default: 'text' }
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Input.vue.js.map