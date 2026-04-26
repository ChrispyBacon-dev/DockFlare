/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed, ref } from 'vue';
import { Inbox, FileText, Send, Trash2, AlertCircle, Archive, Folder, FolderOpen, FolderPlus, } from 'lucide-vue-next';
import { TooltipRoot, TooltipTrigger, TooltipContent, TooltipPortal } from 'radix-vue';
import { cn } from '../../lib/utils';
import { useMailStore } from '../../stores/mail';
import { mailApi } from '../../api/mail';
const __VLS_props = defineProps({
    isCollapsed: { type: Boolean, default: false },
});
const store = useMailStore();
const iconMap = {
    Inbox, Drafts: FileText, Sent: Send,
    Trash: Trash2, Spam: AlertCircle, Junk: AlertCircle,
    Archive,
};
const PALETTE = [
    '#ef4444', '#f97316', '#eab308', '#22c55e',
    '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6',
];
const getIcon = (name, active = false) => iconMap[name] || (active ? FolderOpen : Folder);
const systemFolders = computed(() => store.folders.filter((f) => f.system_folder));
const customFolders = computed(() => store.folders.filter((f) => !f.system_folder));
const selectFolder = (name) => {
    store.currentFolder = name;
    store.currentMessage = null;
    store.viewMode = 'split';
};
// ── New folder creation ──────────────────────────────────────────────
const showNewFolder = ref(false);
const newFolderName = ref('');
const newFolderColor = ref('');
const creatingFolder = ref(false);
const startNewFolder = () => {
    newFolderName.value = '';
    newFolderColor.value = '';
    showNewFolder.value = true;
};
const cancelNewFolder = () => {
    showNewFolder.value = false;
};
const confirmNewFolder = async () => {
    const name = newFolderName.value.trim();
    if (!name || !store.currentMailbox)
        return;
    creatingFolder.value = true;
    try {
        await mailApi.createFolder(store.currentMailbox, name, newFolderColor.value || undefined);
        const res = await mailApi.getFolders(store.currentMailbox);
        store.folders = res.data;
        showNewFolder.value = false;
    }
    catch {
        store.showToast('Failed to create folder');
    }
    finally {
        creatingFolder.value = false;
    }
};
// ── Folder delete ────────────────────────────────────────────────────
const deleteFolder = async (f) => {
    if (!store.currentMailbox)
        return;
    if (!confirm(`Delete folder "${f.name}"? All messages inside will be deleted.`))
        return;
    try {
        await mailApi.deleteFolder(store.currentMailbox, f.id);
        const res = await mailApi.getFolders(store.currentMailbox);
        store.folders = res.data;
        if (store.currentFolder === f.name) {
            store.currentFolder = store.folders[0]?.name || '';
        }
    }
    catch {
        store.showToast('Failed to delete folder');
    }
};
// ── Folder rename / colour edit ──────────────────────────────────────
const editingFolder = ref(null);
const editName = ref('');
const editColor = ref('');
const startEdit = (f) => {
    editingFolder.value = f;
    editName.value = f.name;
    editColor.value = f.color || '';
};
const cancelEdit = () => {
    editingFolder.value = null;
};
const confirmEdit = async () => {
    if (!editingFolder.value || !store.currentMailbox)
        return;
    const name = editName.value.trim();
    if (!name)
        return;
    try {
        await mailApi.renameFolder(store.currentMailbox, editingFolder.value.id, name, editColor.value || undefined);
        const res = await mailApi.getFolders(store.currentMailbox);
        store.folders = res.data;
        if (store.currentFolder === editingFolder.value.name && name !== editingFolder.value.name) {
            store.currentFolder = name;
        }
        editingFolder.value = null;
    }
    catch {
        store.showToast('Failed to rename folder');
    }
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    'data-collapsed': (__VLS_ctx.isCollapsed),
    ...{ class: "group flex flex-1 flex-col justify-between py-2 overflow-y-auto" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({
    ...{ class: "grid gap-1 px-2 group-[[data-collapsed=true]]:justify-center group-[[data-collapsed=true]]:px-2" },
});
if (!__VLS_ctx.isCollapsed && __VLS_ctx.systemFolders.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 select-none" },
    });
}
for (const [f] of __VLS_getVForSourceType(((__VLS_ctx.isCollapsed ? __VLS_ctx.store.folders : __VLS_ctx.systemFolders)))) {
    (f.name + '-sys');
    if (__VLS_ctx.isCollapsed) {
        const __VLS_0 = {}.TooltipRoot;
        /** @type {[typeof __VLS_components.TooltipRoot, typeof __VLS_components.TooltipRoot, ]} */ ;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
            delayDuration: (0),
        }));
        const __VLS_2 = __VLS_1({
            delayDuration: (0),
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        __VLS_3.slots.default;
        const __VLS_4 = {}.TooltipTrigger;
        /** @type {[typeof __VLS_components.TooltipTrigger, typeof __VLS_components.TooltipTrigger, ]} */ ;
        // @ts-ignore
        const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
            asChild: true,
        }));
        const __VLS_6 = __VLS_5({
            asChild: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_5));
        __VLS_7.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.isCollapsed))
                        return;
                    __VLS_ctx.selectFolder(f.name);
                } },
            ...{ class: (__VLS_ctx.cn('inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground', __VLS_ctx.store.currentFolder === f.name
                    ? 'df-folder-active'
                    : 'text-muted-foreground')) },
        });
        const __VLS_8 = ((__VLS_ctx.getIcon(f.name, __VLS_ctx.store.currentFolder === f.name)));
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
            ...{ class: "size-4" },
            ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
        }));
        const __VLS_10 = __VLS_9({
            ...{ class: "size-4" },
            ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
        }, ...__VLS_functionalComponentArgsRest(__VLS_9));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "sr-only" },
        });
        (f.name);
        var __VLS_7;
        const __VLS_12 = {}.TooltipPortal;
        /** @type {[typeof __VLS_components.TooltipPortal, typeof __VLS_components.TooltipPortal, ]} */ ;
        // @ts-ignore
        const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({}));
        const __VLS_14 = __VLS_13({}, ...__VLS_functionalComponentArgsRest(__VLS_13));
        __VLS_15.slots.default;
        const __VLS_16 = {}.TooltipContent;
        /** @type {[typeof __VLS_components.TooltipContent, typeof __VLS_components.TooltipContent, ]} */ ;
        // @ts-ignore
        const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md flex items-center gap-4" },
        }));
        const __VLS_18 = __VLS_17({
            side: "right",
            ...{ class: "z-50 rounded-md border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md flex items-center gap-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_17));
        __VLS_19.slots.default;
        (f.name);
        if (f.total_count > 0) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "ml-auto text-muted-foreground flex gap-1" },
            });
            if (f.unread_count) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "font-bold" },
                });
                (f.unread_count);
            }
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (f.total_count);
        }
        var __VLS_19;
        var __VLS_15;
        var __VLS_3;
    }
    else if (__VLS_ctx.editingFolder?.id === f.id) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "rounded-md border bg-muted p-2 flex flex-col gap-2" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
            ...{ onKeyup: (__VLS_ctx.confirmEdit) },
            ...{ onKeyup: (__VLS_ctx.cancelEdit) },
            ...{ class: "w-full rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring" },
            autofocus: true,
        });
        (__VLS_ctx.editName);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex gap-1 flex-wrap" },
        });
        for (const [c] of __VLS_getVForSourceType((__VLS_ctx.PALETTE))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.isCollapsed))
                            return;
                        if (!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        __VLS_ctx.editColor = __VLS_ctx.editColor === c ? '' : c;
                    } },
                key: (c),
                ...{ class: "h-5 w-5 rounded-full border-2 transition-transform hover:scale-110" },
                ...{ style: (`background:${c}; border-color:${__VLS_ctx.editColor === c ? '#000' : 'transparent'}`) },
            });
        }
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isCollapsed))
                        return;
                    if (!(__VLS_ctx.editingFolder?.id === f.id))
                        return;
                    __VLS_ctx.editColor = '';
                } },
            ...{ class: "h-5 w-5 rounded-full border-2 text-xs flex items-center justify-center text-muted-foreground hover:bg-accent" },
            ...{ style: (`border-color:${!__VLS_ctx.editColor ? '#888' : 'transparent'}`) },
            title: "No colour",
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex gap-1 justify-end" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.cancelEdit) },
            ...{ class: "text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.confirmEdit) },
            ...{ class: "text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90" },
        });
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: (__VLS_ctx.cn('group/row relative flex items-center rounded-lg text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground', __VLS_ctx.store.currentFolder === f.name
                    ? 'df-folder-active'
                    : 'transparent')) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isCollapsed))
                        return;
                    if (!!(__VLS_ctx.editingFolder?.id === f.id))
                        return;
                    __VLS_ctx.selectFolder(f.name);
                } },
            ...{ class: "flex flex-1 items-center gap-3 px-3 py-2 text-left min-w-0" },
        });
        const __VLS_20 = ((__VLS_ctx.getIcon(f.name, __VLS_ctx.store.currentFolder === f.name)));
        // @ts-ignore
        const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
            ...{ class: "size-4 flex-shrink-0" },
            ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
        }));
        const __VLS_22 = __VLS_21({
            ...{ class: "size-4 flex-shrink-0" },
            ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
        }, ...__VLS_functionalComponentArgsRest(__VLS_21));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "truncate" },
        });
        (f.name);
        if (f.total_count > 0) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: (__VLS_ctx.cn('ml-auto text-xs flex-shrink-0 flex gap-1', __VLS_ctx.store.currentFolder === f.name ? 'opacity-90' : 'text-muted-foreground')) },
            });
            if (f.unread_count) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "rounded-full px-1.5 py-0.5 text-[10.5px] font-bold leading-none flex items-center" },
                    ...{ style: {} },
                });
                (f.unread_count);
            }
            if (!f.unread_count) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (f.total_count);
            }
        }
        if (!f.system_folder) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: (__VLS_ctx.cn('absolute right-1 flex gap-0.5 opacity-0 group-hover/row:opacity-100 [@media(hover:none)]:opacity-100 transition-opacity rounded px-0.5', __VLS_ctx.store.currentFolder === f.name ? 'bg-primary' : 'bg-accent')) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.isCollapsed))
                            return;
                        if (!!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        if (!(!f.system_folder))
                            return;
                        __VLS_ctx.startEdit(f);
                    } },
                ...{ class: "p-1 rounded hover:bg-accent/80" },
                title: "Rename / recolour",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
                ...{ class: "size-3" },
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                'stroke-width': "2",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
                d: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
                d: "M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.isCollapsed))
                            return;
                        if (!!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        if (!(!f.system_folder))
                            return;
                        __VLS_ctx.deleteFolder(f);
                    } },
                ...{ class: "p-1 rounded hover:text-destructive" },
                title: "Delete folder",
            });
            const __VLS_24 = {}.Trash2;
            /** @type {[typeof __VLS_components.Trash2, ]} */ ;
            // @ts-ignore
            const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
                ...{ class: "size-3" },
            }));
            const __VLS_26 = __VLS_25({
                ...{ class: "size-3" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_25));
        }
    }
}
if (!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length) {
    for (const [f] of __VLS_getVForSourceType((__VLS_ctx.customFolders))) {
        (f.name + '-custom');
        if (__VLS_ctx.editingFolder?.id === f.id) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "rounded-md border bg-muted p-2 flex flex-col gap-2" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
                ...{ onKeyup: (__VLS_ctx.confirmEdit) },
                ...{ onKeyup: (__VLS_ctx.cancelEdit) },
                ...{ class: "w-full rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring" },
                autofocus: true,
            });
            (__VLS_ctx.editName);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "flex gap-1 flex-wrap" },
            });
            for (const [c] of __VLS_getVForSourceType((__VLS_ctx.PALETTE))) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!(!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length))
                                return;
                            if (!(__VLS_ctx.editingFolder?.id === f.id))
                                return;
                            __VLS_ctx.editColor = __VLS_ctx.editColor === c ? '' : c;
                        } },
                    key: (c),
                    ...{ class: "h-5 w-5 rounded-full border-2 transition-transform hover:scale-110" },
                    ...{ style: (`background:${c}; border-color:${__VLS_ctx.editColor === c ? '#000' : 'transparent'}`) },
                });
            }
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length))
                            return;
                        if (!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        __VLS_ctx.editColor = '';
                    } },
                ...{ class: "h-5 w-5 rounded-full border-2 text-xs flex items-center justify-center text-muted-foreground hover:bg-accent" },
                ...{ style: (`border-color:${!__VLS_ctx.editColor ? '#888' : 'transparent'}`) },
                title: "No colour",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "flex gap-1 justify-end" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (__VLS_ctx.cancelEdit) },
                ...{ class: "text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (__VLS_ctx.confirmEdit) },
                ...{ class: "text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90" },
            });
        }
        else {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: (__VLS_ctx.cn('group/row relative flex items-center rounded-lg text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground', __VLS_ctx.store.currentFolder === f.name ? 'df-folder-active' : 'transparent')) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length))
                            return;
                        if (!!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        __VLS_ctx.selectFolder(f.name);
                    } },
                ...{ class: "flex flex-1 items-center gap-3 px-3 py-2 text-left min-w-0" },
            });
            const __VLS_28 = ((__VLS_ctx.getIcon(f.name, __VLS_ctx.store.currentFolder === f.name)));
            // @ts-ignore
            const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
                ...{ class: "size-4 flex-shrink-0" },
                ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
            }));
            const __VLS_30 = __VLS_29({
                ...{ class: "size-4 flex-shrink-0" },
                ...{ style: (f.color && __VLS_ctx.store.currentFolder !== f.name ? `color:${f.color}` : '') },
            }, ...__VLS_functionalComponentArgsRest(__VLS_29));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "truncate" },
            });
            (f.name);
            if (f.total_count > 0) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: (__VLS_ctx.cn('ml-auto text-xs flex-shrink-0 flex gap-1', __VLS_ctx.store.currentFolder === f.name ? 'opacity-90' : 'text-muted-foreground')) },
                });
                if (f.unread_count) {
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                        ...{ class: "rounded-full px-1.5 py-0.5 text-[10.5px] font-bold leading-none flex items-center" },
                        ...{ style: {} },
                    });
                    (f.unread_count);
                }
                if (!f.unread_count) {
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                    (f.total_count);
                }
            }
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: (__VLS_ctx.cn('absolute right-1 flex gap-0.5 opacity-0 group-hover/row:opacity-100 transition-opacity rounded px-0.5', __VLS_ctx.store.currentFolder === f.name ? 'bg-primary' : 'bg-accent')) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length))
                            return;
                        if (!!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        __VLS_ctx.startEdit(f);
                    } },
                ...{ class: "p-1 rounded hover:bg-accent/80" },
                title: "Rename / recolour",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
                ...{ class: "size-3" },
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                'stroke-width': "2",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
                d: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
                d: "M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z",
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(!__VLS_ctx.isCollapsed && __VLS_ctx.customFolders.length))
                            return;
                        if (!!(__VLS_ctx.editingFolder?.id === f.id))
                            return;
                        __VLS_ctx.deleteFolder(f);
                    } },
                ...{ class: "p-1 rounded hover:text-destructive" },
                title: "Delete folder",
            });
            const __VLS_32 = {}.Trash2;
            /** @type {[typeof __VLS_components.Trash2, ]} */ ;
            // @ts-ignore
            const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
                ...{ class: "size-3" },
            }));
            const __VLS_34 = __VLS_33({
                ...{ class: "size-3" },
            }, ...__VLS_functionalComponentArgsRest(__VLS_33));
        }
    }
}
if (__VLS_ctx.showNewFolder && !__VLS_ctx.isCollapsed) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "rounded-md border bg-muted p-2 flex flex-col gap-2 mt-1" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        ...{ onKeyup: (__VLS_ctx.confirmNewFolder) },
        ...{ onKeyup: (__VLS_ctx.cancelNewFolder) },
        placeholder: "Folder name",
        ...{ class: "w-full rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring" },
        autofocus: true,
    });
    (__VLS_ctx.newFolderName);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex gap-1 flex-wrap" },
    });
    for (const [c] of __VLS_getVForSourceType((__VLS_ctx.PALETTE))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.showNewFolder && !__VLS_ctx.isCollapsed))
                        return;
                    __VLS_ctx.newFolderColor = __VLS_ctx.newFolderColor === c ? '' : c;
                } },
            key: (c),
            ...{ class: "h-5 w-5 rounded-full border-2 transition-transform hover:scale-110" },
            ...{ style: (`background:${c}; border-color:${__VLS_ctx.newFolderColor === c ? '#000' : 'transparent'}`) },
        });
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.showNewFolder && !__VLS_ctx.isCollapsed))
                    return;
                __VLS_ctx.newFolderColor = '';
            } },
        ...{ class: "h-5 w-5 rounded-full border-2 text-xs flex items-center justify-center text-muted-foreground hover:bg-accent" },
        ...{ style: (`border-color:${!__VLS_ctx.newFolderColor ? '#888' : 'transparent'}`) },
        title: "No colour",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex gap-1 justify-end" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.cancelNewFolder) },
        ...{ class: "text-xs px-2 py-1 rounded hover:bg-accent text-muted-foreground" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.confirmNewFolder) },
        ...{ class: "text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50" },
        disabled: (__VLS_ctx.creatingFolder || !__VLS_ctx.newFolderName.trim()),
    });
    (__VLS_ctx.creatingFolder ? '…' : 'Create');
}
if (!__VLS_ctx.isCollapsed) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.startNewFolder) },
        ...{ class: "flex items-center gap-2 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors mt-1" },
    });
    const __VLS_36 = {}.FolderPlus;
    /** @type {[typeof __VLS_components.FolderPlus, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        ...{ class: "size-3" },
    }));
    const __VLS_38 = __VLS_37({
        ...{ class: "size-3" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
}
/** @type {__VLS_StyleScopedClasses['group']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-between']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['group-[[data-collapsed=true]]:justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['group-[[data-collapsed=true]]:px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pt-2']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['uppercase']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-widest']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground/60']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['sr-only']} */ ;
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
/** @type {__VLS_StyleScopedClasses['gap-4']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-1']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-transform']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:scale-110']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-end']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-left']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['py-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10.5px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/80']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-1']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-transform']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:scale-110']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-end']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-left']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['py-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10.5px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent/80']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-1']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-1']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-ring']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-transform']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:scale-110']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-end']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-primary/90']} */ ;
/** @type {__VLS_StyleScopedClasses['disabled:opacity-50']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-1']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Trash2: Trash2,
            FolderPlus: FolderPlus,
            TooltipRoot: TooltipRoot,
            TooltipTrigger: TooltipTrigger,
            TooltipContent: TooltipContent,
            TooltipPortal: TooltipPortal,
            cn: cn,
            store: store,
            PALETTE: PALETTE,
            getIcon: getIcon,
            systemFolders: systemFolders,
            customFolders: customFolders,
            selectFolder: selectFolder,
            showNewFolder: showNewFolder,
            newFolderName: newFolderName,
            newFolderColor: newFolderColor,
            creatingFolder: creatingFolder,
            startNewFolder: startNewFolder,
            cancelNewFolder: cancelNewFolder,
            confirmNewFolder: confirmNewFolder,
            deleteFolder: deleteFolder,
            editingFolder: editingFolder,
            editName: editName,
            editColor: editColor,
            startEdit: startEdit,
            cancelEdit: cancelEdit,
            confirmEdit: confirmEdit,
        };
    },
    props: {
        isCollapsed: { type: Boolean, default: false },
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: {
        isCollapsed: { type: Boolean, default: false },
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=FolderNav.vue.js.map