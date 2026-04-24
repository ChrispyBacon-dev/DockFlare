/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, computed } from 'vue';
import { ArrowDownUp, Trash2 } from 'lucide-vue-next';
import { TabsRoot, TabsList, TabsTrigger, TabsContent, } from 'radix-vue';
import { ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb, } from 'radix-vue';
import { useMailStore } from '../../stores/mail';
import { mailApi } from '../../api/mail';
import MessageListItem from './MessageListItem.vue';
import SearchBar from './SearchBar.vue';
import Dialog from '../ui/Dialog.vue';
import Button from '../ui/Button.vue';
const store = useMailStore();
const showTrashConfirm = ref(false);
const folderColor = computed(() => store.currentFolderObj?.color || '');
const unreadMessages = computed(() => store.messages.filter((m) => !m.is_read));
const starredMessages = computed(() => store.messages.filter((m) => m.is_starred));
const displayMessages = computed(() => {
    let msgs = store.messages;
    if (store.activeTab === 'unread')
        msgs = unreadMessages.value;
    else if (store.activeTab === 'starred')
        msgs = starredMessages.value;
    return [...msgs].sort((a, b) => {
        const tA = new Date(a.received_at || a.sent_at || 0).getTime();
        const tB = new Date(b.received_at || b.sent_at || 0).getTime();
        return store.sortOrder === 'desc' ? tB - tA : tA - tB;
    });
});
const toggleSort = () => {
    store.sortOrder = store.sortOrder === 'desc' ? 'asc' : 'desc';
};
const selectMessage = (msg) => {
    if (msg.is_draft) {
        let parsed = msg.to_addresses;
        if (typeof parsed === 'string') {
            try {
                parsed = JSON.parse(parsed);
            }
            catch {
                parsed = [parsed];
            }
        }
        const toAddr = Array.isArray(parsed) ? parsed.join(', ') : (parsed || '');
        store.composeDefaults = {
            draftId: msg.id,
            to: toAddr,
            subject: msg.subject || '',
            body: msg.html_body || msg.text_body || '',
        };
        store.isComposeOpen = true;
        return;
    }
    store.currentMessage = msg;
};
const emptyTrash = () => {
    if (store.currentFolderObj && store.currentFolderObj.name === 'Trash') {
        showTrashConfirm.value = true;
    }
};
const performEmptyTrash = async () => {
    if (!store.currentFolderObj)
        return;
    try {
        await mailApi.emptyFolder(store.currentMailbox, store.currentFolderObj.id);
        store.messages = [];
        store.currentMessage = null;
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
    }
    catch {
        store.showToast('Failed to empty trash');
    }
    finally {
        showTrashConfirm.value = false;
    }
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['list-leave-active']} */ ;
// CSS variable injection 
// CSS variable injection end 
const __VLS_0 = {}.TabsRoot;
/** @type {[typeof __VLS_components.TabsRoot, typeof __VLS_components.TabsRoot, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    modelValue: (__VLS_ctx.store.activeTab),
    ...{ class: "flex h-full flex-col" },
}));
const __VLS_2 = __VLS_1({
    modelValue: (__VLS_ctx.store.activeTab),
    ...{ class: "flex h-full flex-col" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "h-[52px] flex items-center px-4 flex-shrink-0" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({
    ...{ class: "text-xl font-bold" },
});
(__VLS_ctx.store.currentFolder || 'Inbox');
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "ml-auto flex items-center gap-1" },
});
if (__VLS_ctx.store.currentFolder === 'Trash' && __VLS_ctx.store.messages.length > 0) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.emptyTrash) },
        ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors" },
        title: "Empty Trash",
    });
    const __VLS_4 = {}.Trash2;
    /** @type {[typeof __VLS_components.Trash2, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        ...{ class: "size-4" },
    }));
    const __VLS_6 = __VLS_5({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.toggleSort) },
    ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
    title: (__VLS_ctx.store.sortOrder === 'desc' ? 'Oldest first' : 'Newest first'),
});
const __VLS_8 = {}.ArrowDownUp;
/** @type {[typeof __VLS_components.ArrowDownUp, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    ...{ class: "size-4" },
    ...{ class: (__VLS_ctx.store.sortOrder === 'asc' ? 'rotate-180' : '') },
}));
const __VLS_10 = __VLS_9({
    ...{ class: "size-4" },
    ...{ class: (__VLS_ctx.store.sortOrder === 'asc' ? 'rotate-180' : '') },
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
const __VLS_12 = {}.TabsList;
/** @type {[typeof __VLS_components.TabsList, typeof __VLS_components.TabsList, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    ...{ class: "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground" },
}));
const __VLS_14 = __VLS_13({
    ...{ class: "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground" },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_15.slots.default;
const __VLS_16 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    value: "all",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}));
const __VLS_18 = __VLS_17({
    value: "all",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_19.slots.default;
var __VLS_19;
const __VLS_20 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    value: "unread",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}));
const __VLS_22 = __VLS_21({
    value: "unread",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
var __VLS_23;
const __VLS_24 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    value: "starred",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}));
const __VLS_26 = __VLS_25({
    value: "starred",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow" },
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
var __VLS_27;
var __VLS_15;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "bg-background/95 p-4 backdrop-blur supports-[backdrop-filter]:bg-background/60" },
});
/** @type {[typeof SearchBar, ]} */ ;
// @ts-ignore
const __VLS_28 = __VLS_asFunctionalComponent(SearchBar, new SearchBar({}));
const __VLS_29 = __VLS_28({}, ...__VLS_functionalComponentArgsRest(__VLS_28));
const __VLS_31 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_32 = __VLS_asFunctionalComponent(__VLS_31, new __VLS_31({
    value: "all",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_33 = __VLS_32({
    value: "all",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_32));
__VLS_34.slots.default;
const __VLS_35 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_36 = __VLS_asFunctionalComponent(__VLS_35, new __VLS_35({
    ...{ class: "h-full" },
}));
const __VLS_37 = __VLS_36({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_36));
__VLS_38.slots.default;
const __VLS_39 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_40 = __VLS_asFunctionalComponent(__VLS_39, new __VLS_39({
    ...{ class: "h-full" },
}));
const __VLS_41 = __VLS_40({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_40));
__VLS_42.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col gap-2 p-4 pt-0" },
});
if (__VLS_ctx.store.messagesLoading) {
    for (const [n] of __VLS_getVForSourceType((6))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            key: (n),
            ...{ class: "h-16 rounded-lg bg-muted animate-pulse" },
        });
    }
}
else {
    const __VLS_43 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_44 = __VLS_asFunctionalComponent(__VLS_43, new __VLS_43({
        name: "list",
        appear: true,
    }));
    const __VLS_45 = __VLS_44({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_44));
    __VLS_46.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_47 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }));
        const __VLS_48 = __VLS_47({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }, ...__VLS_functionalComponentArgsRest(__VLS_47));
        let __VLS_50;
        let __VLS_51;
        let __VLS_52;
        const __VLS_53 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_49;
    }
    var __VLS_46;
    if (__VLS_ctx.displayMessages.length === 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "p-8 text-center text-muted-foreground" },
        });
    }
    if (__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.store.messagesLoading))
                        return;
                    if (!(__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading))
                        return;
                    __VLS_ctx.store.loadMore();
                } },
            ...{ class: "w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50" },
            disabled: (__VLS_ctx.store.isFetchingNextPage),
        });
        (__VLS_ctx.store.isFetchingNextPage ? 'Loading…' : 'Load more');
    }
}
var __VLS_42;
const __VLS_54 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_55 = __VLS_asFunctionalComponent(__VLS_54, new __VLS_54({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_56 = __VLS_55({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_55));
__VLS_57.slots.default;
const __VLS_58 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_59 = __VLS_asFunctionalComponent(__VLS_58, new __VLS_58({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_60 = __VLS_59({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_59));
var __VLS_57;
var __VLS_38;
var __VLS_34;
const __VLS_62 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_63 = __VLS_asFunctionalComponent(__VLS_62, new __VLS_62({
    value: "unread",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_64 = __VLS_63({
    value: "unread",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_63));
__VLS_65.slots.default;
const __VLS_66 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_67 = __VLS_asFunctionalComponent(__VLS_66, new __VLS_66({
    ...{ class: "h-full" },
}));
const __VLS_68 = __VLS_67({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_67));
__VLS_69.slots.default;
const __VLS_70 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_71 = __VLS_asFunctionalComponent(__VLS_70, new __VLS_70({
    ...{ class: "h-full" },
}));
const __VLS_72 = __VLS_71({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_71));
__VLS_73.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col gap-2 p-4 pt-0" },
});
if (__VLS_ctx.store.messagesLoading) {
    for (const [n] of __VLS_getVForSourceType((6))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            key: (n),
            ...{ class: "h-16 rounded-lg bg-muted animate-pulse" },
        });
    }
}
else {
    const __VLS_74 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_75 = __VLS_asFunctionalComponent(__VLS_74, new __VLS_74({
        name: "list",
        appear: true,
    }));
    const __VLS_76 = __VLS_75({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_75));
    __VLS_77.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_78 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }));
        const __VLS_79 = __VLS_78({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }, ...__VLS_functionalComponentArgsRest(__VLS_78));
        let __VLS_81;
        let __VLS_82;
        let __VLS_83;
        const __VLS_84 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_80;
    }
    var __VLS_77;
    if (__VLS_ctx.displayMessages.length === 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "p-8 text-center text-muted-foreground" },
        });
    }
    if (__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.store.messagesLoading))
                        return;
                    if (!(__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading))
                        return;
                    __VLS_ctx.store.loadMore();
                } },
            ...{ class: "w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50" },
            disabled: (__VLS_ctx.store.isFetchingNextPage),
        });
        (__VLS_ctx.store.isFetchingNextPage ? 'Loading…' : 'Load more');
    }
}
var __VLS_73;
const __VLS_85 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_86 = __VLS_asFunctionalComponent(__VLS_85, new __VLS_85({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_87 = __VLS_86({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_86));
__VLS_88.slots.default;
const __VLS_89 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_90 = __VLS_asFunctionalComponent(__VLS_89, new __VLS_89({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_91 = __VLS_90({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_90));
var __VLS_88;
var __VLS_69;
var __VLS_65;
const __VLS_93 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_94 = __VLS_asFunctionalComponent(__VLS_93, new __VLS_93({
    value: "starred",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_95 = __VLS_94({
    value: "starred",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_94));
__VLS_96.slots.default;
const __VLS_97 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_98 = __VLS_asFunctionalComponent(__VLS_97, new __VLS_97({
    ...{ class: "h-full" },
}));
const __VLS_99 = __VLS_98({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_98));
__VLS_100.slots.default;
const __VLS_101 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_102 = __VLS_asFunctionalComponent(__VLS_101, new __VLS_101({
    ...{ class: "h-full" },
}));
const __VLS_103 = __VLS_102({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_102));
__VLS_104.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col gap-2 p-4 pt-0" },
});
if (__VLS_ctx.store.messagesLoading) {
    for (const [n] of __VLS_getVForSourceType((6))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            key: (n),
            ...{ class: "h-16 rounded-lg bg-muted animate-pulse" },
        });
    }
}
else {
    const __VLS_105 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_106 = __VLS_asFunctionalComponent(__VLS_105, new __VLS_105({
        name: "list",
        appear: true,
    }));
    const __VLS_107 = __VLS_106({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_106));
    __VLS_108.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_109 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }));
        const __VLS_110 = __VLS_109({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
        }, ...__VLS_functionalComponentArgsRest(__VLS_109));
        let __VLS_112;
        let __VLS_113;
        let __VLS_114;
        const __VLS_115 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_111;
    }
    var __VLS_108;
    if (__VLS_ctx.displayMessages.length === 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "p-8 text-center text-muted-foreground" },
        });
    }
    if (__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.store.messagesLoading))
                        return;
                    if (!(__VLS_ctx.store.hasMoreMessages && !__VLS_ctx.store.messagesLoading))
                        return;
                    __VLS_ctx.store.loadMore();
                } },
            ...{ class: "w-full py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50" },
            disabled: (__VLS_ctx.store.isFetchingNextPage),
        });
        (__VLS_ctx.store.isFetchingNextPage ? 'Loading…' : 'Load more');
    }
}
var __VLS_104;
const __VLS_116 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_118 = __VLS_117({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_117));
__VLS_119.slots.default;
const __VLS_120 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_122 = __VLS_121({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_121));
var __VLS_119;
var __VLS_100;
var __VLS_96;
var __VLS_3;
/** @type {[typeof Dialog, typeof Dialog, ]} */ ;
// @ts-ignore
const __VLS_124 = __VLS_asFunctionalComponent(Dialog, new Dialog({
    open: (__VLS_ctx.showTrashConfirm),
}));
const __VLS_125 = __VLS_124({
    open: (__VLS_ctx.showTrashConfirm),
}, ...__VLS_functionalComponentArgsRest(__VLS_124));
__VLS_126.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "space-y-4" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({
    ...{ class: "text-lg font-semibold leading-none tracking-tight" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "text-sm text-muted-foreground" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex justify-end gap-2 pt-4" },
});
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_127 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "outline",
}));
const __VLS_128 = __VLS_127({
    ...{ 'onClick': {} },
    variant: "outline",
}, ...__VLS_functionalComponentArgsRest(__VLS_127));
let __VLS_130;
let __VLS_131;
let __VLS_132;
const __VLS_133 = {
    onClick: (...[$event]) => {
        __VLS_ctx.showTrashConfirm = false;
    }
};
__VLS_129.slots.default;
var __VLS_129;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_134 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "destructive",
}));
const __VLS_135 = __VLS_134({
    ...{ 'onClick': {} },
    variant: "destructive",
}, ...__VLS_functionalComponentArgsRest(__VLS_134));
let __VLS_137;
let __VLS_138;
let __VLS_139;
const __VLS_140 = {
    onClick: (__VLS_ctx.performEmptyTrash)
};
__VLS_136.slots.default;
var __VLS_136;
var __VLS_126;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[52px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive-foreground']} */ ;
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
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['ring-offset-background']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-2']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-offset-2']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:shadow']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['ring-offset-background']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-2']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-offset-2']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:shadow']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['ring-offset-background']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-2']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:ring-offset-2']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:shadow']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background/95']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['backdrop-blur']} */ ;
/** @type {__VLS_StyleScopedClasses['supports-[backdrop-filter]:bg-background/60']} */ ;
/** @type {__VLS_StyleScopedClasses['m-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-16']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['p-8']} */ ;
/** @type {__VLS_StyleScopedClasses['text-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled:opacity-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['touch-none']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['m-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-16']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['p-8']} */ ;
/** @type {__VLS_StyleScopedClasses['text-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled:opacity-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['touch-none']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['m-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-16']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['p-8']} */ ;
/** @type {__VLS_StyleScopedClasses['text-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled:opacity-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['touch-none']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-tight']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-end']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-4']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            ArrowDownUp: ArrowDownUp,
            Trash2: Trash2,
            TabsRoot: TabsRoot,
            TabsList: TabsList,
            TabsTrigger: TabsTrigger,
            TabsContent: TabsContent,
            ScrollAreaRoot: ScrollAreaRoot,
            ScrollAreaViewport: ScrollAreaViewport,
            ScrollAreaScrollbar: ScrollAreaScrollbar,
            ScrollAreaThumb: ScrollAreaThumb,
            MessageListItem: MessageListItem,
            SearchBar: SearchBar,
            Dialog: Dialog,
            Button: Button,
            store: store,
            showTrashConfirm: showTrashConfirm,
            folderColor: folderColor,
            displayMessages: displayMessages,
            toggleSort: toggleSort,
            selectMessage: selectMessage,
            emptyTrash: emptyTrash,
            performEmptyTrash: performEmptyTrash,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MessageList.vue.js.map