/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, watch } from 'vue';
import { useMailStore } from '../../stores/mail';
const props = defineProps({
    modelValue: { type: String, default: '' }
});
const emit = defineEmits(['update:modelValue']);
const store = useMailStore();
const text = ref(props.modelValue);
watch(() => props.modelValue, (val) => {
    text.value = val;
    store.composeBody = val;
});
const onInput = (e) => {
    const val = e.target.value;
    text.value = val;
    store.composeBody = val;
    emit('update:modelValue', val);
};
const getHTML = () => text.value;
const __VLS_exposed = { getHTML };
defineExpose(__VLS_exposed);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col border rounded-md overflow-hidden" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.textarea)({
    ...{ onInput: (__VLS_ctx.onInput) },
    value: (__VLS_ctx.text),
    placeholder: "Write your message...",
    ...{ class: "flex-1 p-4 text-sm resize-none focus:outline-none min-h-[160px]" },
});
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['resize-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[160px]']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            text: text,
            onInput: onInput,
        };
    },
    emits: {},
    props: {
        modelValue: { type: String, default: '' }
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {
            ...__VLS_exposed,
        };
    },
    emits: {},
    props: {
        modelValue: { type: String, default: '' }
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=ComposeEditor.vue.js.map