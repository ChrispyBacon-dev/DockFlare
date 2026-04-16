import apiClient from './client';
export const authApi = {
    checkAuth: () => apiClient.get('/auth/me'),
    loginWithPassword: async (email, password) => {
        const response = await fetch('/email/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        return response.json();
    },
};
//# sourceMappingURL=auth.js.map