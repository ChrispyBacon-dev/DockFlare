/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, watch, nextTick, onUnmounted } from 'vue';
import { Paperclip, X, Bold as BoldIcon, Italic as ItalicIcon, Link2, List as ListIcon, ListOrdered, Minus, Underline as UnderlineIcon, AlignLeft as AlignLeftIcon, AlignCenter as AlignCenterIcon, AlignRight as AlignRightIcon, Quote as QuoteIcon, RemoveFormatting, Baseline, Trash2, Type, BookmarkCheck, Maximize2, Minimize2 } from 'lucide-vue-next';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import LinkExtension from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import Typography from '@tiptap/extension-typography';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Color from '@tiptap/extension-color';
import TextStyle from '@tiptap/extension-text-style';
import Highlight from '@tiptap/extension-highlight';
import FontFamily from '@tiptap/extension-font-family';
import { mailApi } from '../../api/mail';
import { useMailStore } from '../../stores/mail';
import Button from '../ui/Button.vue';
const __VLS_props = defineProps({ panelMode: { type: Boolean, default: false } });
const store = useMailStore();
const to = ref('');
const subject = ref('');
const attachments = ref([]);
const sending = ref(false);
const savingDraft = ref(false);
const savedDraft = ref(false);
const draftId = ref(null);
const error = ref('');
const minimized = ref(false);
const showFormatting = ref(false);
const quotedHtml = ref('');
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;
const editor = useEditor({
    extensions: [
        StarterKit,
        LinkExtension.configure({ openOnClick: false }),
        Placeholder.configure({ placeholder: 'Write your message…' }),
        Typography,
        Underline,
        TextAlign.configure({ types: ['heading', 'paragraph'] }),
        TextStyle,
        Color,
        Highlight.configure({ multicolor: true }),
        FontFamily,
    ],
    editorProps: {
        attributes: { class: 'tiptap-editor' },
    },
    onUpdate: ({ editor }) => {
        if (store.composeDefaults !== null) {
            store.composeDefaults = { ...store.composeDefaults, body: editor.getHTML() };
        }
        else {
            store.composeDefaults = { body: editor.getHTML() };
        }
    },
});
watch(() => store.isComposeOpen, async (open) => {
    if (open && store.composeDefaults) {
        to.value = store.composeDefaults.to || '';
        subject.value = store.composeDefaults.subject || '';
        quotedHtml.value = store.composeDefaults.quotedHtml || '';
        if (store.composeDefaults.draftId) {
            draftId.value = store.composeDefaults.draftId;
        }
        minimized.value = false;
        await nextTick();
        if (store.composeDefaults.body) {
            editor.value?.commands.setContent(store.composeDefaults.body);
        }
        else {
            editor.value?.commands.clearContent();
        }
    }
    else if (!open) {
        reset();
    }
}, { immediate: true });
watch(to, (val) => {
    if (store.composeDefaults !== null) {
        store.composeDefaults = { ...store.composeDefaults, to: val };
    }
});
watch(subject, (val) => {
    if (store.composeDefaults !== null) {
        store.composeDefaults = { ...store.composeDefaults, subject: val };
    }
});
watch(quotedHtml, (val) => {
    if (store.composeDefaults !== null) {
        store.composeDefaults = { ...store.composeDefaults, quotedHtml: val };
    }
});
onUnmounted(() => editor.value?.destroy());
const reset = () => {
    to.value = '';
    subject.value = '';
    attachments.value = [];
    error.value = '';
    minimized.value = false;
    draftId.value = null;
    savedDraft.value = false;
    quotedHtml.value = '';
    editor.value?.commands.clearContent();
    store.composeDefaults = null;
};
const close = () => {
    store.isComposeOpen = false;
    store.isComposeFullView = false;
};
const toggleFullView = () => {
    store.isComposeFullView = !store.isComposeFullView;
    minimized.value = false;
};
const discardDraft = async () => {
    if (draftId.value && store.currentMailbox) {
        try {
            await mailApi.deleteMessage(store.currentMailbox, String(draftId.value));
            const res = await mailApi.getFolders(store.currentMailbox);
            store.folders = res.data;
            if (store.currentFolder === 'Drafts') {
                store.messages = store.messages.filter((m) => m.id !== draftId.value);
            }
        }
        catch (e) { }
    }
    close();
};
const toggleMinimize = () => {
    minimized.value = !minimized.value;
};
const onFileChange = (e) => {
    const input = e.target;
    if (!input.files)
        return;
    for (const file of Array.from(input.files)) {
        if (!attachments.value.find(f => f.name === file.name && f.size === file.size)) {
            attachments.value.push(file);
        }
    }
    input.value = '';
};
const removeAttachment = (index) => {
    attachments.value.splice(index, 1);
};
const formatBytes = (bytes) => {
    if (bytes < 1024)
        return `${bytes} B`;
    if (bytes < 1024 * 1024)
        return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};
