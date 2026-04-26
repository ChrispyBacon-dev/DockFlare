/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { SplitterGroup, SplitterPanel, SplitterResizeHandle, TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal, } from 'radix-vue';
import { ref, watch, computed } from 'vue';
import { PenSquare, Sun, Moon, LogOut, Settings, Columns2, ChevronLeft, Menu, PanelLeftClose, PanelLeftOpen, ArrowLeft } from 'lucide-vue-next';
import MailboxSelector from './MailboxSelector.vue';
import FolderNav from './FolderNav.vue';
import MessageList from './MessageList.vue';
import MessageDisplay from './MessageDisplay.vue';
import ComposeDialog from './ComposeDialog.vue';
import SettingsNav from '../settings/SettingsNav.vue';
import SettingsPanel from '../settings/SettingsPanel.vue';
import { useMailStore } from '../../stores/mail';
import { useAuth } from '../../composables/useAuth';
import { useBreakpoint } from '../../composables/useBreakpoint';
const store = useMailStore();
const { logout } = useAuth();
const { isMobile } = useBreakpoint();
const compose = () => {
    store.composeDefaults = null;
    store.isComposeOpen = true;
};
const mobilePanel = ref('list');
watch(() => store.currentFolder, () => {
    store.isSettingsOpen = false;
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
/** @type {__VLS_StyleScopedClasses['df-compose-btn']} */ ;
// CSS variable injection 
// CSS variable injection end 
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
        ...{ class: "flex flex-col h-[100dvh] w-screen overflow-hidden" },
        ...{ style: {} },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-end gap-2 px-3 pb-2 border-b border-border flex-shrink-0 pt-safe" },
        ...{ style: {} },
    });
    if (__VLS_ctx.mobilePanel !== 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.goBack) },
            ...{ class: "inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0" },
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
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-['Outfit'] font-extrabold text-[19px] tracking-[-0.01em] leading-none select-none h-10 flex items-center px-1" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[#194466] dark:text-[#5EB1E5]" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[#FBA612]" },
        });
    }
    if (__VLS_ctx.mobilePanel !== 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "flex-1 text-[15px] font-semibold truncate pb-0.5" },
        });
        (__VLS_ctx.mobileTitle);
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "flex-1" },
        });
    }
    if (__VLS_ctx.mobilePanel === 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.isMobile))
                        return;
                    if (!(__VLS_ctx.mobilePanel === 'folders'))
                        return;
                    __VLS_ctx.store.toggleTheme();
                } },
            ...{ class: "inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0" },
        });
        if (__VLS_ctx.store.isDark) {
            const __VLS_9 = {}.Sun;
            /** @type {[typeof __VLS_components.Sun, ]} */ ;
            // @ts-ignore
            const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
                ...{ class: "size-4" },
            }));
            const __VLS_11 = __VLS_10({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_10));
        }
        else {
            const __VLS_13 = {}.Moon;
            /** @type {[typeof __VLS_components.Moon, ]} */ ;
            // @ts-ignore
            const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
                ...{ class: "size-4" },
            }));
            const __VLS_15 = __VLS_14({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_14));
        }
    }
    if (__VLS_ctx.mobilePanel === 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.isMobile))
                        return;
                    if (!(__VLS_ctx.mobilePanel === 'folders'))
                        return;
                    __VLS_ctx.store.isSettingsOpen = true;
                } },
            ...{ class: "inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0" },
        });
        const __VLS_17 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
            ...{ class: "size-4" },
        }));
        const __VLS_19 = __VLS_18({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_18));
    }
    if (__VLS_ctx.mobilePanel === 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.logout) },
            ...{ class: "inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors flex-shrink-0" },
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
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-1 min-h-0 overflow-hidden" },
    });
    if (__VLS_ctx.mobilePanel === 'folders') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-full flex flex-col overflow-y-auto" },
        });
        if (__VLS_ctx.store.mailboxes.length > 1) {
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
        }
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
        const __VLS_31 = __VLS_asFunctionalComponent(MessageList, new MessageList({
            hideTitle: (true),
        }));
        const __VLS_32 = __VLS_31({
            hideTitle: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_31));
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
        ...{ class: "flex items-center justify-around border-t border-border flex-shrink-0 pb-safe" },
        ...{ style: {} },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.isMobile))
                    return;
                __VLS_ctx.mobilePanel = 'folders';
            } },
        ...{ class: "flex flex-col items-center gap-1 px-6 py-2 rounded-xl transition-colors min-h-[44px] justify-center" },
        ...{ class: (__VLS_ctx.mobilePanel === 'folders' ? '' : 'text-muted-foreground') },
        ...{ style: (__VLS_ctx.mobilePanel === 'folders' ? 'color: #FBA612;' : '') },
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
        ...{ class: "flex items-center justify-center h-12 w-12 rounded-full shadow-lg transition-colors flex-shrink-0" },
        ...{ style: {} },
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
        ...{ class: "flex flex-col items-center gap-1 px-6 py-2 rounded-xl transition-colors min-h-[44px] justify-center" },
        ...{ class: (__VLS_ctx.mobilePanel === 'list' ? '' : 'text-muted-foreground') },
        ...{ style: (__VLS_ctx.mobilePanel === 'list' ? 'color: #FBA612;' : '') },
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
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "h-screen w-screen overflow-hidden flex flex-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "df-sidebar flex flex-col flex-shrink-0 relative overflow-hidden" },
        ...{ style: ({
                width: __VLS_ctx.store.isCollapsed ? '52px' : '220px',
                background: 'var(--df-sidebar-bg)',
                backdropFilter: 'var(--df-sidebar-blur)',
                boxShadow: '2px 0 12px rgba(0,0,0,0.04)',
            }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "h-[54px] flex items-center justify-center px-[14px] flex-shrink-0" },
    });
    if (!__VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.img)({
            src: "/logo.gif",
            alt: "DockFlare",
            ...{ class: "h-7 w-auto select-none" },
            draggable: "false",
        });
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-['Outfit'] font-extrabold text-[15px] leading-none select-none mx-auto" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[#194466] dark:text-[#5EB1E5]" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[#FBA612]" },
        });
    }
    if (__VLS_ctx.store.mailboxes.length > 1 && !__VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "px-3 pb-2 flex-shrink-0" },
        });
        /** @type {[typeof MailboxSelector, ]} */ ;
        // @ts-ignore
        const __VLS_49 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
            isCollapsed: (false),
        }));
        const __VLS_50 = __VLS_49({
            isCollapsed: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    }
    else if (__VLS_ctx.store.mailboxes.length > 1 && __VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex justify-center pb-2 flex-shrink-0" },
        });
        /** @type {[typeof MailboxSelector, ]} */ ;
        // @ts-ignore
        const __VLS_52 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
            isCollapsed: (true),
        }));
        const __VLS_53 = __VLS_52({
            isCollapsed: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_52));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "px-3 pb-3 flex-shrink-0" },
    });
    if (!__VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.compose) },
            ...{ class: "df-compose-btn w-full flex items-center justify-center gap-2 rounded-xl py-2 text-sm font-semibold transition-all" },
        });
        const __VLS_55 = {}.PenSquare;
        /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
        // @ts-ignore
        const __VLS_56 = __VLS_asFunctionalComponent(__VLS_55, new __VLS_55({
            ...{ class: "size-4" },
        }));
        const __VLS_57 = __VLS_56({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_56));
    }
    else {
        const __VLS_59 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_60 = __VLS_asFunctionalComponent(__VLS_59, new __VLS_59({
            delayDuration: (0),
        }));
        const __VLS_61 = __VLS_60({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_60));
        __VLS_62.slots.default;
        const __VLS_63 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
            asChild: true,
        }));
        const __VLS_65 = __VLS_64({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_64));
        __VLS_66.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.compose) },
            ...{ class: "df-compose-btn inline-flex h-[34px] w-[34px] items-center justify-center rounded-full transition-all mx-auto" },
        });
        const __VLS_67 = {}.PenSquare;
        /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
        // @ts-ignore
        const __VLS_68 = __VLS_asFunctionalComponent(__VLS_67, new __VLS_67({
            ...{ class: "size-4" },
        }));
        const __VLS_69 = __VLS_68({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_68));
        var __VLS_66;
        const __VLS_71 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_72 = __VLS_asFunctionalComponent(__VLS_71, new __VLS_71({}));
        const __VLS_73 = __VLS_72({}, ...__VLS_functionalComponentArgsRest(__VLS_72));
        __VLS_74.slots.default;
        const __VLS_75 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_77 = __VLS_76({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_76));
        __VLS_78.slots.default;
        var __VLS_78;
        var __VLS_74;
        var __VLS_62;
    }
    /** @type {[typeof FolderNav, ]} */ ;
    // @ts-ignore
    const __VLS_79 = __VLS_asFunctionalComponent(FolderNav, new FolderNav({
        isCollapsed: (__VLS_ctx.store.isCollapsed),
    }));
    const __VLS_80 = __VLS_79({
        isCollapsed: (__VLS_ctx.store.isCollapsed),
    }, ...__VLS_functionalComponentArgsRest(__VLS_79));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.store.isCollapsed
                ? 'flex flex-col items-center gap-1 px-2 py-3 flex-shrink-0'
                : 'px-3 py-3 flex-shrink-0 space-y-0.5') },
    });
    if (!__VLS_ctx.store.isCollapsed) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.isCollapsed = true;
                } },
            ...{ class: "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors" },
        });
        const __VLS_82 = {}.PanelLeftClose;
        /** @type {[typeof __VLS_components.PanelLeftClose, ]} */ ;
        // @ts-ignore
        const __VLS_83 = __VLS_asFunctionalComponent(__VLS_82, new __VLS_82({
            ...{ class: "size-4" },
        }));
        const __VLS_84 = __VLS_83({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_83));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.toggleTheme();
                } },
            ...{ class: "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors" },
        });
        if (__VLS_ctx.store.isDark) {
            const __VLS_86 = {}.Sun;
            /** @type {[typeof __VLS_components.Sun, ]} */ ;
            // @ts-ignore
            const __VLS_87 = __VLS_asFunctionalComponent(__VLS_86, new __VLS_86({
                ...{ class: "size-4" },
            }));
            const __VLS_88 = __VLS_87({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_87));
        }
        else {
            const __VLS_90 = {}.Moon;
            /** @type {[typeof __VLS_components.Moon, ]} */ ;
            // @ts-ignore
            const __VLS_91 = __VLS_asFunctionalComponent(__VLS_90, new __VLS_90({
                ...{ class: "size-4" },
            }));
            const __VLS_92 = __VLS_91({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_91));
        }
        (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.isSettingsOpen = true;
                } },
            ...{ class: "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors" },
        });
        const __VLS_94 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_95 = __VLS_asFunctionalComponent(__VLS_94, new __VLS_94({
            ...{ class: "size-4" },
        }));
        const __VLS_96 = __VLS_95({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_95));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.logout) },
            ...{ class: "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors" },
        });
        const __VLS_98 = {}.LogOut;
        /** @type {[typeof __VLS_components.LogOut, ]} */ ;
        // @ts-ignore
        const __VLS_99 = __VLS_asFunctionalComponent(__VLS_98, new __VLS_98({
            ...{ class: "size-4" },
        }));
        const __VLS_100 = __VLS_99({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_99));
    }
    else {
        const __VLS_102 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_103 = __VLS_asFunctionalComponent(__VLS_102, new __VLS_102({
            delayDuration: (0),
        }));
        const __VLS_104 = __VLS_103({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_103));
        __VLS_105.slots.default;
        const __VLS_106 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_107 = __VLS_asFunctionalComponent(__VLS_106, new __VLS_106({
            asChild: true,
        }));
        const __VLS_108 = __VLS_107({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_107));
        __VLS_109.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isMobile))
                        return;
                    if (!!(!__VLS_ctx.store.isCollapsed))
                        return;
                    __VLS_ctx.store.isCollapsed = false;
                } },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
        });
        const __VLS_110 = {}.PanelLeftOpen;
        /** @type {[typeof __VLS_components.PanelLeftOpen, ]} */ ;
        // @ts-ignore
        const __VLS_111 = __VLS_asFunctionalComponent(__VLS_110, new __VLS_110({
            ...{ class: "size-4" },
        }));
        const __VLS_112 = __VLS_111({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_111));
        var __VLS_109;
        const __VLS_114 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_115 = __VLS_asFunctionalComponent(__VLS_114, new __VLS_114({}));
        const __VLS_116 = __VLS_115({}, ...__VLS_functionalComponentArgsRest(__VLS_115));
        __VLS_117.slots.default;
        const __VLS_118 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_119 = __VLS_asFunctionalComponent(__VLS_118, new __VLS_118({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_120 = __VLS_119({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_119));
        __VLS_121.slots.default;
        var __VLS_121;
        var __VLS_117;
        var __VLS_105;
        const __VLS_122 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_123 = __VLS_asFunctionalComponent(__VLS_122, new __VLS_122({
            delayDuration: (0),
        }));
        const __VLS_124 = __VLS_123({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_123));
        __VLS_125.slots.default;
        const __VLS_126 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_127 = __VLS_asFunctionalComponent(__VLS_126, new __VLS_126({
            asChild: true,
        }));
        const __VLS_128 = __VLS_127({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_127));
        __VLS_129.slots.default;
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
            const __VLS_130 = {}.Sun;
            /** @type {[typeof __VLS_components.Sun, ]} */ ;
            // @ts-ignore
            const __VLS_131 = __VLS_asFunctionalComponent(__VLS_130, new __VLS_130({
                ...{ class: "size-4" },
            }));
            const __VLS_132 = __VLS_131({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_131));
        }
        else {
            const __VLS_134 = {}.Moon;
            /** @type {[typeof __VLS_components.Moon, ]} */ ;
            // @ts-ignore
            const __VLS_135 = __VLS_asFunctionalComponent(__VLS_134, new __VLS_134({
                ...{ class: "size-4" },
            }));
            const __VLS_136 = __VLS_135({
                ...{ class: "size-4" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_135));
        }
        var __VLS_129;
        const __VLS_138 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_139 = __VLS_asFunctionalComponent(__VLS_138, new __VLS_138({}));
        const __VLS_140 = __VLS_139({}, ...__VLS_functionalComponentArgsRest(__VLS_139));
        __VLS_141.slots.default;
        const __VLS_142 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_143 = __VLS_asFunctionalComponent(__VLS_142, new __VLS_142({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_144 = __VLS_143({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_143));
        __VLS_145.slots.default;
        (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
        var __VLS_145;
        var __VLS_141;
        var __VLS_125;
        const __VLS_146 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_147 = __VLS_asFunctionalComponent(__VLS_146, new __VLS_146({
            delayDuration: (0),
        }));
        const __VLS_148 = __VLS_147({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_147));
        __VLS_149.slots.default;
        const __VLS_150 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_151 = __VLS_asFunctionalComponent(__VLS_150, new __VLS_150({
            asChild: true,
        }));
        const __VLS_152 = __VLS_151({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_151));
        __VLS_153.slots.default;
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
        const __VLS_154 = {}.Settings;
        /** @type {[typeof __VLS_components.Settings, ]} */ ;
        // @ts-ignore
        const __VLS_155 = __VLS_asFunctionalComponent(__VLS_154, new __VLS_154({
            ...{ class: "size-4" },
        }));
        const __VLS_156 = __VLS_155({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_155));
        var __VLS_153;
        const __VLS_158 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_159 = __VLS_asFunctionalComponent(__VLS_158, new __VLS_158({}));
        const __VLS_160 = __VLS_159({}, ...__VLS_functionalComponentArgsRest(__VLS_159));
        __VLS_161.slots.default;
        const __VLS_162 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_163 = __VLS_asFunctionalComponent(__VLS_162, new __VLS_162({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_164 = __VLS_163({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_163));
        __VLS_165.slots.default;
        var __VLS_165;
        var __VLS_161;
        var __VLS_149;
        const __VLS_166 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_167 = __VLS_asFunctionalComponent(__VLS_166, new __VLS_166({
            delayDuration: (0),
        }));
        const __VLS_168 = __VLS_167({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_167));
        __VLS_169.slots.default;
        const __VLS_170 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_171 = __VLS_asFunctionalComponent(__VLS_170, new __VLS_170({
            asChild: true,
        }));
        const __VLS_172 = __VLS_171({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_171));
        __VLS_173.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.logout) },
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
        });
        const __VLS_174 = {}.LogOut;
        /** @type {[typeof __VLS_components.LogOut, ]} */ ;
        // @ts-ignore
        const __VLS_175 = __VLS_asFunctionalComponent(__VLS_174, new __VLS_174({
            ...{ class: "size-4" },
        }));
        const __VLS_176 = __VLS_175({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_175));
        var __VLS_173;
        const __VLS_178 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_179 = __VLS_asFunctionalComponent(__VLS_178, new __VLS_178({}));
        const __VLS_180 = __VLS_179({}, ...__VLS_functionalComponentArgsRest(__VLS_179));
        __VLS_181.slots.default;
        const __VLS_182 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_183 = __VLS_asFunctionalComponent(__VLS_182, new __VLS_182({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }));
        const __VLS_184 = __VLS_183({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_183));
        __VLS_185.slots.default;
        var __VLS_185;
        var __VLS_181;
        var __VLS_169;
    }
    if (__VLS_ctx.store.isSettingsOpen) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex-none h-full overflow-y-auto border-r border-border" },
            ...{ style: {} },
        });
        /** @type {[typeof SettingsNav, ]} */ ;
        // @ts-ignore
        const __VLS_186 = __VLS_asFunctionalComponent(SettingsNav, new SettingsNav({}));
        const __VLS_187 = __VLS_186({}, ...__VLS_functionalComponentArgsRest(__VLS_186));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex-1 h-full overflow-hidden" },
            ...{ style: {} },
        });
        /** @type {[typeof SettingsPanel, ]} */ ;
        // @ts-ignore
        const __VLS_189 = __VLS_asFunctionalComponent(SettingsPanel, new SettingsPanel({}));
        const __VLS_190 = __VLS_189({}, ...__VLS_functionalComponentArgsRest(__VLS_189));
    }
    else {
        const __VLS_192 = {}.SplitterGroup;
        /** @type {[typeof __VLS_components.SplitterGroup, typeof __VLS_components.SplitterGroup, ]} */ ;
        // @ts-ignore
        const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
            id: "mail-layout",
            direction: "horizontal",
            ...{ class: "flex-1 h-full items-stretch" },
        }));
        const __VLS_194 = __VLS_193({
            id: "mail-layout",
            direction: "horizontal",
            ...{ class: "flex-1 h-full items-stretch" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_193));
        __VLS_195.slots.default;
        if (__VLS_ctx.store.viewMode === 'split') {
            const __VLS_196 = {}.SplitterPanel;
            /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
            // @ts-ignore
            const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
                id: "mail-list",
                defaultSize: (35),
                minSize: (25),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }));
            const __VLS_198 = __VLS_197({
                id: "mail-list",
                defaultSize: (35),
                minSize: (25),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_197));
            __VLS_199.slots.default;
            /** @type {[typeof MessageList, ]} */ ;
            // @ts-ignore
            const __VLS_200 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
            const __VLS_201 = __VLS_200({}, ...__VLS_functionalComponentArgsRest(__VLS_200));
            var __VLS_199;
            const __VLS_203 = {}.SplitterResizeHandle;
            /** @type {[typeof __VLS_components.SplitterResizeHandle, ]} */ ;
            // @ts-ignore
            const __VLS_204 = __VLS_asFunctionalComponent(__VLS_203, new __VLS_203({
                id: "display-handle",
                ...{ class: "self-stretch w-px bg-transparent hover:bg-border/30 active:bg-border/60 transition-colors" },
            }));
            const __VLS_205 = __VLS_204({
                id: "display-handle",
                ...{ class: "self-stretch w-px bg-transparent hover:bg-border/30 active:bg-border/60 transition-colors" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_204));
            const __VLS_207 = {}.SplitterPanel;
            /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
            // @ts-ignore
            const __VLS_208 = __VLS_asFunctionalComponent(__VLS_207, new __VLS_207({
                id: "mail-display",
                defaultSize: (65),
                minSize: (30),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }));
            const __VLS_209 = __VLS_208({
                id: "mail-display",
                defaultSize: (65),
                minSize: (30),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_208));
            __VLS_210.slots.default;
            if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
                /** @type {[typeof ComposeDialog, ]} */ ;
                // @ts-ignore
                const __VLS_211 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
                    panelMode: (true),
                }));
                const __VLS_212 = __VLS_211({
                    panelMode: (true),
                }, ...__VLS_functionalComponentArgsRest(__VLS_211));
            }
            else {
                /** @type {[typeof MessageDisplay, ]} */ ;
                // @ts-ignore
                const __VLS_214 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
                    message: (__VLS_ctx.store.currentMessage ?? undefined),
                }));
                const __VLS_215 = __VLS_214({
                    message: (__VLS_ctx.store.currentMessage ?? undefined),
                }, ...__VLS_functionalComponentArgsRest(__VLS_214));
            }
            var __VLS_210;
        }
        else {
            const __VLS_217 = {}.SplitterPanel;
            /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
            // @ts-ignore
            const __VLS_218 = __VLS_asFunctionalComponent(__VLS_217, new __VLS_217({
                id: "mail-content",
                defaultSize: (100),
                minSize: (30),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }));
            const __VLS_219 = __VLS_218({
                id: "mail-content",
                defaultSize: (100),
                minSize: (30),
                ...{ class: "flex flex-col overflow-hidden" },
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_218));
            __VLS_220.slots.default;
            if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
                /** @type {[typeof ComposeDialog, ]} */ ;
                // @ts-ignore
                const __VLS_221 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
                    panelMode: (true),
                }));
                const __VLS_222 = __VLS_221({
                    panelMode: (true),
                }, ...__VLS_functionalComponentArgsRest(__VLS_221));
            }
            else {
                if (!__VLS_ctx.store.currentMessage) {
                    /** @type {[typeof MessageList, ]} */ ;
                    // @ts-ignore
                    const __VLS_224 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
                    const __VLS_225 = __VLS_224({}, ...__VLS_functionalComponentArgsRest(__VLS_224));
                }
                else {
                    /** @type {[typeof MessageDisplay, ]} */ ;
                    // @ts-ignore
                    const __VLS_227 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
                        message: (__VLS_ctx.store.currentMessage ?? undefined),
                    }));
                    const __VLS_228 = __VLS_227({
                        message: (__VLS_ctx.store.currentMessage ?? undefined),
                    }, ...__VLS_functionalComponentArgsRest(__VLS_227));
                }
            }
            var __VLS_220;
        }
        var __VLS_195;
    }
}
if (!__VLS_ctx.isMobile) {
    /** @type {[typeof ComposeDialog, ]} */ ;
    // @ts-ignore
    const __VLS_230 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({}));
    const __VLS_231 = __VLS_230({}, ...__VLS_functionalComponentArgsRest(__VLS_230));
}
else {
    const __VLS_233 = {}.Teleport;
    /** @type {[typeof __VLS_components.Teleport, typeof __VLS_components.Teleport, ]} */ ;
    // @ts-ignore
    const __VLS_234 = __VLS_asFunctionalComponent(__VLS_233, new __VLS_233({
        to: "body",
    }));
    const __VLS_235 = __VLS_234({
        to: "body",
    }, ...__VLS_functionalComponentArgsRest(__VLS_234));
    __VLS_236.slots.default;
    if (__VLS_ctx.store.isComposeOpen) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "fixed inset-0 z-50 flex flex-col pt-safe" },
            ...{ style: {} },
        });
        /** @type {[typeof ComposeDialog, ]} */ ;
        // @ts-ignore
        const __VLS_237 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
            panelMode: (true),
        }));
        const __VLS_238 = __VLS_237({
            panelMode: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_237));
    }
    if (__VLS_ctx.store.isSettingsOpen) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "fixed inset-0 z-50 flex flex-col pt-safe" },
            ...{ style: {} },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex items-center gap-2 px-3 pb-2 border-b border-border flex-shrink-0" },
            ...{ style: {} },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.isMobile))
                        return;
                    if (!(__VLS_ctx.store.isSettingsOpen))
                        return;
                    __VLS_ctx.store.isSettingsOpen = false;
                } },
            ...{ class: "inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground active:bg-accent transition-colors" },
        });
        const __VLS_240 = {}.ArrowLeft;
        /** @type {[typeof __VLS_components.ArrowLeft, ]} */ ;
        // @ts-ignore
        const __VLS_241 = __VLS_asFunctionalComponent(__VLS_240, new __VLS_240({
            ...{ class: "size-5" },
        }));
        const __VLS_242 = __VLS_241({
            ...{ class: "size-5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_241));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[15px] font-semibold" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex flex-1 min-h-0 overflow-hidden" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "w-44 flex-shrink-0 border-r border-border overflow-y-auto" },
            ...{ style: {} },
        });
        /** @type {[typeof SettingsNav, ]} */ ;
        // @ts-ignore
        const __VLS_244 = __VLS_asFunctionalComponent(SettingsNav, new SettingsNav({}));
        const __VLS_245 = __VLS_244({}, ...__VLS_functionalComponentArgsRest(__VLS_244));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex-1 overflow-hidden" },
            ...{ style: {} },
        });
        /** @type {[typeof SettingsPanel, ]} */ ;
        // @ts-ignore
        const __VLS_247 = __VLS_asFunctionalComponent(SettingsPanel, new SettingsPanel({
            hideHeader: (true),
        }));
        const __VLS_248 = __VLS_247({
            hideHeader: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_247));
    }
    var __VLS_236;
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[100dvh]']} */ ;
/** @type {__VLS_StyleScopedClasses['w-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-end']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-2']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-safe']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['font-[\'Outfit\']']} */ ;
/** @type {__VLS_StyleScopedClasses['font-extrabold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[19px]']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-[-0.01em]']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[#194466]']} */ ;
/** @type {__VLS_StyleScopedClasses['dark:text-[#5EB1E5]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[#FBA612]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[15px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-accent']} */ ;
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
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-around']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-safe']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['px-6']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[44px]']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['h-12']} */ ;
/** @type {__VLS_StyleScopedClasses['w-12']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['px-6']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[44px]']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['h-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['w-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-row']} */ ;
/** @type {__VLS_StyleScopedClasses['df-sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[54px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-[14px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-7']} */ ;
/** @type {__VLS_StyleScopedClasses['w-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['font-[\'Outfit\']']} */ ;
/** @type {__VLS_StyleScopedClasses['font-extrabold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[15px]']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[#194466]']} */ ;
/** @type {__VLS_StyleScopedClasses['dark:text-[#5EB1E5]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[#FBA612]']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-3']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['df-compose-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['df-compose-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[34px]']} */ ;
/** @type {__VLS_StyleScopedClasses['w-[34px]']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-auto']} */ ;
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
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/60']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/60']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/60']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/60']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
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
/** @type {__VLS_StyleScopedClasses['flex-none']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['border-r']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['items-stretch']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['self-stretch']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-border/30']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-border/60']} */ ;
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
/** @type {__VLS_StyleScopedClasses['pt-safe']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-safe']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-2']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['active:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[15px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-0']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['w-44']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['border-r']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
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
            ChevronLeft: ChevronLeft,
            Menu: Menu,
            PanelLeftClose: PanelLeftClose,
            PanelLeftOpen: PanelLeftOpen,
            ArrowLeft: ArrowLeft,
            MailboxSelector: MailboxSelector,
            FolderNav: FolderNav,
            MessageList: MessageList,
            MessageDisplay: MessageDisplay,
            ComposeDialog: ComposeDialog,
            SettingsNav: SettingsNav,
            SettingsPanel: SettingsPanel,
            store: store,
            logout: logout,
            isMobile: isMobile,
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