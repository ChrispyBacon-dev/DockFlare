/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { cn } from '../../lib/utils';
const props = defineProps({
    modelValue: { type: [String, Number], default: '' },
    class: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.textarea)({
    ...{ onInput: (...[$event]) => {
            __VLS_ctx.emit('update:modelValue', $event.target.value);
        } },
    value: (__VLS_ctx.modelValue),
    ...{ class: (__VLS_ctx.cn('flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50', props.class)) },
});
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            cn: cn,
            emit: emit,
        };
    },
    emits: {},
    props: {
        modelValue: { type: [String, Number], default: '' },
        class: { type: String, default: '' },
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
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Textarea.vue.js.map