import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('dr_jwt'))
  const refreshToken = ref<string | null>(localStorage.getItem('dr_refresh'))
  const email = ref<string>(localStorage.getItem('dr_email') || '')

  const isAuthenticated = computed(() => !!token.value)

  function setTokens(access: string, refresh: string | null) {
    token.value = access
    if (refresh) refreshToken.value = refresh
    localStorage.setItem('dr_jwt', access)
    if (refresh) localStorage.setItem('dr_refresh', refresh)
  }

  function setEmail(e: string) {
    email.value = e
    localStorage.setItem('dr_email', e)
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    email.value = ''
    localStorage.removeItem('dr_jwt')
    localStorage.removeItem('dr_refresh')
    localStorage.removeItem('dr_email')
  }

  return { token, refreshToken, email, isAuthenticated, setTokens, setEmail, logout }
})
