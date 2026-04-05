import { useToast } from 'vue-toastification'

const toast = useToast()

const AlertService = {
  success(text, time, callback) {
    toast.success(text, {
      timeout: time || 2000,
      position: 'top-right',
      onClose: () => {
        callback && callback()
      }
    })
  },
  error(error, time) {
    const backendErrors = error?.response?.data?.errors
    const normalizedBackendErrors = Array.isArray(backendErrors)
      ? backendErrors.length && backendErrors.join('; ')
      : typeof backendErrors === 'string'
        ? backendErrors
        : null
    const message =
      normalizedBackendErrors ||
      error?.response?.data?.message ||
      error?.message ||
      'An error occurred'
    const detail = error?.response?.data?.detail

    const text = detail ? `${message}: ${detail}` : message

    toast.error(text, {
      timeout: time || 5000,
      position: 'top-right'
    })
  }
}

export default AlertService
