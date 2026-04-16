import { ref } from 'vue';
const deferredPrompt = ref(null);
const canInstall = ref(false);
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt.value = e;
    canInstall.value = true;
});
window.addEventListener('appinstalled', () => {
    deferredPrompt.value = null;
    canInstall.value = false;
});
export function useInstallPrompt() {
    const promptInstall = async () => {
        if (!deferredPrompt.value)
            return;
        await deferredPrompt.value.prompt();
        const { outcome } = await deferredPrompt.value.userChoice;
        if (outcome === 'accepted') {
            deferredPrompt.value = null;
            canInstall.value = false;
        }
    };
    return { canInstall, promptInstall };
}
//# sourceMappingURL=useInstallPrompt.js.map