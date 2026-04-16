import axios from 'axios'
import router from '../router'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      import('../stores/auth').then(({ useAuthStore }) => {
        const authStore = useAuthStore()
        authStore.token = ''
      })
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default apiClient
