import { ref } from 'vue'
import { defineStore } from 'pinia'
import adminService from '@/services/adminService'

export const useUserStore = defineStore('user-store', () => {
  const user = ref(null)
  const isAuthenticated = ref(false)
  const authChecked = ref(false)
  // which deployment the backend is (prod, beta, devlabs, ...), from the API envelope
  const env = ref(null)

  function login(userObj) {
    if (!userObj) {
      window.location = import.meta.env.VITE_API_ENDPOINT + '/login'
    }
    user.value = userObj
    isAuthenticated.value = true
  }

  function logout() {
    window.location = import.meta.env.VITE_API_ENDPOINT + '/logout'
    user.value = null
    isAuthenticated.value = false
    authChecked.value = true
  }

  async function checkAuth() {
    if (!authChecked.value) {
      const res = await adminService.getUser()
      env.value = res.env || null
      if (res.status === 'success' && res.user) {
        login(res.user)
      }
      authChecked.value = true
    }
  }

  return { user, env, login, logout, checkAuth, isAuthenticated, authChecked }
})
