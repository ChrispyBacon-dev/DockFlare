import { ref } from 'vue';
import { mailApi } from '../api/mail';
export function useSearch() {
    const query = ref('');
    const results = ref([]);
    const loading = ref(false);
    const search = async (address, q) => {
        if (!q) {
            results.value = [];
            return;
        }
        loading.value = true;
        try {
            const res = await mailApi.searchMessages(address, { q });
            const payload = res.data;
            results.value = Array.isArray(payload) ? payload : payload.items || [];
        }
        catch (e) {
            console.error(e);
        }
        finally {
            loading.value = false;
        }
    };
    return { query, results, loading, search };
}
//# sourceMappingURL=useSearch.js.map