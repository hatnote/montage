import { createI18n } from 'vue-i18n'

import en from '@/i18n/en.json'
import hi from '@/i18n/hi.json'

const i18n = createI18n({
  locale: 'en',
  messages: {
    en,
    hi
  }
})

export default i18n
