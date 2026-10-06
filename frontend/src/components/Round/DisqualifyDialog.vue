<template>
  <div class="disqualify-dialog">
    <div class="disqualify-dialog-image">
      <CommonsImage :image="entry" :width="400" image-class="disqualify-dialog-thumbnail" />
    </div>
    <div class="disqualify-dialog-content">
      <h4>{{ entry.name }}</h4>
      <div class="disqualify-dialog-form">
        <label for="dq-reason">Reason for disqualification *</label>
        <cdx-select
          :selected="selectedReason"
          :menu-items="reasonOptions"
          default-label="Select a reason"
          :status="reasonError ? 'error' : 'default'"
          @update:selected="selectedReason = $event"
        />
        <cdx-text-area
          v-if="selectedReason === 'other'"
          v-model="otherReason"
          id="dq-reason"
          placeholder="Enter custom reason"
          :status="reasonError ? 'error' : 'default'"
        />
        <p v-if="reasonError" class="disqualify-dialog-error">
          Please provide a reason for disqualification
        </p>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, defineProps, defineExpose } from 'vue'
import { CdxTextArea, CdxSelect } from '@wikimedia/codex'
import CommonsImage from '@/components/CommonsImage.vue'

const props = defineProps({
  entry: {
    type: Object,
    required: true
  },
  onSave: {
    type: Function,
    required: true
  }
})

const selectedReason = ref('')
const otherReason = ref('')
const reasonError = ref(false)

const reasonOptions = [
  { label: 'Wrong country', value: 'wrong_country' },
  { label: 'Photo not in the correct country', value: 'incorrect_country' },
  { label: 'Photo does not indicate building number', value: 'no_building_number' },
  { label: 'Copyright infringement', value: 'copyright' },
  { label: 'Photo taken by employee of local chapter or sponsor', value: 'employee_photo' },
  { label: 'Other', value: 'other' }
]

const saveImageData = () => {
  let finalReason = ''

  if (selectedReason.value === 'other') {
    finalReason = otherReason.value.trim()
  } else {
    const option = reasonOptions.find((o) => o.value === selectedReason.value)
    finalReason = option ? option.label : ''
  }

  reasonError.value = !finalReason
  if (reasonError.value) return

  if (props.onSave) {
    props.onSave(finalReason)
  }
}

defineExpose({ saveImageData })
</script>
<style scoped>
.disqualify-dialog {
  display: flex;
  gap: 20px;
  padding: 16px 0;
}
.disqualify-dialog-image {
  flex: 0 0 200px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.disqualify-dialog-thumbnail {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
}
.disqualify-dialog-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.disqualify-dialog-content h4 {
  margin: 0 0 16px 0;
  word-break: break-word;
}
.disqualify-dialog-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.disqualify-dialog-form label {
  font-weight: 600;
}
.disqualify-dialog-error {
  color: #d33;
  font-size: 14px;
  margin: 0;
}
</style>
