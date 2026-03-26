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
      
      <div class="login-help-section">
        <cdx-button weight="quiet" @click="showHelp = !showHelp">
          {{ $t('montage-login-trouble-heading') }}
        </cdx-button>
        <div v-if="showHelp" class="login-help-content">
          <ul>
            <li>{{ $t('montage-login-trouble-1') }}</li>
            <li>{{ $t('montage-login-trouble-2') }}</li>
            <li>{{ $t('montage-login-trouble-3') }}</li>
          </ul>
        </div>
      </div>
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
const showHelp = ref(false)

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
  margin-bottom: 20px;
}

.login-help-section {
  text-align: center;
  border-top: 1px solid #eee;
  padding-top: 15px;
}

.login-help-content {
  text-align: left;
  font-size: 13px;
  color: #777;
  margin-top: 10px;
}

.login-help-content ul {
  padding-left: 20px;
}

.login-help-content li {
  margin-bottom: 5px;
}
</style>
