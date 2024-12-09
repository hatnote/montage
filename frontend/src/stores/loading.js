import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLoadingStore = defineStore('loading', () => {
  const loading = ref(null)

  function setLoading(val) {
    loading.value = val
  }

  return { loading, setLoading }
})