const setLink = () => {
    const prev = editor.value?.getAttributes('link').href || '';
    const url = window.prompt('Enter URL', prev);
    if (url === null)
        return;
    if (url === '') {
        editor.value?.chain().focus().unsetLink().run();
    }
    else {
        editor.value?.chain().focus().setLink({ href: url }).run();
    }
};
const saveDraft = async () => {
    if (!store.currentMailbox || !editor.value)
        return;
    savingDraft.value = true;
    error.value = '';
    try {
        const payload = {
            to: to.value ? to.value.split(',').map((s) => s.trim()).filter(Boolean) : [],
            subject: subject.value,
            html_body: editor.value.getHTML() + (quotedHtml.value || ''),
            text_body: editor.value.getText(),
        };
        if (draftId.value) {
            await mailApi.updateDraft(store.currentMailbox, draftId.value, payload);
        }
        else {
            const res = await mailApi.createDraft(store.currentMailbox, payload);
            draftId.value = res.data.id;
        }
        savedDraft.value = true;
        setTimeout(() => { savedDraft.value = false; }, 2000);
        const res = await mailApi.getFolders(store.currentMailbox);
        store.folders = res.data;
    }
    catch (e) {
        error.value = e?.response?.data?.error || 'Failed to save draft.';
    }
    finally {
        savingDraft.value = false;
    }
};
const send = async () => {
    if (!store.currentMailbox || !editor.value)
        return;
    const totalSize = attachments.value.reduce((sum, f) => sum + f.size, 0);
    if (totalSize > MAX_ATTACHMENT_BYTES) {
        error.value = `Attachments exceed 10 MB limit (${formatBytes(totalSize)} total).`;
        return;
    }
    sending.value = true;
    error.value = '';
    try {
        const html = editor.value.getHTML() + (quotedHtml.value || '');
        const text = editor.value.getText();
        const formData = new FormData();
        formData.append('to', to.value);
        formData.append('subject', subject.value);
        formData.append('html', html);
        formData.append('text', text);
        for (const file of attachments.value) {
            formData.append('attachments', file);
        }
        await mailApi.sendMessage(store.currentMailbox, formData);
        const fRes = await mailApi.getFolders(store.currentMailbox);
        store.folders = fRes.data;
        close();
    }
    catch (e) {
        error.value = e?.response?.data?.error || 'Failed to send. Please try again.';
    }
    finally {
        sending.value = false;
    }
};
const fonts = [
    { label: 'Sans Serif', value: 'Inter, ui-sans-serif, system-ui, sans-serif' },
    { label: 'Serif', value: 'ui-serif, Georgia, serif' },
    { label: 'Monospace', value: 'ui-monospace, Consolas, monospace' },
    { label: 'Comic Sans', value: '"Comic Sans MS", "Comic Sans", cursive' },
    { label: 'Garamond', value: 'Garamond, serif' },
    { label: 'Trebuchet', value: '"Trebuchet MS", sans-serif' },
];
const setFont = (e) => {
    const target = e.target;
    if (target.value) {
        editor.value?.chain().focus().setFontFamily(target.value).run();
    }
    else {
        editor.value?.chain().focus().unsetFontFamily().run();
    }
};
const setColor = (e) => {
    const target = e.target;
    editor.value?.chain().focus().setColor(target.value).run();
};
const setHighlight = (e) => {
    const target = e.target;
    editor.value?.chain().focus().setHighlight({ color: target.value }).run();
};
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
if (__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.panelMode
                ? 'flex flex-col h-full w-full bg-background'
                : 'fixed bottom-0 right-6 z-50 flex flex-col rounded-t-xl shadow-2xl border border-border bg-background') },
        ...{ style: (!__VLS_ctx.panelMode ? (__VLS_ctx.minimized ? 'width:320px' : 'width:560px') : '') },
    });
    if (__VLS_ctx.panelMode) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-[52px] flex items-center gap-2 px-4 border-b border-border flex-shrink-0" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "flex-1 text-base font-semibold truncate" },
        });
        (__VLS_ctx.subject || 'New Message');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.toggleFullView) },
            type: "button",
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
            title: "Pop out",
        });
        const __VLS_0 = {}.Minimize2;
        /** @type {[typeof __VLS_components.Minimize2, ]} */ ;
        // @ts-ignore
        const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
            ...{ class: "size-4" },
        }));
        const __VLS_2 = __VLS_1({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_1));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.close) },
            type: "button",
            ...{ class: "inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" },
            title: "Close",
        });
        const __VLS_4 = {}.X;
        /** @type {[typeof __VLS_components.X, ]} */ ;
        // @ts-ignore
        const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
            ...{ class: "size-4" },
        }));
        const __VLS_6 = __VLS_5({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_5));
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ onClick: (__VLS_ctx.toggleMinimize) },
            ...{ class: "flex items-center gap-2 rounded-t-xl bg-primary px-4 py-2.5 cursor-pointer select-none" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "flex-1 text-sm font-semibold text-primary-foreground truncate" },
        });
        (__VLS_ctx.subject || 'New Message');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.toggleFullView) },
            type: "button",
            ...{ class: "rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" },
            title: "Full view",
        });
        const __VLS_8 = {}.Maximize2;
        /** @type {[typeof __VLS_components.Maximize2, ]} */ ;
        // @ts-ignore
        const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
            ...{ class: "size-4" },
        }));
        const __VLS_10 = __VLS_9({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_9));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.toggleMinimize) },
            type: "button",
            ...{ class: "rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" },
            title: "Minimize",
        });
        const __VLS_12 = {}.Minus;
        /** @type {[typeof __VLS_components.Minus, ]} */ ;
        // @ts-ignore
        const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
            ...{ class: "size-4" },
        }));
        const __VLS_14 = __VLS_13({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_13));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.close) },
            type: "button",
            ...{ class: "rounded p-0.5 text-primary-foreground/70 hover:text-primary-foreground hover:bg-white/10 transition-colors" },
            title: "Close",
        });
        const __VLS_16 = {}.X;
        /** @type {[typeof __VLS_components.X, ]} */ ;
        // @ts-ignore
        const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
            ...{ class: "size-4" },
        }));
        const __VLS_18 = __VLS_17({
            ...{ class: "size-4" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: (__VLS_ctx.panelMode ? 'flex flex-col flex-1 overflow-hidden' : 'flex flex-col flex-1 overflow-hidden max-h-[80vh]') },
    });
    __VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.panelMode || !__VLS_ctx.minimized) }, null, null);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex flex-col border-b border-border flex-shrink-0" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        placeholder: "To",
        ...{ class: "w-full border-b border-border px-4 py-2 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none" },
    });
    (__VLS_ctx.to);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        placeholder: "Subject",
        ...{ class: "w-full px-4 py-2 text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none" },
    });
    (__VLS_ctx.subject);
    const __VLS_20 = {}.EditorContent;
    /** @type {[typeof __VLS_components.EditorContent, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        editor: (__VLS_ctx.editor),
        ...{ class: "compose-editor flex-1" },
    }));
    const __VLS_22 = __VLS_21({
        editor: (__VLS_ctx.editor),
        ...{ class: "compose-editor flex-1" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    if (__VLS_ctx.attachments.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex flex-wrap gap-1.5 border-t border-border px-4 py-2 bg-muted/30 flex-shrink-0" },
        });
        for (const [file, i] of __VLS_getVForSourceType((__VLS_ctx.attachments))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (i),
                ...{ class: "flex items-center gap-1 bg-muted text-muted-foreground text-xs rounded px-2 py-1 border border-border" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "truncate max-w-[140px]" },
            });
            (file.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "text-muted-foreground/60" },
            });
            (__VLS_ctx.formatBytes(file.size));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                            return;
                        if (!(__VLS_ctx.attachments.length))
                            return;
                        __VLS_ctx.removeAttachment(i);
                    } },
                type: "button",
                ...{ class: "ml-1 hover:text-destructive" },
            });
            const __VLS_24 = {}.X;
            /** @type {[typeof __VLS_components.X, ]} */ ;
            // @ts-ignore
            const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
                size: (12),
            }));
            const __VLS_26 = __VLS_25({
                size: (12),
            }, ...__VLS_functionalComponentArgsRest(__VLS_25));
        }
    }
    if (__VLS_ctx.quotedHtml) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "border-t border-border px-4 py-1.5 text-xs text-muted-foreground flex-shrink-0 select-none" },
        });
    }
    if (__VLS_ctx.error) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "px-4 py-1 text-xs text-red-500 flex-shrink-0" },
        });
        (__VLS_ctx.error);
    }
    if (__VLS_ctx.showFormatting) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex flex-wrap items-center gap-1 border-t border-border bg-muted/30 px-3 py-1.5 flex-shrink-0" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.select, __VLS_intrinsicElements.select)({
            ...{ onChange: (__VLS_ctx.setFont) },
            ...{ class: "text-xs bg-transparent border-none focus:ring-0 text-foreground cursor-pointer mr-1 max-w-[100px]" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
            value: "",
        });
        for (const [font] of __VLS_getVForSourceType((__VLS_ctx.fonts))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.option, __VLS_intrinsicElements.option)({
                key: (font.value),
                value: (font.value),
            });
            (font.label);
        }
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "mx-1 h-4 w-px bg-border" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleBold().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('bold') ? 'bg-accent' : '') },
            title: "Bold",
        });
        const __VLS_28 = {}.BoldIcon;
        /** @type {[typeof __VLS_components.BoldIcon, ]} */ ;
        // @ts-ignore
        const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
            ...{ class: "size-3.5" },
        }));
        const __VLS_30 = __VLS_29({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_29));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleItalic().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('italic') ? 'bg-accent' : '') },
            title: "Italic",
        });
        const __VLS_32 = {}.ItalicIcon;
        /** @type {[typeof __VLS_components.ItalicIcon, ]} */ ;
        // @ts-ignore
        const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
            ...{ class: "size-3.5" },
        }));
        const __VLS_34 = __VLS_33({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_33));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleUnderline().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('underline') ? 'bg-accent' : '') },
            title: "Underline",
        });
        const __VLS_36 = {}.UnderlineIcon;
        /** @type {[typeof __VLS_components.UnderlineIcon, ]} */ ;
        // @ts-ignore
        const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
            ...{ class: "size-3.5" },
        }));
        const __VLS_38 = __VLS_37({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_37));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "mx-1 h-4 w-px bg-border" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "relative group flex items-center p-1 rounded hover:bg-accent cursor-pointer" },
            title: "Text Color",
        });
        const __VLS_40 = {}.Baseline;
        /** @type {[typeof __VLS_components.Baseline, ]} */ ;
        // @ts-ignore
        const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
            ...{ class: "size-3.5 text-foreground" },
        }));
        const __VLS_42 = __VLS_41({
            ...{ class: "size-3.5 text-foreground" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_41));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
            ...{ onInput: (__VLS_ctx.setColor) },
            type: "color",
            ...{ class: "absolute inset-0 opacity-0 cursor-pointer w-full h-full" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "relative flex items-center p-1 rounded hover:bg-accent cursor-pointer" },
            title: "Background Color",
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-xs font-bold leading-none bg-foreground text-background px-0.5 rounded-sm" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
            ...{ onInput: (__VLS_ctx.setHighlight) },
            type: "color",
            ...{ class: "absolute inset-0 opacity-0 cursor-pointer w-full h-full" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "mx-1 h-4 w-px bg-border" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().setTextAlign('left').run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive({ textAlign: 'left' }) ? 'bg-accent' : '') },
            title: "Align left",
        });
        const __VLS_44 = {}.AlignLeftIcon;
        /** @type {[typeof __VLS_components.AlignLeftIcon, ]} */ ;
        // @ts-ignore
        const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
            ...{ class: "size-3.5" },
        }));
        const __VLS_46 = __VLS_45({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_45));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().setTextAlign('center').run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive({ textAlign: 'center' }) ? 'bg-accent' : '') },
            title: "Align center",
        });
        const __VLS_48 = {}.AlignCenterIcon;
        /** @type {[typeof __VLS_components.AlignCenterIcon, ]} */ ;
        // @ts-ignore
        const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
            ...{ class: "size-3.5" },
        }));
        const __VLS_50 = __VLS_49({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_49));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().setTextAlign('right').run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive({ textAlign: 'right' }) ? 'bg-accent' : '') },
            title: "Align right",
        });
        const __VLS_52 = {}.AlignRightIcon;
        /** @type {[typeof __VLS_components.AlignRightIcon, ]} */ ;
        // @ts-ignore
        const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
            ...{ class: "size-3.5" },
        }));
        const __VLS_54 = __VLS_53({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_53));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "mx-1 h-4 w-px bg-border" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleBulletList().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('bulletList') ? 'bg-accent' : '') },
            title: "Bullet list",
        });
        const __VLS_56 = {}.ListIcon;
        /** @type {[typeof __VLS_components.ListIcon, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            ...{ class: "size-3.5" },
        }));
        const __VLS_58 = __VLS_57({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleOrderedList().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('orderedList') ? 'bg-accent' : '') },
            title: "Ordered list",
        });
        const __VLS_60 = {}.ListOrdered;
        /** @type {[typeof __VLS_components.ListOrdered, ]} */ ;
        // @ts-ignore
        const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
            ...{ class: "size-3.5" },
        }));
        const __VLS_62 = __VLS_61({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_61));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().toggleBlockquote().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            ...{ class: (__VLS_ctx.editor?.isActive('blockquote') ? 'bg-accent' : '') },
            title: "Quote",
        });
        const __VLS_64 = {}.QuoteIcon;
        /** @type {[typeof __VLS_components.QuoteIcon, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            ...{ class: "size-3.5" },
        }));
        const __VLS_66 = __VLS_65({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ class: "mx-1 h-4 w-px bg-border" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                        return;
                    if (!(__VLS_ctx.showFormatting))
                        return;
                    __VLS_ctx.editor?.chain().focus().unsetAllMarks().clearNodes().run();
                } },
            type: "button",
            ...{ class: "rounded p-1 hover:bg-accent transition-colors" },
            title: "Remove formatting",
        });
        const __VLS_68 = {}.RemoveFormatting;
        /** @type {[typeof __VLS_components.RemoveFormatting, ]} */ ;
        // @ts-ignore
        const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
            ...{ class: "size-3.5" },
        }));
        const __VLS_70 = __VLS_69({
            ...{ class: "size-3.5" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center justify-between gap-2 border-t border-border px-4 py-2.5 flex-shrink-0 bg-background" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex items-center gap-1" },
    });
    /** @type {[typeof Button, typeof Button, ]} */ ;
    // @ts-ignore
    const __VLS_72 = __VLS_asFunctionalComponent(Button, new Button({
        ...{ 'onClick': {} },
        as: "button",
        type: "button",
        size: "sm",
        ...{ class: "rounded-full px-5 font-semibold tracking-wide" },
        disabled: (__VLS_ctx.sending || !__VLS_ctx.to),
    }));
    const __VLS_73 = __VLS_72({
        ...{ 'onClick': {} },
        as: "button",
        type: "button",
        size: "sm",
        ...{ class: "rounded-full px-5 font-semibold tracking-wide" },
        disabled: (__VLS_ctx.sending || !__VLS_ctx.to),
    }, ...__VLS_functionalComponentArgsRest(__VLS_72));
    let __VLS_75;
    let __VLS_76;
    let __VLS_77;
    const __VLS_78 = {
        onClick: (__VLS_ctx.send)
    };
    __VLS_74.slots.default;
    (__VLS_ctx.sending ? 'Sending…' : 'Send');
    var __VLS_74;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.saveDraft) },
        type: "button",
        ...{ class: "ml-1 rounded p-1.5 transition-colors" },
        ...{ class: (__VLS_ctx.savedDraft ? 'text-green-500' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground') },
        disabled: (__VLS_ctx.savingDraft),
        title: "Save draft",
    });
    const __VLS_79 = {}.BookmarkCheck;
    /** @type {[typeof __VLS_components.BookmarkCheck, ]} */ ;
    // @ts-ignore
    const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
        ...{ class: "size-4" },
    }));
    const __VLS_81 = __VLS_80({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_80));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!(__VLS_ctx.store.isComposeOpen && (__VLS_ctx.panelMode || !__VLS_ctx.store.isComposeFullView)))
                    return;
                __VLS_ctx.showFormatting = !__VLS_ctx.showFormatting;
            } },
        type: "button",
        ...{ class: "ml-1 rounded p-1.5 hover:bg-accent transition-colors" },
        ...{ class: (__VLS_ctx.showFormatting ? 'bg-accent text-accent-foreground' : 'text-muted-foreground') },
        title: "Formatting options",
    });
    const __VLS_83 = {}.Type;
    /** @type {[typeof __VLS_components.Type, ]} */ ;
    // @ts-ignore
    const __VLS_84 = __VLS_asFunctionalComponent(__VLS_83, new __VLS_83({
        ...{ class: "size-4" },
    }));
    const __VLS_85 = __VLS_84({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_84));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
        title: "Attach files",
    });
    const __VLS_87 = {}.Paperclip;
    /** @type {[typeof __VLS_components.Paperclip, ]} */ ;
    // @ts-ignore
    const __VLS_88 = __VLS_asFunctionalComponent(__VLS_87, new __VLS_87({
        ...{ class: "size-4" },
    }));
    const __VLS_89 = __VLS_88({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_88));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
        ...{ onChange: (__VLS_ctx.onFileChange) },
        type: "file",
        multiple: true,
        ...{ class: "hidden" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.setLink) },
        type: "button",
        ...{ class: "rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors" },
        title: "Insert link",
    });
    const __VLS_91 = {}.Link2;
    /** @type {[typeof __VLS_components.Link2, ]} */ ;
    // @ts-ignore
    const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
        ...{ class: "size-4" },
    }));
    const __VLS_93 = __VLS_92({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_92));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.discardDraft) },
        type: "button",
        ...{ class: "rounded p-1.5 text-muted-foreground hover:bg-accent hover:text-destructive transition-colors" },
        title: (__VLS_ctx.draftId ? 'Delete draft' : 'Discard'),
    });
    const __VLS_95 = {}.Trash2;
    /** @type {[typeof __VLS_components.Trash2, ]} */ ;
    // @ts-ignore
    const __VLS_96 = __VLS_asFunctionalComponent(__VLS_95, new __VLS_95({
        ...{ class: "size-4" },
    }));
    const __VLS_97 = __VLS_96({
        ...{ class: "size-4" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_96));
}
/** @type {__VLS_StyleScopedClasses['h-[52px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-base']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
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
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-t-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground/70']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-white/10']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground/70']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-white/10']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-foreground/70']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-white/10']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['placeholder:text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['placeholder:text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:outline-none']} */ ;
/** @type {__VLS_StyleScopedClasses['compose-editor']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted/30']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['max-w-[140px]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground/60']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-red-500']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted/30']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['py-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['border-none']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-1']} */ ;
/** @type {__VLS_StyleScopedClasses['max-w-[100px]']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['group']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['absolute']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['opacity-0']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['leading-none']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-background']} */ ;
/** @type {__VLS_StyleScopedClasses['px-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['absolute']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['opacity-0']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['mx-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-px']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-border']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-3.5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-between']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-2.5']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['px-5']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-wide']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-1']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['cursor-pointer']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-accent-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['p-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-accent']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-destructive']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-colors']} */ ;
/** @type {__VLS_StyleScopedClasses['size-4']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Paperclip: Paperclip,
            X: X,
            BoldIcon: BoldIcon,
            ItalicIcon: ItalicIcon,
            Link2: Link2,
            ListIcon: ListIcon,
            ListOrdered: ListOrdered,
            Minus: Minus,
            UnderlineIcon: UnderlineIcon,
            AlignLeftIcon: AlignLeftIcon,
            AlignCenterIcon: AlignCenterIcon,
            AlignRightIcon: AlignRightIcon,
            QuoteIcon: QuoteIcon,
            RemoveFormatting: RemoveFormatting,
            Baseline: Baseline,
            Trash2: Trash2,
            Type: Type,
            BookmarkCheck: BookmarkCheck,
            Maximize2: Maximize2,
            Minimize2: Minimize2,
            EditorContent: EditorContent,
            Button: Button,
            store: store,
            to: to,
            subject: subject,
            attachments: attachments,
            sending: sending,
            savingDraft: savingDraft,
            savedDraft: savedDraft,
            draftId: draftId,
            error: error,
            minimized: minimized,
            showFormatting: showFormatting,
            quotedHtml: quotedHtml,
            editor: editor,
            close: close,
            toggleFullView: toggleFullView,
            discardDraft: discardDraft,
            toggleMinimize: toggleMinimize,
            onFileChange: onFileChange,
            removeAttachment: removeAttachment,
            formatBytes: formatBytes,
            setLink: setLink,
            saveDraft: saveDraft,
            send: send,
            fonts: fonts,
            setFont: setFont,
            setColor: setColor,
            setHighlight: setHighlight,
        };
    },
    props: { panelMode: { type: Boolean, default: false } },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    props: { panelMode: { type: Boolean, default: false } },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=ComposeDialog.vue.js.map