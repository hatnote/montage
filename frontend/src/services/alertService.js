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
    // Prefer new API error format: error.response.data.errors
    let text = 'An error occurred'
    if (error?.response?.data?.errors) {
      if (Array.isArray(error.response.data.errors)) {
        text = error.response.data.errors.join('; ')
      } else {
        text = error.response.data.errors
      }
    } else if (error?.response?.data?.message) {
      text = error.response.data.message
    } else if (error?.message) {
      text = error.message
    }
    toast.error(text, {
      timeout: time || 5000,
      position: 'top-right'
    })
  }
}

export default AlertService
