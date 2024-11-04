import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'

import { CdxTooltip } from '@wikimedia/codex'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Toast)
app.use(i18n)

// Global directive
app.directive('tooltip', CdxTooltip)

app.mount('#app')
