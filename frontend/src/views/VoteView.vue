<template>
  <div class="vote-view-container">
    <vote />
  </div>
</template>

<script setup>
import Vote from '@/components/Vote/Vote.vue'
</script>

<style scoped>
.vote-view-container {
  padding: 20px;
  min-height: calc(100vh - 116.5px);
}
</style>
