import axios from 'axios'
import { useLoadingStore } from '@/stores/loading'
import alertService from './alertService'

// Create Axios instance for Backend API
const apiBackend = axios.create({
  baseURL: import.meta.env.VITE_API_ENDPOINT + '/v1/',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  },
  withCredentials: true
})

// Create Axios instance for Commons API (no auth interceptor — Commons uses its own auth)
const apiCommons = axios.create({
  baseURL: 'https://commons.wikimedia.org/w/api.php',
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  }
})

const addLoadingInterceptors = (instance) => {
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

  instance.interceptors.response.use(
    (response) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)
      return response['data']
    },
    (error) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)
      return Promise.reject(error)
    }
  )
}

// Separate 401 session-expiry interceptor — applied only to apiBackend.
// Commons API 401s are not Montage session failures and must not trigger a redirect.
const addAuthInterceptor = (instance) => {
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response && error.response.status === 401) {
        // Extract the backend's error message if available, fall back to a generic one.
        const backendErrors = error.response?.data?.errors
        const message =
          Array.isArray(backendErrors) && backendErrors.length > 0
            ? backendErrors[0]
            : 'Session expired. Please log in again.'

        // Show the message before any navigation so the user understands why
        // they're being redirected and does not lose context of what they were doing.
        alertService.error(message)

        // Delay redirect to give the user time to read the error toast.
        setTimeout(() => {
          window.location.href = '#/'
        }, 2000)
      }
      return Promise.reject(error)
    }
  )
}

addLoadingInterceptors(apiBackend)
addLoadingInterceptors(apiCommons)
addAuthInterceptor(apiBackend)   // session 401 handling — backend only

export { apiBackend, apiCommons }
