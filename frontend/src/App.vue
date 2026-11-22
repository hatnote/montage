<template>
  <app-header />
  <main class="main-container">
     <div v-if="loading" class="loading-container">
      <div class="loading-bar">
        Loading...
      </div>
    </div>
    <router-view  v-else />
  </main>
  <app-footer />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'
 const loading = ref(true)

onMounted(() => {
  // simulate loading delay or wait for data fetch
  setTimeout(() => {
    loading.value = false
  }, 300)
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
