<template>
  <app-header />
  <main class="main-container" >
    <router-view />
  </main>
  <app-footer  />
</template>

<script setup>
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'

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
