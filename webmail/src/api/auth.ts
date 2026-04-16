import apiClient from './client'

export const authApi = {
  checkAuth: () => apiClient.get('/auth/me'),

  loginWithPassword: async (email: string, password: string) => {
    const response = await fetch('/email/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    return response.json()
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const token = localStorage.getItem('jwt_token')
    const response = await fetch('/email/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
    return response.json()
  },
}
