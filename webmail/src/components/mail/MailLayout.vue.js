/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { SplitterGroup, SplitterPanel, SplitterResizeHandle, TooltipProvider, TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal, } from 'radix-vue';
import { PenSquare, Sun, Moon, LogOut } from 'lucide-vue-next';
import { cn } from '../../lib/utils';
import MailboxSelector from './MailboxSelector.vue';
import FolderNav from './FolderNav.vue';
import MessageList from './MessageList.vue';
import MessageDisplay from './MessageDisplay.vue';
import ComposeDialog from './ComposeDialog.vue';
import { useMailStore } from '../../stores/mail';
import { useAuth } from '../../composables/useAuth';
const store = useMailStore();
const { logout } = useAuth();
const onCollapse = () => { store.isCollapsed = true; };
const onExpand = () => { store.isCollapsed = false; };
const compose = () => {
    store.composeDefaults = null;
    store.isComposeOpen = true;
};
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
const __VLS_5 = {}.SplitterGroup;
/** @type {[typeof __VLS_components.SplitterGroup, typeof __VLS_components.SplitterGroup, ]} */ ;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    id: "mail-layout",
    direction: "horizontal",
    ...{ class: "h-screen w-screen items-stretch" },
}));
const __VLS_7 = __VLS_6({
    id: "mail-layout",
    direction: "horizontal",
    ...{ class: "h-screen w-screen items-stretch" },
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
__VLS_8.slots.default;
const __VLS_9 = {}.SplitterPanel;
/** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
// @ts-ignore
const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
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
const __VLS_11 = __VLS_10({
    ...{ 'onCollapse': {} },
    ...{ 'onExpand': {} },
    id: "sidebar",
    defaultSize: (20),
    collapsedSize: (4),
    collapsible: true,
    minSize: (15),
    maxSize: (22),
    ...{ class: (__VLS_ctx.cn('flex flex-col', __VLS_ctx.store.isCollapsed && 'min-w-[50px] transition-all duration-300 ease-in-out')) },
}, ...__VLS_functionalComponentArgsRest(__VLS_10));
let __VLS_13;
let __VLS_14;
let __VLS_15;
const __VLS_16 = {
    onCollapse: (__VLS_ctx.onCollapse)
};
const __VLS_17 = {
    onExpand: (__VLS_ctx.onExpand)
};
__VLS_12.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: (__VLS_ctx.cn('h-[52px] flex items-center gap-1 px-2 flex-shrink-0', __VLS_ctx.store.isCollapsed ? 'flex-col justify-center py-1' : 'flex-row')) },
});
if (!__VLS_ctx.store.isCollapsed) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-1 min-w-0" },
    });
    /** @type {[typeof MailboxSelector, ]} */ ;
    // @ts-ignore
    const __VLS_18 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
        isCollapsed: (false),
    }));
    const __VLS_19 = __VLS_18({
        isCollapsed: (false),
    }, ...__VLS_functionalComponentArgsRest(__VLS_18));
    const __VLS_21 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        delayDuration: (0),
    }));
    const __VLS_23 = __VLS_22({
        delayDuration: (0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    __VLS_24.slots.default;
    const __VLS_25 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({
        asChild: true,
    }));
    const __VLS_27 = __VLS_26({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_26));
    __VLS_28.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.compose) },
        ...{ class: "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex-shrink-0" },
    });
    const __VLS_29 = {}.PenSquare;
    /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
    // @ts-ignore
    const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({
        ...{ class: "size-4" },
    }));
    const __VLS_31 = __VLS_30({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_30));
    var __VLS_28;
    var __VLS_24;
    const __VLS_33 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_34 = __VLS_asFunctionalComponent(__VLS_33, new __VLS_33({
        delayDuration: (0),
    }));
    const __VLS_35 = __VLS_34({
        delayDuration: (0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_34));
    __VLS_36.slots.default;
    const __VLS_37 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_38 = __VLS_asFunctionalComponent(__VLS_37, new __VLS_37({
        asChild: true,
    }));
    const __VLS_39 = __VLS_38({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_38));
    __VLS_40.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(!__VLS_ctx.store.isCollapsed))
                    return;
                __VLS_ctx.store.toggleViewMode();
            } },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
    });
    if (__VLS_ctx.store.viewMode === 'full') {
        const __VLS_41 = {}.Columns;
        /** @type {[typeof __VLS_components.Columns, ]} */ ;
        // @ts-ignore
        const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
            ...{ class: "size-4" },
        }));
        const __VLS_43 = __VLS_42({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    }
    else {
        const __VLS_45 = {}.Maximize;
        /** @type {[typeof __VLS_components.Maximize, ]} */ ;
        // @ts-ignore
        const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
            ...{ class: "size-4" },
        }));
        const __VLS_47 = __VLS_46({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_46));
    }
    var __VLS_40;
    const __VLS_49 = {}.TooltipPortal;
    /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
    // @ts-ignore
    const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({}));
    const __VLS_51 = __VLS_50({}, ...__VLS_functionalComponentArgsRest(__VLS_50));
    __VLS_52.slots.default;
    const __VLS_53 = {}.TooltipContent;
    /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
    // @ts-ignore
    const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
        side: "bottom",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }));
    const __VLS_55 = __VLS_54({
        side: "bottom",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    __VLS_56.slots.default;
    (__VLS_ctx.store.viewMode === 'full' ? 'Split view' : 'Full view');
    var __VLS_56;
    var __VLS_52;
    var __VLS_36;
    const __VLS_57 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
        delayDuration: (0),
    }));
    const __VLS_59 = __VLS_58({
        delayDuration: (0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_58));
    __VLS_60.slots.default;
    const __VLS_61 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_62 = __VLS_asFunctionalComponent(__VLS_61, new __VLS_61({
        asChild: true,
    }));
    const __VLS_63 = __VLS_62({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_62));
    __VLS_64.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(!__VLS_ctx.store.isCollapsed))
                    return;
                __VLS_ctx.store.toggleTheme();
            } },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
    });
    if (__VLS_ctx.store.isDark) {
        const __VLS_65 = {}.Sun;
        /** @type {[typeof __VLS_components.Sun, ]} */ ;
        // @ts-ignore
        const __VLS_66 = __VLS_asFunctionalComponent(__VLS_65, new __VLS_65({
            ...{ class: "size-4" },
        }));
        const __VLS_67 = __VLS_66({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_66));
    }
    else {
        const __VLS_69 = {}.Moon;
        /** @type {[typeof __VLS_components.Moon, ]} */ ;
        // @ts-ignore
        const __VLS_70 = __VLS_asFunctionalComponent(__VLS_69, new __VLS_69({
            ...{ class: "size-4" },
        }));
        const __VLS_71 = __VLS_70({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_70));
    }
    var __VLS_64;
    const __VLS_73 = {}.TooltipPortal;
    /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
    // @ts-ignore
    const __VLS_74 = __VLS_asFunctionalComponent(__VLS_73, new __VLS_73({}));
    const __VLS_75 = __VLS_74({}, ...__VLS_functionalComponentArgsRest(__VLS_74));
    __VLS_76.slots.default;
    const __VLS_77 = {}.TooltipContent;
    /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
    // @ts-ignore
    const __VLS_78 = __VLS_asFunctionalComponent(__VLS_77, new __VLS_77({
        side: "bottom",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }));
    const __VLS_79 = __VLS_78({
        side: "bottom",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_78));
    __VLS_80.slots.default;
    (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
    var __VLS_80;
    var __VLS_76;
    var __VLS_60;
    const __VLS_81 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_82 = __VLS_asFunctionalComponent(__VLS_81, new __VLS_81({
        delayDuration: (0),
    }));
    const __VLS_83 = __VLS_82({
        delayDuration: (0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_82));
    __VLS_84.slots.default;
    const __VLS_85 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_86 = __VLS_asFunctionalComponent(__VLS_85, new __VLS_85({
        asChild: true,
    }));
    const __VLS_87 = __VLS_86({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_86));
    __VLS_88.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.logout) },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors flex-shrink-0" },
    });
    const __VLS_89 = {}.LogOut;
    /** @type {[typeof __VLS_components.LogOut, ]} */ ;
    // @ts-ignore
    const __VLS_90 = __VLS_asFunctionalComponent(__VLS_89, new __VLS_89({
        ...{ class: "size-4" },
    }));
    const __VLS_91 = __VLS_90({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_90));
    var __VLS_88;
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
    var __VLS_100;
    var __VLS_96;
    var __VLS_84;
}
else {
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
        ...{ onClick: (__VLS_ctx.compose) },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors" },
    });
    const __VLS_109 = {}.PenSquare;
    /** @type {[typeof __VLS_components.PenSquare, ]} */ ;
    // @ts-ignore
    const __VLS_110 = __VLS_asFunctionalComponent(__VLS_109, new __VLS_109({
        ...{ class: "size-4" },
    }));
    const __VLS_111 = __VLS_110({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_110));
    var __VLS_108;
    const __VLS_113 = {}.TooltipPortal;
    /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
    // @ts-ignore
    const __VLS_114 = __VLS_asFunctionalComponent(__VLS_113, new __VLS_113({}));
    const __VLS_115 = __VLS_114({}, ...__VLS_functionalComponentArgsRest(__VLS_114));
    __VLS_116.slots.default;
    const __VLS_117 = {}.TooltipContent;
    /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
    // @ts-ignore
    const __VLS_118 = __VLS_asFunctionalComponent(__VLS_117, new __VLS_117({
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }));
    const __VLS_119 = __VLS_118({
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_118));
    __VLS_120.slots.default;
    var __VLS_120;
    var __VLS_116;
    var __VLS_104;
    const __VLS_121 = {}.TooltipRoot;
    /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
    // @ts-ignore
    const __VLS_122 = __VLS_asFunctionalComponent(__VLS_121, new __VLS_121({
        delayDuration: (0),
    }));
    const __VLS_123 = __VLS_122({
        delayDuration: (0),
    }, ...__VLS_functionalComponentArgsRest(__VLS_122));
    __VLS_124.slots.default;
    const __VLS_125 = {}.TooltipTrigger;
    /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_126 = __VLS_asFunctionalComponent(__VLS_125, new __VLS_125({
        asChild: true,
    }));
    const __VLS_127 = __VLS_126({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_126));
    __VLS_128.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.store.isCollapsed))
                    return;
                __VLS_ctx.store.toggleTheme();
            } },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
    });
    if (__VLS_ctx.store.isDark) {
        const __VLS_129 = {}.Sun;
        /** @type {[typeof __VLS_components.Sun, ]} */ ;
        // @ts-ignore
        const __VLS_130 = __VLS_asFunctionalComponent(__VLS_129, new __VLS_129({
            ...{ class: "size-4" },
        }));
        const __VLS_131 = __VLS_130({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_130));
    }
    else {
        const __VLS_133 = {}.Moon;
        /** @type {[typeof __VLS_components.Moon, ]} */ ;
        // @ts-ignore
        const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
            ...{ class: "size-4" },
        }));
        const __VLS_135 = __VLS_134({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_134));
    }
    var __VLS_128;
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
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }));
    const __VLS_143 = __VLS_142({
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_142));
    __VLS_144.slots.default;
    (__VLS_ctx.store.isDark ? 'Light mode' : 'Dark mode');
    var __VLS_144;
    var __VLS_140;
    var __VLS_124;
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
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent transition-colors" },
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
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }));
    const __VLS_163 = __VLS_162({
        side: "right",
        ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_162));
    __VLS_164.slots.default;
    var __VLS_164;
    var __VLS_160;
    var __VLS_148;
    /** @type {[typeof MailboxSelector, ]} */ ;
    // @ts-ignore
    const __VLS_165 = __VLS_asFunctionalComponent(MailboxSelector, new MailboxSelector({
        isCollapsed: (true),
    }));
    const __VLS_166 = __VLS_165({
        isCollapsed: (true),
    }, ...__VLS_functionalComponentArgsRest(__VLS_165));
}
/** @type {[typeof FolderNav, ]} */ ;
// @ts-ignore
const __VLS_168 = __VLS_asFunctionalComponent(FolderNav, new FolderNav({
    isCollapsed: (__VLS_ctx.store.isCollapsed),
}));
const __VLS_169 = __VLS_168({
    isCollapsed: (__VLS_ctx.store.isCollapsed),
}, ...__VLS_functionalComponentArgsRest(__VLS_168));
var __VLS_12;
const __VLS_171 = {}.SplitterResizeHandle;
/** @type {[typeof __VLS_components.SplitterResizeHandle, ]} */ ;
// @ts-ignore
const __VLS_172 = __VLS_asFunctionalComponent(__VLS_171, new __VLS_171({
    id: "sidebar-handle",
    ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
}));
const __VLS_173 = __VLS_172({
    id: "sidebar-handle",
    ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
}, ...__VLS_functionalComponentArgsRest(__VLS_172));
if (__VLS_ctx.store.viewMode === 'split') {
    const __VLS_175 = {}.SplitterPanel;
    /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
    // @ts-ignore
    const __VLS_176 = __VLS_asFunctionalComponent(__VLS_175, new __VLS_175({
        id: "mail-list",
        defaultSize: (35),
        minSize: (25),
        ...{ class: "flex flex-col overflow-hidden" },
    }));
    const __VLS_177 = __VLS_176({
        id: "mail-list",
        defaultSize: (35),
        minSize: (25),
        ...{ class: "flex flex-col overflow-hidden" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_176));
    __VLS_178.slots.default;
    /** @type {[typeof MessageList, ]} */ ;
    // @ts-ignore
    const __VLS_179 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
    const __VLS_180 = __VLS_179({}, ...__VLS_functionalComponentArgsRest(__VLS_179));
    var __VLS_178;
    const __VLS_182 = {}.SplitterResizeHandle;
    /** @type {[typeof __VLS_components.SplitterResizeHandle, ]} */ ;
    // @ts-ignore
    const __VLS_183 = __VLS_asFunctionalComponent(__VLS_182, new __VLS_182({
        id: "display-handle",
        ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
    }));
    const __VLS_184 = __VLS_183({
        id: "display-handle",
        ...{ class: "self-stretch w-[3px] bg-transparent hover:bg-border active:bg-primary/40 transition-colors" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_183));
    const __VLS_186 = {}.SplitterPanel;
    /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
    // @ts-ignore
    const __VLS_187 = __VLS_asFunctionalComponent(__VLS_186, new __VLS_186({
        id: "mail-display",
        defaultSize: (45),
        minSize: (30),
        ...{ class: "flex flex-col overflow-hidden" },
    }));
    const __VLS_188 = __VLS_187({
        id: "mail-display",
        defaultSize: (45),
        minSize: (30),
        ...{ class: "flex flex-col overflow-hidden" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_187));
    __VLS_189.slots.default;
    if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
        /** @type {[typeof ComposeDialog, ]} */ ;
        // @ts-ignore
        const __VLS_190 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
            panelMode: (true),
        }));
        const __VLS_191 = __VLS_190({
            panelMode: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_190));
    }
    else {
        /** @type {[typeof MessageDisplay, ]} */ ;
        // @ts-ignore
        const __VLS_193 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
            message: (__VLS_ctx.store.currentMessage),
        }));
        const __VLS_194 = __VLS_193({
            message: (__VLS_ctx.store.currentMessage),
        }, ...__VLS_functionalComponentArgsRest(__VLS_193));
    }
    var __VLS_189;
}
else {
    const __VLS_196 = {}.SplitterPanel;
    /** @type {[typeof __VLS_components.SplitterPanel, typeof __VLS_components.SplitterPanel, ]} */ ;
    // @ts-ignore
    const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
        id: "mail-content",
        defaultSize: (80),
        minSize: (30),
        ...{ class: "flex flex-col overflow-hidden" },
    }));
    const __VLS_198 = __VLS_197({
        id: "mail-content",
        defaultSize: (80),
        minSize: (30),
        ...{ class: "flex flex-col overflow-hidden" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_197));
    __VLS_199.slots.default;
    if (__VLS_ctx.store.isComposeOpen && __VLS_ctx.store.isComposeFullView) {
        /** @type {[typeof ComposeDialog, ]} */ ;
        // @ts-ignore
        const __VLS_200 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({
            panelMode: (true),
        }));
        const __VLS_201 = __VLS_200({
            panelMode: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_200));
    }
    else {
        if (!__VLS_ctx.store.currentMessage) {
            /** @type {[typeof MessageList, ]} */ ;
            // @ts-ignore
            const __VLS_203 = __VLS_asFunctionalComponent(MessageList, new MessageList({}));
            const __VLS_204 = __VLS_203({}, ...__VLS_functionalComponentArgsRest(__VLS_203));
        }
        else {
            /** @type {[typeof MessageDisplay, ]} */ ;
            // @ts-ignore
            const __VLS_206 = __VLS_asFunctionalComponent(MessageDisplay, new MessageDisplay({
                message: (__VLS_ctx.store.currentMessage),
            }));
            const __VLS_207 = __VLS_206({
                message: (__VLS_ctx.store.currentMessage),
            }, ...__VLS_functionalComponentArgsRest(__VLS_206));
        }
    }
    var __VLS_199;
}
var __VLS_8;
/** @type {[typeof ComposeDialog, ]} */ ;
// @ts-ignore
const __VLS_209 = __VLS_asFunctionalComponent(ComposeDialog, new ComposeDialog({}));
const __VLS_210 = __VLS_209({}, ...__VLS_functionalComponentArgsRest(__VLS_209));
var __VLS_3;
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
            cn: cn,
            MailboxSelector: MailboxSelector,
            FolderNav: FolderNav,
            MessageList: MessageList,
            MessageDisplay: MessageDisplay,
            ComposeDialog: ComposeDialog,
            store: store,
            logout: logout,
            onCollapse: onCollapse,
            onExpand: onExpand,
            compose: compose,
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