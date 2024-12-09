<template>
    <cdx-multiselect-lookup
      v-model:input-chips="userChips"
      v-model:selected="selectedUsers"
      v-model:input-value="userInputValue"
      :menu-items="userOptions"
      @input="searchUser"
    >
      <template #no-results> {{  $t('montage-no-results') }} </template>
    </cdx-multiselect-lookup>
</template>

<script setup>
import { ref, watch } from 'vue'
import dataService from '@/services/dataService'

import { CdxMultiselectLookup } from '@wikimedia/codex'

const props = defineProps({
  users: Array
})

const emit = defineEmits(['update:selectedUsers'])

const userChips = ref([...props.users].map( u => ({ label: u, value: u })))
const userInputValue = ref('')
const userOptions = ref([...props.users].map( u => ({ label: u, value: u })))
const selectedUsers = ref([...props.users])

watch(selectedUsers, (newVal) => {
  emit('update:selectedUsers', newVal)
})

function searchUser(searchName) {
  if (!searchName) {
    userOptions.value = []
    return
  }

  if (searchName.length < 2) return

  dataService.searchUser(searchName.charAt(0).toUpperCase() + searchName.slice(1)).then((data) => {
    if (userInputValue.value !== searchName) return

    const users = data.query.globalallusers.map((user) => ({
      label: user.name,
      value: user.name
    }))
    userOptions.value = users
  })
}
</script>
