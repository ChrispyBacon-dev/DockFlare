import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
export const useMailStore = defineStore('mail', () => {
    const mailboxes = ref([]);
    const currentMailbox = ref('');
    const folders = ref([]);
    const currentFolder = ref('');
    const messages = ref([]);
    const currentMessage = ref(null);
    const isComposeOpen = ref(false);
    const isComposeFullView = ref(false);
    const composeDefaults = ref(null);
    const composeBody = ref('');
    const activeTab = ref('all');
    const isCollapsed = ref(false);
    const sortOrder = ref('desc');
    const isDark = ref(localStorage.getItem('theme') === 'dark');
    const viewMode = ref(localStorage.getItem('viewMode') || 'split');
    const unreadMessages = computed(() => messages.value.filter((m) => !m.is_read));
    const starredMessages = computed(() => messages.value.filter((m) => m.is_starred));
    const currentFolderObj = computed(() => folders.value.find((f) => f.name === currentFolder.value) || null);
    function toggleTheme() {
        isDark.value = !isDark.value;
        if (isDark.value) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        }
        else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }
    function toggleViewMode() {
        viewMode.value = viewMode.value === 'split' ? 'full' : 'split';
        localStorage.setItem('viewMode', viewMode.value);
    }
    return {
        mailboxes, currentMailbox,
        folders, currentFolder, currentFolderObj,
        messages, currentMessage,
        isComposeOpen, isComposeFullView, composeDefaults, composeBody,
        activeTab, isCollapsed,
        sortOrder, isDark, toggleTheme,
        viewMode, toggleViewMode,
        unreadMessages, starredMessages,
    };
});
//# sourceMappingURL=mail.js.map