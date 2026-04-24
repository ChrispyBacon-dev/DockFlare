/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { SplitterGroup, SplitterPanel, SplitterResizeHandle, TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal, } from 'radix-vue';
import { defineAsyncComponent, ref, watch, computed } from 'vue';
import { PenSquare, Sun, Moon, LogOut, Settings, Columns2, Maximize2, ChevronLeft, Menu } from 'lucide-vue-next';
import { cn } from '../../lib/utils';
import MailboxSelector from './MailboxSelector.vue';
import FolderNav from './FolderNav.vue';
import MessageList from './MessageList.vue';
import MessageDisplay from './MessageDisplay.vue';
import ComposeDialog from './ComposeDialog.vue';
import { useMailStore } from '../../stores/mail';
import { useAuth } from '../../composables/useAuth';
import { useBreakpoint } from '../../composables/useBreakpoint';
const SettingsDialog = defineAsyncComponent(() => import('./SettingsDialog.vue'));
const store = useMailStore();
const { logout } = useAuth();
const { isMobile } = useBreakpoint();
const onCollapse = () => { store.isCollapsed = true; };
const onExpand = () => { store.isCollapsed = false; };
const compose = () => {
    store.composeDefaults = null;
    store.isComposeOpen = true;
};
const mobilePanel = ref('list');
watch(() => store.currentFolder, () => {
    if (isMobile.value)
        mobilePanel.value = 'list';
});
watch(() => store.currentMessage, (msg) => {
    if (isMobile.value && msg)
        mobilePanel.value = 'detail';
});
const goBack = () => {
    if (mobilePanel.value === 'detail') {
        store.currentMessage = null;
        mobilePanel.value = 'list';
    }
    else if (mobilePanel.value === 'list') {
        mobilePanel.value = 'folders';
    }
};
const mobileTitle = computed(() => {
    if (mobilePanel.value === 'folders')
        return store.currentMailbox || 'Folders';
    if (mobilePanel.value === 'list')
        return store.currentFolder || 'Inbox';
    return store.currentMessage?.subject || 'Message';
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.TooltipProvider;
/** @type {[typeof __VLS_components.TooltipProvider, typeof __VLS_components.TooltipProvider, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    delayDuration: (0),
}));
const __VLS_2 = __VLS_1({
    delayDuration: (0),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
if (__VLS_ctx.isMobile) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex flex-col h-[100dvh] w-screen bg-background overflow-hidden" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "h-14 flex items-center gap-2 px-3 border-b border-border flex-shrink-0 bg-background" },
    });
    if (__VLS_ctx.mobilePanel !== 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.goBack) },
            ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0" },
        });
        const __VLS_5 = {}.ChevronLeft;
        /** @type {[typeof __VLS_components.ChevronLeft, ]} */ ;
        // @ts-ignore
        const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
            ...{ class: "size-5" },
        }));
        const __VLS_7 = __VLS_6({
            ...{ class: "size-5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.isMobile))
                        return;
                    if (!!(__VLS_ctx.mobilePanel !== 'folders'))
                        return;
                    __VLS_ctx.store.isSettingsOpen = true;
                } },
            ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0" },
        });
        const __VLS_9 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
            ...{ class: "size-4" },
        }));
        const __VLS_11 = __VLS_10({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_10));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "flex-1 text-base font-semibold truncate" },
    });
    (__VLS_ctx.mobileTitle);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.isMobile))
                    return;
                __VLS_ctx.store.toggleTheme();
            } },
        ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0" },
    });
    if (__VLS_ctx.store.isDark) {
        const __VLS_13 = {}.Sun;
        /** @type {[typeof __VLS_components.Sun, ]} */ ;
        // @ts-ignore
        const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
            ...{ class: "size-4" },
        }));
        const __VLS_15 = __VLS_14({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_14));
    }
    else {
        const __VLS_17 = {}.Moon;
        /** @type {[typeof __VLS_components.Moon, ]} */ ;
        // @ts-ignore
        const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
            ...{ class: "size-4" },
        }));
        const __VLS_19 = __VLS_18({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_18));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.logout) },
        ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors flex-shrink-0" },
    });
    const __VLS_21 = {}.LogOut;
    /** @type {[typeof __VLS_components.LogOut, ]} */ ;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        ...{ class: "size-4" },
    }));
    const __VLS_23 = __VLS_22({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-1 min-h-0 overflow-hidden" },
    });
    if (__VLS_ctx.mobilePanel === 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-full flex flex-col overflow-y-auto" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "px-3 py-3 border-b border-border" },
        });
        /** @type {[typeof MailboxSelector, ]} */ ;
        // @ts-ignore
        const __VLS_25 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
            isCollapsed: (false),
        }));
        const __VLS_26 = __VLS_25({
            isCollapsed: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_25));
        /** @type {[typeof FolderNav, ]} */ ;
        // @ts-ignore
        const __VLS_28 = __VLS_asFunctionalComponent(FolderNav, new FolderNav({
            isCollapsed: (false),
        }));
        const __VLS_29 = __VLS_28({
            isCollapsed: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_28));
    }
    else if (__VLS_ctx.mobilePanel === 'list') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-full flex flex-col overflow-hidden" },
        });
        /** @type {[typeof MessageList, ]} */ ;
        // @ts-ignore
        const __VLS_31 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
        const __VLS_32 = __VLS_31({}, ...__VLS_functionalComponentArgsRest(__VLS_31));
    }
    else if (__VLS_ctx.mobilePanel === 'detail') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-full flex flex-col overflow-hidden" },
        });
        /** @type {[typeof MessageDisplay, ]} */ ;
        // @ts-ignore
        const __VLS_34 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
            message: (__VLS_ctx.store.currentMessage ?? undefined),
        }));
        const __VLS_35 = __VLS_34({
            message: (__VLS_ctx.store.currentMessage ?? undefined),
        }, ...__VLS_functionalComponentArgsRest(__VLS_34));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "h-16 flex items-center justify-around border-t border-border flex-shrink-0 bg-background pb-safe" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.isMobile))
                    return;
                __VLS_ctx.mobilePanel = 'folders';
            } },
        ...{ class: "flex flex-col items-center gap-0.5 px-4 py-2 rounded-lg transition-colors" },
        ...{ class: (__VLS_ctx.mobilePanel === 'folders' ? 'text-primary' : 'text-muted-foreground hover:text-foreground') },
    });
    const __VLS_37 = {}.Menu;
    /** @type {[typeof __VLS_components.Menu, ]} */ ;
    // @ts-ignore
    const __VLS_38 = __VLS_asFunctionalComponent(__VLS_37, new __VLS_37({
        ...{ class: "size-5" },
    }));
    const __VLS_39 = __VLS_38({
        ...{ class: "size-5" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_38));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "text-[10px] font-medium" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.compose) },
        ...{ class: "flex items-center justify-center h-12 w-12 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors" },
    });
    const __VLS_41 = {}.PenSquare;
    /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
    // @ts-ignore
    const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
        ...{ class: "size-5" },
    }));
    const __VLS_43 = __VLS_42({
        ...{ class: "size-5" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.isMobile))
                    return;
                __VLS_ctx.mobilePanel = 'list';
            } },
        ...{ class: "flex flex-col items-center gap-0.5 px-4 py-2 rounded-lg transition-colors" },
        ...{ class: (__VLS_ctx.mobilePanel === 'list' ? 'text-primary' : 'text-muted-foreground hover:text-foreground') },
    });
    const __VLS_45 = {}.Columns2;
    /** @type {[typeof __VLS_components.Columns2, ]} */ ;
    // @ts-ignore
    const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
        ...{ class: "size-5" },
    }));
    const __VLS_47 = __VLS_46({
        ...{ class: "size-5" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_46));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "text-[10px] font-medium" },
    });
}
else {
    const __VLS_49 = {}.SplitterGroup;
    /** @type {[typeof __VLS_components.SplitterGroup, typeof __VLS_components.SplitterGroup, ]} */ ;
    // @ts-ignore
    const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({
        id: "mail-layout",
        direction: "horizontal",
        ...{ class: "h-screen w-screen items-stretch" },
    }));
    const __VLS_51 = __VLS_50({
        id: "mail-layout",
        direction: "horizontal",
        ...{ class: "h-screen w-screen items-stretch" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_50));
    __VLS_52.slots.default;
    const __VLS_53 = {}.SplitterPanel;
    /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
    // @ts-ignore
    const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
        ...{ 'onCollapse': {} },
        ...{ 'onExpand': {} },
        id: "sidebar",
        defaultSize: (20),
        collapsedSize: (4),
        collapsible: true,
        minSize: (15),
        maxSize: (22),
        ...{ class: (__VLS_ctx.cn('flex flex-col', __VLS_ctx.store.isCollapsed && 'min-w-[50px] transition-all duration-300 ease-in-out')) },
    }));
    const __VLS_55 = __VLS_54({
        ...{ 'onCollapse': {} },
        ...{ 'onExpand': {} },
        id: "sidebar",
        defaultSize: (20),
        collapsedSize: (4),
        collapsible: true,
        minSize: (15),
        maxSize: (22),
        ...{ class: (__VLS_ctx.cn('flex flex-col', __VLS_ctx.store.isCollapsed && 'min-w-[50px] transition-all duration-300 ease-in-out')) },
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    let __VLS_57;
    let __VLS_58;
    let __VLS_59;
    const __VLS_60 = {
        onCollapse: (__VLS_ctx.onCollapse)
    };
    const __VLS_61 = {
        onExpand: (__VLS_ctx.onExpand)
    };
    __VLS_56.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.cn('h-[52px] flex items-center gap-1 px-2 flex-shrink-0', __VLS_ctx.store.isCollapsed ? 'flex-col justify-center py-1' : 'flex-row')) },
    });
    if (!__VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex-1 min-w-0" },
        });
        /** @type {[typeof MailboxSelector, ]} */ ;
        // @ts-ignore
        const __VLS_62 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
            isCollapsed: (false),
        }));
        const __VLS_63 = __VLS_62({
            isCollapsed: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_62));
        const __VLS_65 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_66 = __VLS_asFunctionalComponent(__VLS_65, new __VLS_65({
            delayDuration: (0),
        }));
        const __VLS_67 = __VLS_66({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_66));
        __VLS_68.slots.default;
        const __VLS_69 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_70 = __VLS_asFunctionalComponent(__VLS_69, new __VLS_69({
            asChild: true,
        }));
        const __VLS_71 = __VLS_70({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_70));
        __VLS_72.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.compose) },
            ...{ class: "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex-shrink-0" },
        });
        const __VLS_73 = {}.PenSquare;
        /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
        // @ts-ignore
        const __VLS_74 = __VLS_asFunctionalComponent(__VLS_73, new __VLS_73({
            ...{ class: "size-4" },
        }));
        const __VLS_75 = __VLS_74({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_74));
        var __VLS_72;
        var __VLS_68;
        const __VLS_77 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_78 = __VLS_asFunctionalComponent(__VLS_77, new __VLS_77({
            delayDuration: (0),
        }));
        const __VLS_79 = __VLS_78({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_78));
        __VLS_80.slots.default;
        const __VLS_81 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_82 = __VLS_asFunctionalComponent(__VLS_81, new __VLS_81({
            asChild: true,
        }));
        const __VLS_83 = __VLS_82({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_82));
        __VLS_84.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.toggleViewMode();
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
        });
        if (__VLS_ctx.store.viewMode === 'full') {
            const __VLS_85 = {}.Columns2;
            /** @type {[typeof __VLS_components.Columns2, ]} */ ;
            // @ts-ignore
            const __VLS_86 = __VLS_asFunctionalComponent(__VLS_85, new __VLS_85({
                ...{ class: "size-4" },
            }));
            const __VLS_87 = __VLS_86({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_86));
        }
        else {
            const __VLS_89 = {}.Maximize2;
            /** @type {[typeof __VLS_components.Maximize2, ]} */ ;
            // @ts-ignore
            const __VLS_90 = __VLS_asFunctionalComponent(__VLS_89, new __VLS_89({
                ...{ class: "size-4" },
            }));
            const __VLS_91 = __VLS_90({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_90));
        }
        var __VLS_84;
        const __VLS_93 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_94 = __VLS_asFunctionalComponent(__VLS_93, new __VLS_93({}));
        const __VLS_95 = __VLS_94({}, ...__VLS_functionalComponentArgsRest(__VLS_94));
        __VLS_96.slots.default;
        const __VLS_97 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_98 = __VLS_asFunctionalComponent(__VLS_97, new __VLS_97({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_99 = __VLS_98({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_98));
        __VLS_100.slots.default;
        (__VLS_ctx.store.viewMode === 'full' ? 'Split view' : 'Full view');
        var __VLS_100;
        var __VLS_96;
        var __VLS_80;
        const __VLS_101 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_102 = __VLS_asFunctionalComponent(__VLS_101, new __VLS_101({
            delayDuration: (0),
        }));
        const __VLS_103 = __VLS_102({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_102));
        __VLS_104.slots.default;
        const __VLS_105 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_106 = __VLS_asFunctionalComponent(__VLS_105, new __VLS_105({
            asChild: true,
        }));
        const __VLS_107 = __VLS_106({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_106));
        __VLS_108.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.toggleTheme();
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
        });
        if (__VLS_ctx.store.isDark) {
            const __VLS_109 = {}.Sun;
            /** @type {[typeof __VLS_components.Sun, ]} */ ;
            // @ts-ignore
            const __VLS_110 = __VLS_asFunctionalComponent(__VLS_109, new __VLS_109({
                ...{ class: "size-4" },
            }));
            const __VLS_111 = __VLS_110({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_110));
        }
        else {
            const __VLS_113 = {}.Moon;
            /** @type {[typeof __VLS_components.Moon, ]} */ ;
            // @ts-ignore
            const __VLS_114 = __VLS_asFunctionalComponent(__VLS_113, new __VLS_113({
                ...{ class: "size-4" },
            }));
            const __VLS_115 = __VLS_114({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_114));
        }
        var __VLS_108;
        const __VLS_117 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_118 = __VLS_asFunctionalComponent(__VLS_117, new __VLS_117({}));
        const __VLS_119 = __VLS_118({}, ...__VLS_functionalComponentArgsRest(__VLS_118));
        __VLS_120.slots.default;
        const __VLS_121 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_122 = __VLS_asFunctionalComponent(__VLS_121, new __VLS_121({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_123 = __VLS_122({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_122));
        __VLS_124.slots.default;
        (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
        var __VLS_124;
        var __VLS_120;
        var __VLS_104;
        const __VLS_125 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_126 = __VLS_asFunctionalComponent(__VLS_125, new __VLS_125({
            delayDuration: (0),
        }));
        const __VLS_127 = __VLS_126({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_126));
        __VLS_128.slots.default;
        const __VLS_129 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_130 = __VLS_asFunctionalComponent(__VLS_129, new __VLS_129({
            asChild: true,
        }));
        const __VLS_131 = __VLS_130({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_130));
        __VLS_132.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.isSettingsOpen = true;
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
        });
        const __VLS_133 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
            ...{ class: "size-4" },
        }));
        const __VLS_135 = __VLS_134({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_134));
        var __VLS_132;
        const __VLS_137 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_138 = __VLS_asFunctionalComponent(__VLS_137, new __VLS_137({}));
        const __VLS_139 = __VLS_138({}, ...__VLS_functionalComponentArgsRest(__VLS_138));
        __VLS_140.slots.default;
        const __VLS_141 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_142 = __VLS_asFunctionalComponent(__VLS_141, new __VLS_141({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_143 = __VLS_142({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_142));
        __VLS_144.slots.default;
        var __VLS_144;
        var __VLS_140;
        var __VLS_128;
        const __VLS_145 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_146 = __VLS_asFunctionalComponent(__VLS_145, new __VLS_145({
            delayDuration: (0),
        }));
        const __VLS_147 = __VLS_146({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_146));
        __VLS_148.slots.default;
        const __VLS_149 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_150 = __VLS_asFunctionalComponent(__VLS_149, new __VLS_149({
            asChild: true,
        }));
        const __VLS_151 = __VLS_150({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_150));
        __VLS_152.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.logout) },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
        });
        const __VLS_153 = {}.LogOut;
        /** @type {[typeof __VLS_components.LogOut, ]} */ ;
        // @ts-ignore
        const __VLS_154 = __VLS_asFunctionalComponent(__VLS_153, new __VLS_153({
            ...{ class: "size-4" },
        }));
        const __VLS_155 = __VLS_154({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_154));
        var __VLS_152;
        const __VLS_157 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_158 = __VLS_asFunctionalComponent(__VLS_157, new __VLS_157({}));
        const __VLS_159 = __VLS_158({}, ...__VLS_functionalComponentArgsRest(__VLS_158));
        __VLS_160.slots.default;
        const __VLS_161 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_162 = __VLS_asFunctionalComponent(__VLS_161, new __VLS_161({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_163 = __VLS_162({
            side: "bottom",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_162));
        __VLS_164.slots.default;
        var __VLS_164;
        var __VLS_160;
        var __VLS_148;
    }
    else {
        const __VLS_165 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_166 = __VLS_asFunctionalComponent(__VLS_165, new __VLS_165({
            delayDuration: (0),
        }));
        const __VLS_167 = __VLS_166({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_166));
        __VLS_168.slots.default;
        const __VLS_169 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_170 = __VLS_asFunctionalComponent(__VLS_169, new __VLS_169({
            asChild: true,
        }));
        const __VLS_171 = __VLS_170({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_170));
        __VLS_172.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.compose) },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" },
        });
        const __VLS_173 = {}.PenSquare;
        /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
        // @ts-ignore
        const __VLS_174 = __VLS_asFunctionalComponent(__VLS_173, new __VLS_173({
            ...{ class: "size-4" },
        }));
        const __VLS_175 = __VLS_174({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_174));
        var __VLS_172;
        const __VLS_177 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_178 = __VLS_asFunctionalComponent(__VLS_177, new __VLS_177({}));
        const __VLS_179 = __VLS_178({}, ...__VLS_functionalComponentArgsRest(__VLS_178));
        __VLS_180.slots.default;
        const __VLS_181 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_182 = __VLS_asFunctionalComponent(__VLS_181, new __VLS_181({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_183 = __VLS_182({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_182));
        __VLS_184.slots.default;
        var __VLS_184;
        var __VLS_180;
        var __VLS_168;
        const __VLS_185 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_186 = __VLS_asFunctionalComponent(__VLS_185, new __VLS_185({
            delayDuration: (0),
        }));
        const __VLS_187 = __VLS_186({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_186));
        __VLS_188.slots.default;
        const __VLS_189 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_190 = __VLS_asFunctionalComponent(__VLS_189, new __VLS_189({
            asChild: true,
        }));
        const __VLS_191 = __VLS_190({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_190));
        __VLS_192.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.toggleTheme();
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
        });
        if (__VLS_ctx.store.isDark) {
            const __VLS_193 = {}.Sun;
            /** @type {[typeof __VLS_components.Sun, ]} */ ;
            // @ts-ignore
            const __VLS_194 = __VLS_asFunctionalComponent(__VLS_193, new __VLS_193({
                ...{ class: "size-4" },
            }));
            const __VLS_195 = __VLS_194({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_194));
        }
        else {
            const __VLS_197 = {}.Moon;
            /** @type {[typeof __VLS_components.Moon, ]} */ ;
            // @ts-ignore
            const __VLS_198 = __VLS_asFunctionalComponent(__VLS_197, new __VLS_197({
                ...{ class: "size-4" },
            }));
            const __VLS_199 = __VLS_198({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_198));
        }
        var __VLS_192;
        const __VLS_201 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_202 = __VLS_asFunctionalComponent(__VLS_201, new __VLS_201({}));
        const __VLS_203 = __VLS_202({}, ...__VLS_functionalComponentArgsRest(__VLS_202));
        __VLS_204.slots.default;
        const __VLS_205 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_206 = __VLS_asFunctionalComponent(__VLS_205, new __VLS_205({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_207 = __VLS_206({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_206));
        __VLS_208.slots.default;
        (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
        var __VLS_208;
        var __VLS_204;
        var __VLS_188;
        const __VLS_209 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_210 = __VLS_asFunctionalComponent(__VLS_209, new __VLS_209({
            delayDuration: (0),
        }));
        const __VLS_211 = __VLS_210({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_210));
        __VLS_212.slots.default;
        const __VLS_213 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_214 = __VLS_asFunctionalComponent(__VLS_213, new __VLS_213({
            asChild: true,
        }));
        const __VLS_215 = __VLS_214({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_214));
        __VLS_216.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.isSettingsOpen = true;
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
        });
        const __VLS_217 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_218 = __VLS_asFunctionalComponent(__VLS_217, new __VLS_217({
            ...{ class: "size-4" },
        }));
        const __VLS_219 = __VLS_218({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_218));
        var __VLS_216;
        const __VLS_221 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_222 = __VLS_asFunctionalComponent(__VLS_221, new __VLS_221({}));
        const __VLS_223 = __VLS_222({}, ...__VLS_functionalComponentArgsRest(__VLS_222));
        __VLS_224.slots.default;
        const __VLS_225 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_226 = __VLS_asFunctionalComponent(__VLS_225, new __VLS_225({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_227 = __VLS_226({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_226));
        __VLS_228.slots.default;
        var __VLS_228;
        var __VLS_224;
        var __VLS_212;
        const __VLS_229 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_230 = __VLS_asFunctionalComponent(__VLS_229, new __VLS_229({
            delayDuration: (0),
        }));
        const __VLS_231 = __VLS_230({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_230));
        __VLS_232.slots.default;
        const __VLS_233 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_234 = __VLS_asFunctionalComponent(__VLS_233, new __VLS_233({
            asChild: true,
        }));
        const __VLS_235 = __VLS_234({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_234));
        __VLS_236.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.logout) },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
        });
        const __VLS_237 = {}.LogOut;
        /** @type {[typeof __VLS_components.LogOut, ]} */ ;
        // @ts-ignore
        const __VLS_238 = __VLS_asFunctionalComponent(__VLS_237, new __VLS_237({
            ...{ class: "size-4" },
        }));
        const __VLS_239 = __VLS_238({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_238));
        var __VLS_236;
        const __VLS_241 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_242 = __VLS_asFunctionalComponent(__VLS_241, new __VLS_241({}));
        const __VLS_243 = __VLS_242({}, ...__VLS_functionalComponentArgsRest(__VLS_242));
        __VLS_244.slots.default;
        const __VLS_245 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_246 = __VLS_asFunctionalComponent(__VLS_245, new __VLS_245({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_247 = __VLS_246({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_246));
        __VLS_248.slots.default;
        var __VLS_248;
        var __VLS_244;
        var __VLS_232;
        /** @type {[typeof MailboxSelector, ]} */ ;
        // @ts-ignore
        const __VLS_249 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
            isCollapsed: (true),
        }));
        const __VLS_250 = __VLS_249({
            isCollapsed: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_249));
    }
    /** @type {[typeof FolderNav, ]} */ ;
    // @ts-ignore
    const __VLS_252 = __VLS_asFunctionalComponent(FolderNav, new FolderNav({
        isCollapsed: (__VLS_ctx.store.isCollapsed),
    }));
    const __VLS_253 = __VLS_252({
        isCollapsed: (__VLS_ctx.store.isCollapsed),
    }, ...__VLS_functionalComponentArgsRest(__VLS_252));
    var __VLS_56;
    const __VLS_255 = {}.SplitterResizeHandle;
    /** @type {[typeof __VLS_components.SplitterResizeHandle, ]} */ ;
    // @ts-ignore
    const __VLS_256 = __VLS_asFunctionalComponent(__VLS_255, new __VLS_255({
        id: "sidebar-handle",
        ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
    }));
    const __VLS_257 = __VLS_256({
        id: "sidebar-handle",
        ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_256));
    if (__VLS_ctx.store.viewMode === 'split') {
        const __VLS_259 = {}.SplitterPanel;
        /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
        // @ts-ignore
        const __VLS_260 = __VLS_asFunctionalComponent(__VLS_259, new __VLS_259({
            id: "mail-list",
            defaultSize: (35),
            minSize: (25),
            ...{ class: "flex flex-col overflow-hidden" },
        }));
        const __VLS_261 = __VLS_260({
            id: "mail-list",
            defaultSize: (35),
            minSize: (25),
            ...{ class: "flex flex-col overflow-hidden" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_260));
        __VLS_262.slots.default;
        /** @type {[typeof MessageList, ]} */ ;
        // @ts-ignore
        const __VLS_263 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
        const __VLS_264 = __VLS_263({}, ...__VLS_functionalComponentArgsRest(__VLS_263));
        var __VLS_262;
        const __VLS_266 = {}.SplitterResizeHandle;
        /** @type {[typeof __VLS_components.SplitterResizeHandle, ]} */ ;
        // @ts-ignore
        const __VLS_267 = __VLS_asFunctionalComponent(__VLS_266, new __VLS_266({
            id: "display-handle",
            ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
        }));
        const __VLS_268 = __VLS_267({
            id: "display-handle",
            ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_267));
        const __VLS_270 = {}.SplitterPanel;
        /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
        // @ts-ignore
        const __VLS_271 = __VLS_asFunctionalComponent(__VLS_270, new __VLS_270({
            id: "mail-display",
            defaultSize: (45),
            minSize: (30),
            ...{ class: "flex flex-col overflow-hidden" },
        }));
        const __VLS_272 = __VLS_271({
            id: "mail-display",
            defaultSize: (45),
            minSize: (30),
            ...{ class: "flex flex-col overflow-hidden" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_271));
        __VLS_273.slots.default;
        if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
            /** @type {[typeof ComposeDialog, ]} */ ;
            // @ts-ignore
            const __VLS_274 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
                panelMode: (true),
            }));
            const __VLS_275 = __VLS_274({
                panelMode: (true),
            }, ...__VLS_functionalComponentArgsRest(__VLS_274));
        }
        else {
            /** @type {[typeof MessageDisplay, ]} */ ;
            // @ts-ignore
            const __VLS_277 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
                message: (__VLS_ctx.store.currentMessage ?? undefined),
            }));
            const __VLS_278 = __VLS_277({
                message: (__VLS_ctx.store.currentMessage ?? undefined),
            }, ...__VLS_functionalComponentArgsRest(__VLS_277));
        }
        var __VLS_273;
    }
    else {
        const __VLS_280 = {}.SplitterPanel;
        /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
        // @ts-ignore
        const __VLS_281 = __VLS_asFunctionalComponent(__VLS_280, new __VLS_280({
            id: "mail-content",
            defaultSize: (80),
            minSize: (30),
            ...{ class: "flex flex-col overflow-hidden" },
        }));
        const __VLS_282 = __VLS_281({
            id: "mail-content",
            defaultSize: (80),
            minSize: (30),
            ...{ class: "flex flex-col overflow-hidden" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_281));
        __VLS_283.slots.default;
        if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
            /** @type {[typeof ComposeDialog, ]} */ ;
            // @ts-ignore
            const __VLS_284 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
                panelMode: (true),
            }));
            const __VLS_285 = __VLS_284({
                panelMode: (true),
            }, ...__VLS_functionalComponentArgsRest(__VLS_284));
        }
        else {
            if (!__VLS_ctx.store.currentMessage) {
                /** @type {[typeof MessageList, ]} */ ;
                // @ts-ignore
                const __VLS_287 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
                const __VLS_288 = __VLS_287({}, ...__VLS_functionalComponentArgsRest(__VLS_287));
            }
            else {
                /** @type {[typeof MessageDisplay, ]} */ ;
                // @ts-ignore
                const __VLS_290 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
                    message: (__VLS_ctx.store.currentMessage ?? undefined),
                }));
                const __VLS_291 = __VLS_290({
                    message: (__VLS_ctx.store.currentMessage ?? undefined),
                }, ...__VLS_functionalComponentArgsRest(__VLS_290));
            }
        }
        var __VLS_283;
    }
    var __VLS_52;
}
if (!__VLS_ctx.isMobile) {
    /** @type {[typeof ComposeDialog, ]} */ ;
    // @ts-ignore
    const __VLS_293 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({}));
    const __VLS_294 = __VLS_293({}, ...__VLS_functionalComponentArgsRest(__VLS_293));
}
else {
    const __VLS_296 = {}.Teleport;
    /** @type {[typeof __VLS_components.Teleport, typeof __VLS_components.Teleport, ]} */ ;
    // @ts-ignore
    const __VLS_297 = __VLS_asFunctionalComponent(__VLS_296, new __VLS_296({
        to: "body",
    }));
    const __VLS_298 = __VLS_297({
        to: "body",
    }, ...__VLS_functionalComponentArgsRest(__VLS_297));
    __VLS_299.slots.default;
    if (__VLS_ctx.store.isComposeOpen) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "fixed inset-0 z-50 flex flex-col bg-background" },
        });
        /** @type {[typeof ComposeDialog, ]} */ ;
        // @ts-ignore
        const __VLS_300 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
            panelMode: (true),
        }));
        const __VLS_301 = __VLS_300({
            panelMode: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_300));
    }
    var __VLS_299;
}
const __VLS_303 = {}.SettingsDialog;
/** @type {[typeof __VLS_components.SettingsDialog, ]} */ ;
// @ts-ignore
const __VLS_304 = __VLS_asFunctionalComponent(__VLS_303, new __VLS_303({}));
const __VLS_305 = __VLS_304({}, ...__VLS_functionalComponentArgsRest(__VLS_304));
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[100dvh]']} */ ;
/** @type {__VLS_StyleScopedClasses['w-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-14']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-base']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-0']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-3']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-16']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-around']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-safe']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['h-12']} */ ;
/** @type {__VLS_StyleScopedClasses['w-12']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['h-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['w-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['items-stretch']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['self-stretch']} */ ;
/** @type {__VLS_StyleScopedClasses['w-[3px]']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-primary/40']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['self-stretch']} */ ;
/** @type {__VLS_StyleScopedClasses['w-[3px]']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-primary/40']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            SplitterGroup: SplitterGroup,
            SplitterPanel: SplitterPanel,
            SplitterResizeHandle: SplitterResizeHandle,
            TooltipProvider: TooltipProvider,
            TooltipRoot: TooltipRoot,
            TooltipTrigger: TooltipTrigger,
            TooltipContent: TooltipContent,
            TooltipPortal: TooltipPortal,
            PenSquare: PenSquare,
            Sun: Sun,
            Moon: Moon,
            LogOut: LogOut,
            Settings: Settings,
            Columns2: Columns2,
            Maximize2: Maximize2,
            ChevronLeft: ChevronLeft,
            Menu: Menu,
            cn: cn,
            MailboxSelector: MailboxSelector,
            FolderNav: FolderNav,
            MessageList: MessageList,
            MessageDisplay: MessageDisplay,
            ComposeDialog: ComposeDialog,
            SettingsDialog: SettingsDialog,
            store: store,
            logout: logout,
            isMobile: isMobile,
            onCollapse: onCollapse,
            onExpand: onExpand,
            compose: compose,
            mobilePanel: mobilePanel,
            goBack: goBack,
            mobileTitle: mobileTitle,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MailLayout.vue.js.map