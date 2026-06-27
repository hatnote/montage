import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme-store', () => {
  const isDark = ref(false)

  function init() {
    isDark.value = localStorage.getItem('_montageTheme') === 'dark'
    _apply()
  }

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem('_montageTheme', isDark.value ? 'dark' : 'light')
    _apply()
  }

  function _apply() {
    document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  }

  return { isDark, init, toggle }
})
