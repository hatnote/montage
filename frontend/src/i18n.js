import { createI18n } from 'vue-i18n';
import en from '@/i18n/en.json';

// Initialize with default English messages in case of error
const messages = { en }; 

// Dynamically load all other messages
async function loadMessages() {
  try {
    const modules = import.meta.glob('./i18n/*.json');
    await Promise.all(
      Object.entries(modules).map(async ([path, importFn]) => {
        const lang = path.replace('./i18n/', '').replace('.json', '');
        if (lang !== 'en') {
          const module = await importFn();
          messages[lang] = module.default;
        }
      })
    );
  } catch (error) {
    console.error('Error loading i18n messages:', error);
  }
}

// Initialize i18n instance
async function initializeI18n() {
  try {
    await loadMessages();
  } catch (error) {
    console.error('Error initializing i18n:', error);
  }

  return createI18n({
    locale: 'en',
    fallbackLocale: 'en',
    messages
  });
}

export default initializeI18n;