import { useToast } from 'vue-toastification'

const toast = useToast()

const AlertService = {
  success(text, time) {
    toast.success(text, {
      timeout: time || 2000,
      position: 'top-right'
    })
  },
  error(error, time) {
    const message = error?.response?.data?.message || error?.message || 'An error occurred'
    const detail = error?.response?.data?.detail

    const text = detail ? `${message}: ${detail}` : message

    toast.error(text, {
      timeout: time || 5000,
      position: 'top-right'
    })
  }
}

export default AlertService
