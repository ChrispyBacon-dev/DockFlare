/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { Bell, Palette, AtSign, Mail, Shield, Info, HelpCircle } from 'lucide-vue-next';
import { useMailStore } from '@/stores/mail';
const store = useMailStore();
const categories = [
    { key: 'notifications', label: 'Notifications', icon: Bell },
    { key: 'appearance', label: 'Appearance', icon: Palette },
    { key: 'aliases', label: 'Aliases', icon: AtSign },
    { key: 'autoresponder', label: 'Auto-Responder', icon: Mail },
    { key: 'security', label: 'Security', icon: Shield },
    { key: 'about', label: 'About', icon: Info },
    { key: 'help', label: 'Help', icon: HelpCircle },
];
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({
    ...{ class: "flex flex-col gap-0.5 p-3" },
});
for (const [cat] of __VLS_getVForSourceType((__VLS_ctx.categories))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.store.settingsCategory = cat.key;
            } },
        key: (cat.key),
        ...{ class: "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors text-left" },
        ...{ class: (__VLS_ctx.store.settingsCategory === cat.key
                ? 'bg-[#FBA612]/10 text-[#FBA612] font-medium'
                : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground') },
    });
    const __VLS_0 = ((cat.icon));
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        ...{ class: "size-4 shrink-0" },
    }));
    const __VLS_2 = __VLS_1({
        ...{ class: "size-4 shrink-0" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    (cat.label);
}
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['p-3']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['text-left']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            store: store,
            categories: categories,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=SettingsNav.vue.js.map