<template>
  <div class="dialog-container">
    <user-list :users="users" @update:selectedUsers="users = $event" />
    <cdx-button
      class="save-btn"
      action="progressive"
      weight="primary"
      @click="saveNewOrganizer"
      :disabled="isLoading"
    >
      {{ props.addMsg }}
    </cdx-button>
    <clip-loader v-if="isLoading" style="margin-top: 32px" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'

// Components
import { CdxButton } from '@wikimedia/codex'
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
import UserList from './UserList.vue'

// Props
const props = defineProps({
  addMsg: String,
  addSuccessMsg: String
})

// State
const isLoading = ref(false)
const users = ref([])

const saveNewOrganizer = () => {
  console.log(users.value)
  if (!users.value.length) {
    alertService.error({ message: 'Please add at least one user' })
    return
  }

  if (users.value.length > 1) {
    alertService.error({ message: 'Please add only one user' })
    return
  }

  const username = users.value[0]
  isLoading.value = true
  adminService
    .addOrganizer({ username })
    .then(() => {
      alertService.success(props.addSuccessMsg, 1500, () => {
        isLoading.value = false
        window.location.reload()
      })
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
}
</script>
<style>
.dialog-container {
  position: relative;
}

.dialog-container .cdx-menu {
  position: relative !important;
}

.save-btn {
  margin-top: 32px;
  float: right;
}
</style>
