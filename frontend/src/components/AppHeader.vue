<template>
  <header class="header-container">
    <router-link to="/" class="header-title">MONTAGE</router-link>
    <div v-if="userStore.user !== null" class="header-user">
      <div class="account-info-container">
        <account class="account-info-icon" />
        <span>{{ userStore.user.username }}</span>
      </div>
      <cdx-button action="destructive" weight="quiet" @click="userStore.logout">
        Logout
      </cdx-button>
    </div>
  </header>
</template>

<script setup>
import { useUserStore } from '@/stores/user'
import { CdxButton } from '@wikimedia/codex'
import Account from 'vue-material-design-icons/Account.vue'

const userStore = useUserStore()
console.log(userStore.user)
</script>

<style scoped>
.header-container {
  padding: 18px 64px;
  height: 63px;
  border-bottom: 3px solid #006cb6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: bold;
  color: #000;
  text-decoration: none;
}

.account-info-container {
  display: flex;
  margin-right: 16px;
  margin-top: 8px;
}

.header-user {
  display: flex;
  color: gray;
}

.account-info-icon {
  margin-right: 8px;
}
</style>
