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

import AlertService from './alertService'

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

  // Response Interceptor
  instance.interceptors.response.use(
    (response) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      return response['data']
    },
    (error) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      if (error.response && error.response.status === 401) {
        // Auth failure - could be session expired
        // Hard redirect to home to trigger re-auth check
        AlertService.error({ message: 'Session expired. Please log in again.' })
        setTimeout(() => {
          window.location.href = '#/'
        }, 2000)
      }

      return Promise.reject(error)
    }
  )
}

addInterceptors(apiBackend)
addInterceptors(apiCommons)

export { apiBackend, apiCommons }
