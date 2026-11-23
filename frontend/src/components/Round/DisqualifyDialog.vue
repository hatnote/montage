<template>
  <div class="disqualify-dialog">
    <div class="disqualify-dialog-image">
      <CommonsImage :image="entry" :width="400" image-class="disqualify-dialog-thumbnail" />
    </div>
    <div class="disqualify-dialog-content">
      <h4>{{ entry.name }}</h4>
      <div class="disqualify-dialog-form">
        <label for="dq-reason">{{ $t('montage-disqualify-reason') }} *</label>
        <cdx-select
          :selected="selectedReason"
          :menu-items="menuItems"
          :default-label="$t('montage-disqualify-select-reason')"
          :status="reasonError ? 'error' : 'default'"
          @update:selected="selectedReason = $event"
        />
        <cdx-text-area
          v-if="selectedReason === 'other'"
          v-model="otherReason"
          id="dq-reason"
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
<script setup>
import { ref, computed, defineProps, defineExpose } from 'vue'
import { CdxTextArea, CdxSelect } from '@wikimedia/codex'
import CommonsImage from '@/components/CommonsImage.vue'
import { i18n } from '@/i18n'
import en from '@/i18n/en.json'

// dialogService renders this component outside the app context, so
// useI18n() is not available here; use the global instance instead.
const $t = i18n.global.t

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
  { value: 'not_eligible', key: 'montage-disqualify-reason-not-eligible' },
  { value: 'monument_id', key: 'montage-disqualify-reason-monument-id' },
  { value: 'copyright', key: 'montage-disqualify-reason-copyright' },
  { value: 'photographer_not_eligible', key: 'montage-disqualify-reason-photographer' },
  { value: 'other', key: 'montage-disqualify-reason-other' }
]

const menuItems = computed(() => reasonOptions.map((o) => ({ value: o.value, label: $t(o.key) })))

const saveImageData = () => {
  let finalReason = ''

  if (selectedReason.value === 'other') {
    finalReason = otherReason.value.trim()
  } else {
    const option = reasonOptions.find((o) => o.value === selectedReason.value)
    // Send the English text, not the translation, so the stored reason and
    // the audit log read the same whatever language the coordinator uses.
    finalReason = option ? en[option.key] : ''
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
