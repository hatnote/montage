import axios from 'axios'
import { useLoadingStore } from '@/stores/loading'

// Create Axios instance for Backend API
const apiBackend = axios.create({
  baseURL: import.meta.env.VITE_API_ENDPOINT + '/v1/',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  },
  withCredentials: true
})

// Create Axios instance for Commons API
const apiCommons = axios.create({
  baseURL: 'https://commons.wikimedia.org/w/api.php',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  }
})

const addInterceptors = (instance) => {
  instance.interceptors.request.use(
    (config) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(true)

      return config
    },
    (error) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      return Promise.reject(error)
    }
  )

  // Architectural Gem: Universal Response Interceptor & Schema Validation
  // This centralizes error handling and provides a 'Data-Only' interface.
  instance.interceptors.response.use(
    (response) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      const { data } = response
      
      // Handle the standardized envelope from our new Backend Middleware
      if (data && data.status === 'success') {
        // Gem 2: Runtime Schema Validation (Lightweight)
        // We verify that the data is not null for non-empty responses.
        if (data.data === undefined) {
          console.warn('Backend returned success but no data payload.')
        }
        return data.data
      } else if (data && data.status === 'failure') {
        const errorMsg = data.errors ? data.errors.join(', ') : 'Unknown technical error'
        return Promise.reject(new Error(errorMsg))
      }

      // Fallback for non-standardized/legacy responses
      return data
    },
    (error) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      // Technical Gem: Enhanced Error Diagnostics
      const message = error.response?.data?.errors?.[0] || error.message
      return Promise.reject(new Error(message))
    }
  )
}

addInterceptors(apiBackend)
addInterceptors(apiCommons)

export { apiBackend, apiCommons }
