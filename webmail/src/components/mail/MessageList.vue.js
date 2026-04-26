/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, computed, watch } from 'vue';
import { ArrowDownUp, Trash2, Square, CheckSquare, FolderInput } from 'lucide-vue-next';
import { TabsRoot, TabsList, TabsTrigger, TabsContent, } from 'radix-vue';
import { ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb, } from 'radix-vue';
import { DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuPortal, } from 'radix-vue';
import { useMailStore } from '../../stores/mail';
import { mailApi } from '../../api/mail';
import MessageListItem from './MessageListItem.vue';
import SearchBar from './SearchBar.vue';
import Dialog from '../ui/Dialog.vue';
import Button from '../ui/Button.vue';
const props = defineProps({
    hideTitle: { type: Boolean, default: false },
});
const store = useMailStore();
const showTrashConfirm = ref(false);
const bulkSelectMode = ref(false);
const selectedIds = ref(new Set());
const isBulkLoading = ref(false);
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
const trashFolder = computed(() => store.folders.find((f) => f.name === 'Trash'));
const otherFolders = computed(() => store.folders.filter((f) => f.name !== store.currentFolder));
const hasSelection = computed(() => selectedIds.value.size > 0);
const allSelected = computed(() => displayMessages.value.length > 0 && selectedIds.value.size === displayMessages.value.length);
watch(() => store.activeTab, () => {
    selectedIds.value = new Set();
});
const toggleSort = () => {
    store.sortOrder = store.sortOrder === 'desc' ? 'asc' : 'desc';
};
function toggleBulkSelect() {
    bulkSelectMode.value = !bulkSelectMode.value;
    if (!bulkSelectMode.value) {
        selectedIds.value = new Set();
    }
}
function toggleSelectAll() {
    if (allSelected.value) {
        selectedIds.value = new Set();
    }
    else {
        selectedIds.value = new Set(displayMessages.value.map((m) => m.id));
    }
}
function toggleMessageSelection(id) {
    const next = new Set(selectedIds.value);
    if (next.has(id))
        next.delete(id);
    else
        next.add(id);
    selectedIds.value = next;
}
const selectMessage = (msg) => {
    if (bulkSelectMode.value) {
        toggleMessageSelection(msg.id);
        return;
    }
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
async function bulkMoveToTrash() {
    if (!hasSelection.value || !trashFolder.value)
        return;
    isBulkLoading.value = true;
    try {
        await mailApi.moveMessages(store.currentMailbox, {
            message_ids: [...selectedIds.value],
            folder_id: trashFolder.value.id,
        });
        store.messages = store.messages.filter((m) => !selectedIds.value.has(m.id));
        selectedIds.value = new Set();
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
        store.showToast('Messages moved to Trash', 'success');
    }
    catch {
        store.showToast('Failed to move messages to Trash');
    }
    finally {
        isBulkLoading.value = false;
    }
}
async function bulkMoveToFolder(folderId, folderName) {
    if (!hasSelection.value)
        return;
    isBulkLoading.value = true;
    try {
        await mailApi.moveMessages(store.currentMailbox, {
            message_ids: [...selectedIds.value],
            folder_id: folderId,
        });
        store.messages = store.messages.filter((m) => !selectedIds.value.has(m.id));
        selectedIds.value = new Set();
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
        store.showToast(`Messages moved to ${folderName}`, 'success');
    }
    catch {
        store.showToast('Failed to move messages');
    }
    finally {
        isBulkLoading.value = false;
    }
}
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
    ...{ class: "flex items-center px-4 flex-shrink-0" },
    ...{ class: (__VLS_ctx.hideTitle ? 'h-[44px]' : 'h-[52px]') },
});
if (!__VLS_ctx.hideTitle) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({
        ...{ class: "text-xl font-bold" },
    });
    (__VLS_ctx.store.currentFolder || 'Inbox');
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-1" },
    ...{ class: (__VLS_ctx.hideTitle ? 'w-full justify-between' : 'ml-auto') },
});
if (__VLS_ctx.bulkSelectMode) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.toggleSelectAll) },
        ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
        title: (__VLS_ctx.allSelected ? 'Deselect all' : 'Select all'),
    });
    if (__VLS_ctx.allSelected) {
        const __VLS_4 = {}.CheckSquare;
        /** @type {[typeof __VLS_components.CheckSquare, ]} */ ;
        // @ts-ignore
        const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
            ...{ class: "size-4" },
        }));
        const __VLS_6 = __VLS_5({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_5));
    }
    else {
        const __VLS_8 = {}.Square;
        /** @type {[typeof __VLS_components.Square, ]} */ ;
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
            ...{ class: "size-4" },
        }));
        const __VLS_10 = __VLS_9({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    }
    if (__VLS_ctx.store.currentFolder !== 'Trash') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.bulkMoveToTrash) },
            ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors" },
            ...{ class: (__VLS_ctx.hasSelection && !__VLS_ctx.isBulkLoading
                    ? 'text-muted-foreground hover:bg-destructive hover:text-destructive-foreground'
                    : 'text-muted-foreground/30 cursor-not-allowed') },
            disabled: (!__VLS_ctx.hasSelection || __VLS_ctx.isBulkLoading),
            title: "Move to Trash",
        });
        const __VLS_12 = {}.Trash2;
        /** @type {[typeof __VLS_components.Trash2, ]} */ ;
        // @ts-ignore
        const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
            ...{ class: "size-4" },
        }));
        const __VLS_14 = __VLS_13({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    }
    const __VLS_16 = {}.DropdownMenuRoot;
    /** @type {[typeof __VLS_components.DropdownMenuRoot, typeof __VLS_components.DropdownMenuRoot, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({}));
    const __VLS_18 = __VLS_17({}, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    const __VLS_20 = {}.DropdownMenuTrigger;
    /** @type {[typeof __VLS_components.DropdownMenuTrigger, typeof __VLS_components.DropdownMenuTrigger, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        asChild: true,
    }));
    const __VLS_22 = __VLS_21({
        asChild: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    __VLS_23.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors" },
        ...{ class: (__VLS_ctx.hasSelection && !__VLS_ctx.isBulkLoading
                ? 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                : 'text-muted-foreground/30 cursor-not-allowed') },
        disabled: (!__VLS_ctx.hasSelection || __VLS_ctx.isBulkLoading),
        title: "Move to folder",
    });
    const __VLS_24 = {}.FolderInput;
    /** @type {[typeof __VLS_components.FolderInput, ]} */ ;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        ...{ class: "size-4" },
    }));
    const __VLS_26 = __VLS_25({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    var __VLS_23;
    const __VLS_28 = {}.DropdownMenuPortal;
    /** @type {[typeof __VLS_components.DropdownMenuPortal, typeof __VLS_components.DropdownMenuPortal, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({}));
    const __VLS_30 = __VLS_29({}, ...__VLS_functionalComponentArgsRest(__VLS_29));
    __VLS_31.slots.default;
    const __VLS_32 = {}.DropdownMenuContent;
    /** @type {[typeof __VLS_components.DropdownMenuContent, typeof __VLS_components.DropdownMenuContent, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        align: "end",
        sideOffset: (4),
        ...{ class: "z-50 min-w-[160px] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
    }));
    const __VLS_34 = __VLS_33({
        align: "end",
        sideOffset: (4),
        ...{ class: "z-50 min-w-[160px] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    __VLS_35.slots.default;
    for (const [folder] of __VLS_getVForSourceType((__VLS_ctx.otherFolders))) {
        const __VLS_36 = {}.DropdownMenuItem;
        /** @type {[typeof __VLS_components.DropdownMenuItem, typeof __VLS_components.DropdownMenuItem, ]} */ ;
        // @ts-ignore
        const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
            ...{ 'onClick': {} },
            key: (folder.id),
            ...{ class: "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground" },
        }));
        const __VLS_38 = __VLS_37({
            ...{ 'onClick': {} },
            key: (folder.id),
            ...{ class: "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_37));
        let __VLS_40;
        let __VLS_41;
        let __VLS_42;
        const __VLS_43 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.bulkSelectMode))
                    return;
                __VLS_ctx.bulkMoveToFolder(folder.id, folder.name);
            }
        };
        __VLS_39.slots.default;
        if (folder.color) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span)({
                ...{ class: "h-2 w-2 rounded-full flex-shrink-0" },
                ...{ style: (`background: ${folder.color}`) },
            });
        }
        (folder.name);
        var __VLS_39;
    }
    var __VLS_35;
    var __VLS_31;
    var __VLS_19;
}
if (__VLS_ctx.store.currentFolder === 'Trash' && __VLS_ctx.store.messages.length > 0 && !__VLS_ctx.bulkSelectMode) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.emptyTrash) },
        ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive hover:text-destructive-foreground transition-colors" },
        title: "Empty Trash",
    });
    const __VLS_44 = {}.Trash2;
    /** @type {[typeof __VLS_components.Trash2, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        ...{ class: "size-4" },
    }));
    const __VLS_46 = __VLS_45({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.toggleBulkSelect) },
    ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors" },
    ...{ class: (__VLS_ctx.bulkSelectMode
            ? 'bg-accent text-[#FBA612]'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground') },
    title: "Select messages",
});
if (__VLS_ctx.bulkSelectMode) {
    const __VLS_48 = {}.CheckSquare;
    /** @type {[typeof __VLS_components.CheckSquare, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        ...{ class: "size-4" },
    }));
    const __VLS_50 = __VLS_49({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
}
else {
    const __VLS_52 = {}.Square;
    /** @type {[typeof __VLS_components.Square, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        ...{ class: "size-4" },
    }));
    const __VLS_54 = __VLS_53({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.toggleSort) },
    ...{ class: "inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
    title: (__VLS_ctx.store.sortOrder === 'desc' ? 'Oldest first' : 'Newest first'),
});
const __VLS_56 = {}.ArrowDownUp;
/** @type {[typeof __VLS_components.ArrowDownUp, ]} */ ;
// @ts-ignore
const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
    ...{ class: "size-4" },
    ...{ class: (__VLS_ctx.store.sortOrder === 'asc' ? 'rotate-180' : '') },
}));
const __VLS_58 = __VLS_57({
    ...{ class: "size-4" },
    ...{ class: (__VLS_ctx.store.sortOrder === 'asc' ? 'rotate-180' : '') },
}, ...__VLS_functionalComponentArgsRest(__VLS_57));
const __VLS_60 = {}.TabsList;
/** @type {[typeof __VLS_components.TabsList, typeof __VLS_components.TabsList, ]} */ ;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
    ...{ class: "inline-flex h-9 items-center gap-1 bg-transparent" },
}));
const __VLS_62 = __VLS_61({
    ...{ class: "inline-flex h-9 items-center gap-1 bg-transparent" },
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
__VLS_63.slots.default;
const __VLS_64 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
    value: "all",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'all' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}));
