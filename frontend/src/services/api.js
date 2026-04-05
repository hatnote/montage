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

  // Response Interceptor
  instance.interceptors.response.use(
    (response) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      const data = response['data']
      if (data?.status === 'failure' || data?.status === 'exception') {
        const rawErrors = data.errors
        let messages = []
        if (Array.isArray(rawErrors)) {
          messages = rawErrors
        } else if (typeof rawErrors === 'string') {
          messages = [rawErrors]
        } else if (rawErrors && typeof rawErrors === 'object') {
          messages = Object.values(rawErrors).flatMap((value) =>
            Array.isArray(value) ? value : typeof value === 'string' ? [value] : []
          )
        }
        const err = new Error(messages.join('; ') || 'An error occurred')
        err.response = response
        return Promise.reject(err)
      }

      return data
    },
    (error) => {
      const loadingStore = useLoadingStore()
      loadingStore.setLoading(false)

      return Promise.reject(error)
    }
  )
}

addInterceptors(apiBackend)
addInterceptors(apiCommons)

export { apiBackend, apiCommons }
