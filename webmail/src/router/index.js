import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'mail',
            component: () => import('../views/MailView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/login',
            name: 'login',
            component: () => import('../views/LoginView.vue')
        },
        {
            path: '/auth/callback',
            name: 'auth-callback',
            component: () => import('../views/LoginView.vue')
        },
        {
            path: '/settings',
            name: 'settings',
            component: () => import('../views/SettingsView.vue'),
            meta: { requiresAuth: true }
        }
    ]
});
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore();
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next('/login');
    }
    else {
        next();
    }
});
export default router;
//# sourceMappingURL=index.js.map