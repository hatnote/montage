<template>
  <footer class="footer-container">
    <div class="footer-left">
      <span>&copy; {{ new Date().getFullYear() }} // {{ $t('montage-credit') }}</span>
      <a
        href="https://commons.wikimedia.org/wiki/Commons:Montage"
        class="footer-link"
        target="_blank"
      >
        {{ $t('montage-about') }}</a
      >
      <a href="https://github.com/hatnote/montage" class="footer-link" target="_blank">
        {{ $t('montage-source-code') }}
      </a>
    </div>
    <div class="footer-right">
      <span class="env-label">{{ envName }}</span>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// The backend's MONTAGE_ENV, not Vite's build mode: every deployed tool is a
// production build, so import.meta.env.DEV alone said "PROD" everywhere.
const ENV_LABELS = { prod: 'PROD', beta: 'BETA', devlabs: 'DEV', dev: 'LOCAL' }
const envName = computed(() => {
  const env = userStore.env
  if (env) return ENV_LABELS[env] || env.toUpperCase()
  return import.meta.env.DEV ? 'LOCAL' : ''
})
</script>

<style scoped>
.footer-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  font-size: 14px;
  color: #666;
  border-top: 1px solid #e0e0e0;
}

.footer-left {
  display: flex;
  align-items: center;
}

.footer-link {
  margin-left: 12px;
  color: #006cb6;
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}

.env-label {
  font-weight: bold;
  color: #006cb6;
}
</style>
