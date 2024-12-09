<template>
  <div class="home-view">
    <login-box v-if="userStore.user === null" />
    <active-campaign v-else />
  </div>
</template>

<script setup>
import { useUserStore } from '@/stores/user'
import ActiveCampaign from '@/components/Campaign/ActiveCampaign.vue'
import LoginBox from '@/components/LoginBox.vue'

const userStore = useUserStore()
</script>