const __VLS_66 = __VLS_65({
    value: "all",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'all' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}, ...__VLS_functionalComponentArgsRest(__VLS_65));
__VLS_67.slots.default;
var __VLS_67;
const __VLS_68 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
    value: "unread",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'unread' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}));
const __VLS_70 = __VLS_69({
    value: "unread",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'unread' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}, ...__VLS_functionalComponentArgsRest(__VLS_69));
__VLS_71.slots.default;
var __VLS_71;
const __VLS_72 = {}.TabsTrigger;
/** @type {[typeof __VLS_components.TabsTrigger, typeof __VLS_components.TabsTrigger, ]} */ ;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
    value: "starred",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'starred' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}));
const __VLS_74 = __VLS_73({
    value: "starred",
    ...{ class: "inline-flex items-center justify-center whitespace-nowrap rounded-full py-1.5 px-3 text-sm font-medium transition-all data-[state=active]:font-semibold data-[state=inactive]:text-muted-foreground focus-visible:outline-none min-h-[36px]" },
    ...{ style: (__VLS_ctx.store.activeTab === 'starred' ? 'background: rgba(251,166,18,0.12); color: #FBA612;' : '') },
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
__VLS_75.slots.default;
var __VLS_75;
var __VLS_63;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "px-[10px] pb-2" },
});
/** @type {[typeof SearchBar, ]} */ ;
// @ts-ignore
const __VLS_76 = __VLS_asFunctionalComponent(SearchBar, new SearchBar({}));
const __VLS_77 = __VLS_76({}, ...__VLS_functionalComponentArgsRest(__VLS_76));
const __VLS_79 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
    value: "all",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_81 = __VLS_80({
    value: "all",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_80));
