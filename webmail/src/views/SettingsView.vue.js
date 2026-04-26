/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import SettingsNav from '@/components/settings/SettingsNav.vue';
import SettingsPanel from '@/components/settings/SettingsPanel.vue';
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex h-full" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "w-48 border-r border-border overflow-y-auto" },
});
/** @type {[typeof SettingsNav, ]} */ ;
// @ts-ignore
const __VLS_0 = __VLS_asFunctionalComponent(SettingsNav, new SettingsNav({}));
const __VLS_1 = __VLS_0({}, ...__VLS_functionalComponentArgsRest(__VLS_0));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex-1 overflow-hidden" },
});
/** @type {[typeof SettingsPanel, ]} */ ;
// @ts-ignore
const __VLS_3 = __VLS_asFunctionalComponent(SettingsPanel, new SettingsPanel({
    hideHeader: (true),
}));
const __VLS_4 = __VLS_3({
    hideHeader: (true),
}, ...__VLS_functionalComponentArgsRest(__VLS_3));
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['w-48']} */ ;
/** @type {__VLS_StyleScopedClasses['border-r']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            SettingsNav: SettingsNav,
            SettingsPanel: SettingsPanel,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=SettingsView.vue.js.map