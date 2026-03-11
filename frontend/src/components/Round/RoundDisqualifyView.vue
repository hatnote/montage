<template>
  <div class="disqualify-dialog">
    <div class="diqualify-dialog-image">
      <CommonsImage :image="entry" :width="400" image-class="disqualify-dialog-thumbnail" />
    </div>
    <div class="disqualify-dialog-content">
      <h4>{{ entry.name }}</h4>
      <div class="disqualify-dialog-form">
        <label for="dq-reason">{{ $t('montage-disqualify-reason') }} *</label>
        <cdx-text-area
          id="dq-reason"
          v-model="reason"
          :placeholder="$t('montage-disqualify-reason-placeholder')"
          :status="reasonError ? 'error' : 'default'"
        />
        <p v-if="reasonError" class="disqualify-dialog-error">
          {{ $t('montage-disqualify-reason-required') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CdxTextArea } from '@wikimedia/codex'
import CommonsImage from '../CommonsImage.vue'

const props = defineProps({
  entry: {
    type: Object,
    required: true
  }
})

const reason = ref('')
const reasonError = ref(false)

const validate = () => {
  reasonError.value = !reason.value.trim()
  return !reasonError.value
}

const getReason = () => {
  return reason.value.trim()
}

defineExpose({ validate, getReason })
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
