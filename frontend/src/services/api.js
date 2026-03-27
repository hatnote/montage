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

const validateSchema = (data, schema, name = 'Global') => {
  if (import.meta.env.MODE === 'production') return data // Skip in production for performance
  
  if (!data || typeof data !== 'object') {
    console.warn(`[API Validation][${name}] Expected object, got ${typeof data}`)
    return data
  }

  Object.keys(schema).forEach((key) => {
    if (!(key in data)) {
      console.error(`[API Validation][${name}] Missing required field: "${key}"`)
    } else if (typeof data[key] !== schema[key]) {
      console.error(
        `[API Validation][${name}] Type mismatch for "${key}": Expected ${schema[key]}, got ${typeof data[key]}`
      )
    }
  })
  return data
}

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

      const res = response.data
      
      // Standardize response handling (Competitive Upgrade over PR #424)
      if (res.status === 'success') {
        // Example Schema Validation (to be extended in service files)
        if (response.config.url.includes('/campaign/')) {
          validateSchema(res.data, { id: 'number', name: 'string' }, 'Campaign')
        }
        return res.data
      }
      
      return Promise.reject(new Error(res.errors ? res.errors.join(', ') : 'API Error'))
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