__VLS_82.slots.default;
const __VLS_83 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_84 = __VLS_asFunctionalComponent(__VLS_83, new __VLS_83({
    ...{ class: "h-full" },
}));
const __VLS_85 = __VLS_84({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_84));
__VLS_86.slots.default;
const __VLS_87 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_88 = __VLS_asFunctionalComponent(__VLS_87, new __VLS_87({
    ...{ class: "h-full" },
}));
const __VLS_89 = __VLS_88({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_88));
__VLS_90.slots.default;
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
    const __VLS_91 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
        name: "list",
        appear: true,
    }));
    const __VLS_93 = __VLS_92({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_92));
    __VLS_94.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_95 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }));
        const __VLS_96 = __VLS_95({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }, ...__VLS_functionalComponentArgsRest(__VLS_95));
        let __VLS_98;
        let __VLS_99;
        let __VLS_100;
        const __VLS_101 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_97;
    }
    var __VLS_94;
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
var __VLS_90;
const __VLS_102 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_103 = __VLS_asFunctionalComponent(__VLS_102, new __VLS_102({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_104 = __VLS_103({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_103));
__VLS_105.slots.default;
const __VLS_106 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_107 = __VLS_asFunctionalComponent(__VLS_106, new __VLS_106({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_108 = __VLS_107({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_107));
var __VLS_105;
var __VLS_86;
var __VLS_82;
const __VLS_110 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_111 = __VLS_asFunctionalComponent(__VLS_110, new __VLS_110({
    value: "unread",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_112 = __VLS_111({
    value: "unread",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_111));
__VLS_113.slots.default;
const __VLS_114 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_115 = __VLS_asFunctionalComponent(__VLS_114, new __VLS_114({
    ...{ class: "h-full" },
}));
const __VLS_116 = __VLS_115({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_115));
__VLS_117.slots.default;
const __VLS_118 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_119 = __VLS_asFunctionalComponent(__VLS_118, new __VLS_118({
    ...{ class: "h-full" },
}));
const __VLS_120 = __VLS_119({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_119));
__VLS_121.slots.default;
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
    const __VLS_122 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_123 = __VLS_asFunctionalComponent(__VLS_122, new __VLS_122({
        name: "list",
        appear: true,
    }));
    const __VLS_124 = __VLS_123({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_123));
    __VLS_125.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_126 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }));
        const __VLS_127 = __VLS_126({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }, ...__VLS_functionalComponentArgsRest(__VLS_126));
        let __VLS_129;
        let __VLS_130;
        let __VLS_131;
        const __VLS_132 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_128;
    }
    var __VLS_125;
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
var __VLS_121;
const __VLS_133 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_134 = __VLS_asFunctionalComponent(__VLS_133, new __VLS_133({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_135 = __VLS_134({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_134));
__VLS_136.slots.default;
const __VLS_137 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_138 = __VLS_asFunctionalComponent(__VLS_137, new __VLS_137({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_139 = __VLS_138({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_138));
var __VLS_136;
var __VLS_117;
var __VLS_113;
const __VLS_141 = {}.TabsContent;
/** @type {[typeof __VLS_components.TabsContent, typeof __VLS_components.TabsContent, ]} */ ;
// @ts-ignore
const __VLS_142 = __VLS_asFunctionalComponent(__VLS_141, new __VLS_141({
    value: "starred",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}));
const __VLS_143 = __VLS_142({
    value: "starred",
    ...{ class: "m-0 flex-1 overflow-hidden" },
}, ...__VLS_functionalComponentArgsRest(__VLS_142));
__VLS_144.slots.default;
const __VLS_145 = {}.ScrollAreaRoot;
/** @type {[typeof __VLS_components.ScrollAreaRoot, typeof __VLS_components.ScrollAreaRoot, ]} */ ;
// @ts-ignore
const __VLS_146 = __VLS_asFunctionalComponent(__VLS_145, new __VLS_145({
    ...{ class: "h-full" },
}));
const __VLS_147 = __VLS_146({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_146));
__VLS_148.slots.default;
const __VLS_149 = {}.ScrollAreaViewport;
/** @type {[typeof __VLS_components.ScrollAreaViewport, typeof __VLS_components.ScrollAreaViewport, ]} */ ;
// @ts-ignore
const __VLS_150 = __VLS_asFunctionalComponent(__VLS_149, new __VLS_149({
    ...{ class: "h-full" },
}));
const __VLS_151 = __VLS_150({
    ...{ class: "h-full" },
}, ...__VLS_functionalComponentArgsRest(__VLS_150));
__VLS_152.slots.default;
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
    const __VLS_153 = {}.TransitionGroup;
    /** @type {[typeof __VLS_components.TransitionGroup, typeof __VLS_components.TransitionGroup, ]} */ ;
    // @ts-ignore
    const __VLS_154 = __VLS_asFunctionalComponent(__VLS_153, new __VLS_153({
        name: "list",
        appear: true,
    }));
    const __VLS_155 = __VLS_154({
        name: "list",
        appear: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_154));
    __VLS_156.slots.default;
    for (const [msg] of __VLS_getVForSourceType((__VLS_ctx.displayMessages))) {
        /** @type {[typeof MessageListItem, ]} */ ;
        // @ts-ignore
        const __VLS_157 = __VLS_asFunctionalComponent(MessageListItem, new MessageListItem({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }));
        const __VLS_158 = __VLS_157({
            ...{ 'onClick': {} },
            key: (msg.id),
            message: (msg),
            selected: (__VLS_ctx.store.currentMessage?.id === msg.id),
            folderColor: (__VLS_ctx.folderColor),
            bulkSelectMode: (__VLS_ctx.bulkSelectMode),
            isChecked: (__VLS_ctx.selectedIds.has(msg.id)),
        }, ...__VLS_functionalComponentArgsRest(__VLS_157));
        let __VLS_160;
        let __VLS_161;
        let __VLS_162;
        const __VLS_163 = {
            onClick: (...[$event]) => {
                if (!!(__VLS_ctx.store.messagesLoading))
                    return;
                __VLS_ctx.selectMessage(msg);
            }
        };
        var __VLS_159;
    }
    var __VLS_156;
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
var __VLS_152;
const __VLS_164 = {}.ScrollAreaScrollbar;
/** @type {[typeof __VLS_components.ScrollAreaScrollbar, typeof __VLS_components.ScrollAreaScrollbar, ]} */ ;
// @ts-ignore
const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}));
const __VLS_166 = __VLS_165({
    orientation: "vertical",
    ...{ class: "flex touch-none select-none bg-transparent p-0.5 transition-colors w-2.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_165));
__VLS_167.slots.default;
const __VLS_168 = {}.ScrollAreaThumb;
/** @type {[typeof __VLS_components.ScrollAreaThumb, ]} */ ;
// @ts-ignore
const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}));
const __VLS_170 = __VLS_169({
    ...{ class: "relative flex-1 rounded-full bg-border" },
}, ...__VLS_functionalComponentArgsRest(__VLS_169));
var __VLS_167;
var __VLS_148;
var __VLS_144;
var __VLS_3;
/** @type {[typeof Dialog, typeof Dialog, ]} */ ;
// @ts-ignore
const __VLS_172 = __VLS_asFunctionalComponent(Dialog, new Dialog({
    open: (__VLS_ctx.showTrashConfirm),
}));
const __VLS_173 = __VLS_172({
    open: (__VLS_ctx.showTrashConfirm),
}, ...__VLS_functionalComponentArgsRest(__VLS_172));
__VLS_174.slots.default;
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
const __VLS_175 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "outline",
}));
const __VLS_176 = __VLS_175({
    ...{ 'onClick': {} },
    variant: "outline",
}, ...__VLS_functionalComponentArgsRest(__VLS_175));
let __VLS_178;
let __VLS_179;
let __VLS_180;
const __VLS_181 = {
    onClick: (...[$event]) => {
        __VLS_ctx.showTrashConfirm = false;
    }
};
__VLS_177.slots.default;
var __VLS_177;
/** @type {[typeof Button, typeof Button, ]} */ ;
// @ts-ignore
const __VLS_182 = __VLS_asFunctionalComponent(Button, new Button({
    ...{ 'onClick': {} },
    variant: "destructive",
}));
const __VLS_183 = __VLS_182({
    ...{ 'onClick': {} },
    variant: "destructive",
}, ...__VLS_functionalComponentArgsRest(__VLS_182));
let __VLS_185;
let __VLS_186;
let __VLS_187;
const __VLS_188 = {
    onClick: (__VLS_ctx.performEmptyTrash)
};
__VLS_184.slots.default;
var __VLS_184;
var __VLS_174;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['z-50']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-[160px]']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-popover']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-popover-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-md']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
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
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=inactive]:text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[36px]']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=inactive]:text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[36px]']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['whitespace-nowrap']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=active]:font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['data-[state=inactive]:text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['focus-visible:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-[36px]']} */ ;
/** @type {__VLS_StyleScopedClasses['px-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-2']} */ ;
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
            Square: Square,
            CheckSquare: CheckSquare,
            FolderInput: FolderInput,
            TabsRoot: TabsRoot,
            TabsList: TabsList,
            TabsTrigger: TabsTrigger,
            TabsContent: TabsContent,
            ScrollAreaRoot: ScrollAreaRoot,
            ScrollAreaViewport: ScrollAreaViewport,
            ScrollAreaScrollbar: ScrollAreaScrollbar,
            ScrollAreaThumb: ScrollAreaThumb,
            DropdownMenuRoot: DropdownMenuRoot,
            DropdownMenuTrigger: DropdownMenuTrigger,
            DropdownMenuContent: DropdownMenuContent,
            DropdownMenuItem: DropdownMenuItem,
            DropdownMenuPortal: DropdownMenuPortal,
            MessageListItem: MessageListItem,
            SearchBar: SearchBar,
            Dialog: Dialog,
            Button: Button,
            store: store,
            showTrashConfirm: showTrashConfirm,
            bulkSelectMode: bulkSelectMode,
            selectedIds: selectedIds,
            isBulkLoading: isBulkLoading,
            folderColor: folderColor,
            displayMessages: displayMessages,
            otherFolders: otherFolders,
            hasSelection: hasSelection,
            allSelected: allSelected,
            toggleSort: toggleSort,
            toggleBulkSelect: toggleBulkSelect,
            toggleSelectAll: toggleSelectAll,
            selectMessage: selectMessage,
            emptyTrash: emptyTrash,
            performEmptyTrash: performEmptyTrash,
            bulkMoveToTrash: bulkMoveToTrash,
            bulkMoveToFolder: bulkMoveToFolder,
        };
    },
    props: {
        hideTitle: { type: Boolean, default: false },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        hideTitle: { type: Boolean, default: false },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MessageList.vue.js.map