<template>
  <app-header />
  <main class="main-container" >
    <!-- <div class="loading-container" v-if="loadingStore.loading">
      <cdx-progress-bar class="loading-bar" />
    </div> -->
    <router-view />
  </main>
  <app-footer  />
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
import { useUserStore } from '@/stores/user'
// import { useLoadingStore } from '@/stores/loading'
// import { CdxProgressBar } from '@wikimedia/codex'

const userStore = useUserStore()
// const loadingStore = useLoadingStore()

onMounted(async () => {
  await userStore.checkAuth()
})
</script>

<style scoped>
.main-container {
  background-color: #fafafa;
  min-height: calc(100vh - 116.5px);
  padding: 0 8px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 116.5px);
  width: 100%;
}

.loading-bar {
  width: 50%;
}
</style>
