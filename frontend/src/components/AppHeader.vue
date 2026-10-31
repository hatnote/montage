<template>
  <header class="header-container">
    <router-link to="/" class="header-title">MONTAGE</router-link>
    <div style="display: flex; align-items: center">
      <div v-if="userStore.user !== null" class="header-user">
        <div class="account-info-container">
          <account class="account-info-icon" />
          <span>{{ userStore.user.username }}</span>
        </div>
        <cdx-button action="destructive" weight="quiet" @click="userStore.logout">
          {{ $t('montage-login-logout') }}
        </cdx-button>
      </div>

      <div class="theme-switch-wrapper">
        <weather-sunny v-if="themeStore.isDark" :size="18" />
        <weather-night v-else :size="18" />
        <label class="switch">
          <input type="checkbox" :checked="themeStore.isDark" @change="themeStore.toggle" />
          <span class="slider"></span>
        </label>
      </div>

      <cdx-select
        class="language-select"
        :menu-items="availableLanguages"
        :selected="selectedLanguage"
        @update:selected="changeLanguage"
      />
    </div>
  </header>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { useI18n } from 'vue-i18n'
import ISO6391 from 'iso-639-1'

// Components
import { CdxButton, CdxSelect } from '@wikimedia/codex'

// Icons
import Account from 'vue-material-design-icons/Account.vue'
import WeatherNight from 'vue-material-design-icons/WeatherNight.vue'
import WeatherSunny from 'vue-material-design-icons/WeatherSunny.vue'

const userStore = useUserStore()
const themeStore = useThemeStore()
const { locale, messages } = useI18n()

const selectedLanguage = ref('en')

const availableLanguages = Object.keys(messages.value).map((key) => {
  return {
    label: ISO6391.getNativeName(key) || key,
    value: key
  }
})

const changeLanguage = (newLanguage) => {
  selectedLanguage.value = newLanguage
  locale.value = newLanguage
  localStorage.setItem('_montageLanguage', newLanguage)
}

onMounted(() => {
  const storedLanguage = localStorage.getItem('_montageLanguage')
  if (storedLanguage && messages.value[storedLanguage]) {
    selectedLanguage.value = storedLanguage
    locale.value = storedLanguage
  } else {
    selectedLanguage.value = locale.value
  }
})
</script>

<style scoped>
.header-container {
  padding: 18px 16px 18px 64px;
  height: 63px;
  border-bottom: 3px solid var(--link-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--bg-surface);
}

.header-title {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-header);
  text-decoration: none;
}

.account-info-container {
  display: flex;
  margin-right: 16px;
}

.header-user {
  display: flex;
  align-items: center;
  color: var(--text-header-user);
}

.account-info-icon {
  margin-right: 8px;
}

.language-select {
  margin-left: 16px;
  width: 120px;
}
</style>
