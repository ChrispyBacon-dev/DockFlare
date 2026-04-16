import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
export function useAuth() {
    const authStore = useAuthStore();
    const router = useRouter();
    const login = (token) => {
        authStore.setToken(token);
        router.push('/');
    };
    const logout = () => {
        authStore.logout();
        router.push('/login');
    };
    const user = computed(() => authStore.decodeToken());
    return {
        isAuthenticated: authStore.isAuthenticated,
        token: authStore.token,
        user,
        login,
        logout
    };
}
//# sourceMappingURL=useAuth.js.map