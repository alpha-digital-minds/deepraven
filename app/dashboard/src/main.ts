import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { api } from './api'
import { useAuthStore } from './stores/auth'
import './style.css'

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)

// Wire Axios interceptors after Pinia is active
let _refreshPromise: Promise<void> | null = null

api.interceptors.request.use(config => {
  const auth = useAuthStore()
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  return config
})

api.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const auth = useAuthStore()
      if (auth.refreshToken) {
        if (!_refreshPromise) {
          _refreshPromise = api
            .post('/auth/refresh', { refresh_token: auth.refreshToken }, { _retry: true } as never)
            .then(r => auth.setTokens(r.data.access_token, r.data.refresh_token))
            .catch(() => { auth.logout(); router.push('/login') })
            .finally(() => { _refreshPromise = null })
        }
        await _refreshPromise
        if (auth.token) {
          original.headers.Authorization = `Bearer ${auth.token}`
          return api(original)
        }
      } else {
        auth.logout()
        router.push('/login')
      }
    }
    return Promise.reject(error)
  },
)

app.mount('#app')
