import { defineStore } from 'pinia';
import { ref, shallowRef, computed } from 'vue';
import { format as dateFnsFormat } from 'date-fns';
const DATE_FORMATS = {
    us: 'PPpp',
    eu: 'dd.MM.yyyy, HH:mm:ss',
    iso: 'yyyy-MM-dd HH:mm:ss',
};
export const useMailStore = defineStore('mail', () => {
    const mailboxes = ref([]);
    const currentMailbox = ref('');
    const folders = ref([]);
    const currentFolder = ref('');
    const messages = shallowRef([]);
    const totalMessages = ref(0);
    const hasMoreMessages = ref(false);
    const messagesPage = ref(1);
    const isFetchingNextPage = ref(false);
    const currentMessage = ref(null);
    const messagesLoading = ref(false);
    const isComposeOpen = ref(false);
    const isComposeFullView = ref(false);
    const isSettingsOpen = ref(false);
    const composeDefaults = ref(null);
    const composeBody = ref('');
    const activeTab = ref('all');
    const isCollapsed = ref(false);
    const sortOrder = ref('desc');
    const isDark = ref(localStorage.getItem('theme') === 'dark');
    const dateFormat = ref(localStorage.getItem('dateFormat') || 'us');
    const settingsCategory = ref('notifications');
    function formatDate(ts) {
        if (!ts)
            return '';
        return dateFnsFormat(new Date(ts), DATE_FORMATS[dateFormat.value]);
    }
    function setDateFormat(key) {
        dateFormat.value = key;
        localStorage.setItem('dateFormat', key);
    }
    const viewMode = ref(localStorage.getItem('viewMode') || 'split');
    const toast = ref(null);
    let toastTimer = null;
    let _loadMore = null;
    function showToast(message, type = 'error') {
        if (toastTimer)
            clearTimeout(toastTimer);
        toast.value = { message, type };
        toastTimer = setTimeout(() => { toast.value = null; }, 4000);
    }
    function registerLoadMore(fn) {
        _loadMore = fn;
    }
    function loadMore() {
        if (_loadMore)
            _loadMore();
    }
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
        messages, totalMessages, hasMoreMessages, messagesPage, isFetchingNextPage,
        currentMessage, messagesLoading,
        isComposeOpen, isComposeFullView, isSettingsOpen, composeDefaults, composeBody,
        activeTab, isCollapsed,
        sortOrder, isDark, toggleTheme,
        dateFormat, setDateFormat, formatDate,
        settingsCategory,
        viewMode, toggleViewMode,
        unreadMessages, starredMessages,
        toast, showToast,
        registerLoadMore, loadMore,
    };
});
//# sourceMappingURL=mail.js.map