import { ref } from 'vue'
import { defineStore } from 'pinia'
import adminService from '@/services/adminService'

export const useUserStore = defineStore('user-store', () => {
  const user = ref(null)
  const isAuthenticated = ref(false)

  function login(userObj) {
    if (!userObj) {
      window.location =  window.location.origin + '/login'
    }
    user.value = userObj
    isAuthenticated.value = true
  }

  function logout() {
    window.location = window.location.origin + '/logout'
    user.value = null
    isAuthenticated.value = false
  }

  async function checkAuth() {
    if (!isAuthenticated.value) {
      const res = await adminService.get()
      if (res.status === 'success' && res.user) {
        login(res.user)
      }
    }
  }

  return { user, login, logout, checkAuth }
})
