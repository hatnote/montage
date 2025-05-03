import { createI18n } from 'vue-i18n';
import en from '@/i18n/en.json';

const messages = { en };

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages
});

// Dynamically load additional messages after initialization
const loadMessages = async () => {
  try {
    const modules = import.meta.glob('./i18n/*.json');
    await Promise.all(
      Object.entries(modules).map(async ([path, importFn]) => {
        const lang = path.replace('./i18n/', '').replace('.json', '');
        if (lang !== 'en' && lang !== 'qqq') {
          const module = await importFn();
          i18n.global.setLocaleMessage(lang, module.default);
        }
      })
    );
    return i18n;
  } catch (error) {
    console.error('Error loading i18n messages:', error);
    return i18n;
  }
};

export { i18n, loadMessages };
