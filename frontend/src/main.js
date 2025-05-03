import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { i18n, loadMessages } from './i18n'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import { CdxTooltip } from '@wikimedia/codex'
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'

import DatePicker from 'vue-datepicker-next'
import 'vue-datepicker-next/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Toast)
app.use(i18n) // Use i18n immediately with English locale

// Global directive
app.directive('tooltip', CdxTooltip)
app.component('clip-loader', ClipLoader)
app.component('date-picker', DatePicker)

app.mount('#app')

// Load additional language messages dynamically
loadMessages().then(() => {
  console.log('All language messages loaded');
});
