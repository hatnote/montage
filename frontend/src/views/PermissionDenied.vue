<template>
  <div class="permission-denied">
    <h1>{{ $t('permission-denied-title') }}</h1>
    <p>{{ $t('permission-denied-message') }}</p>
    <router-link to="/">
      <cdx-button action="progressive" weight="primary">{{
        $t('permission-denied-home')
      }}</cdx-button>
    </router-link>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { CdxButton } from '@wikimedia/codex'
</script>

<style scoped>
.permission-denied {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  min-height: calc(100vh - 116.5px);
  background-color: #f8f9fa;
  padding: 20px;
}

.permission-denied h1 {
  font-size: 2.5rem;
  margin-bottom: 20px;
  color: #dc3545;
}

.permission-denied p {
  font-size: 1.25rem;
  margin-bottom: 40px;
  color: #6c757d;
}
</style>
