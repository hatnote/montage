import { useToast } from 'vue-toastification'

const toast = useToast()

const toMessage = (value) => {
  if (!value) return ''
  if (Array.isArray(value)) {
    return value
      .map((item) => (typeof item === 'string' ? item : String(item)))
      .filter(Boolean)
      .join(' ')
  }
  return typeof value === 'string' ? value : String(value)
}

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
    const data = error?.response?.data
    const backendErrors = toMessage(data?.errors)
    const backendMessage = toMessage(data?.message)
    const backendDetail = toMessage(data?.detail)
    const fallbackMessage = toMessage(error?.message)

    const text =
      backendErrors ||
      [backendMessage, backendDetail].filter(Boolean).join(': ') ||
      fallbackMessage ||
      'An error occurred'

    toast.error(text, {
      timeout: time || 5000,
      position: 'top-right'
    })
  }
}

export default AlertService
