import { ref, onMounted, onUnmounted } from 'vue';
const isMobile = ref(false);
export function useBreakpoint() {
    const mq = window.matchMedia('(max-width: 767px)');
    const update = (e) => {
        isMobile.value = e.matches;
    };
    onMounted(() => {
        isMobile.value = mq.matches;
        mq.addEventListener('change', update);
    });
    onUnmounted(() => mq.removeEventListener('change', update));
    return { isMobile };
}
//# sourceMappingURL=useBreakpoint.js.map