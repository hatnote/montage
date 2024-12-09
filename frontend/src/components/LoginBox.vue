<template>
  <div class="login-container">
    <div class="login-box-container">
      <h2 class="login-box-heading">{{ $t('montage-login-heading') }}</h2>
      <p class="login-description">{{ $t('montage-login-description') }}</p>
      <p
        class="account-instructions"
        v-html="
          $t('montage-login-account-instructions', [
            `<a href='https://meta.wikimedia.org/wiki/Main_Page' target='_blank' rel='noopener noreferrer'>${$t('montage-login-metawiki')}</a>`
          ])
        "
      ></p>
      <cdx-button class="login-button" action="progressive" icon="check" @click="redirectToLogin">
        {{ $t('montage-login-button') }}
      </cdx-button>
      <clip-loader v-if="isLoading" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CdxButton } from '@wikimedia/codex'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// State
const isLoading = ref(false)

const redirectToLogin = () => {
  isLoading.value = true
  userStore.login(null)
}
</script>

<style scoped>
.login-container {
  min-height: calc(100vh - 116.5px);
  display: flex;
  justify-content: center;
  align-items: center;
}

.login-box-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.login-box-heading {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 36px;
  text-align: center;
}

.login-description,
.account-instructions {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
}

.login-button {
  width: 100%;
  margin-top: 20px;
  margin-bottom: 10px;
}
</style>
