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
const envName = import.meta.env.DEV ? 'DEV' : 'PROD'
</script>

<style scoped>
.footer-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  font-size: 14px;
  color: var(--text-muted);
  border-top: 1px solid var(--border-footer);
  background-color: var(--bg-surface);
}

.footer-left {
  display: flex;
  align-items: center;
}

.footer-link {
  margin-left: 12px;
  color: var(--link-color);
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}

.env-label {
  font-weight: bold;
  color: var(--link-color);
}
</style>
