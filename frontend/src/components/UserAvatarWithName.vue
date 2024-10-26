<template>
  <div class="user-avatar-container">
    <span class="user-avatar-item" v-for="user in sortedCoordinators" :key="user.username">
      <span class="user-avatar" :style="{ backgroundColor: getAvatarColor(user.username) }">
        {{ user.username[0].toUpperCase() }}
      </span>
      {{ user.username }}
    </span>
  </div>
</template>

<script setup>
import { computed, toRefs } from 'vue'
import { getAvatarColor } from '@/utils'

const props = defineProps({
  coordinators: {
    type: Array,
    required: true
  }
})

const { coordinators } = toRefs(props)

const sortedCoordinators = computed(() => {
  return coordinators.value?.slice().sort((a, b) => a.username.localeCompare(b.username))
})
</script>

<style scoped>
.user-avatar-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.user-avatar-item {
  display: flex;
  align-items: center;
  background-color: #e0e0e0;
  padding: 0;
  padding-right: 12px;
  border-radius: 24px;
  font-weight: 500;
}

.user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  color: white;
}
</style>
