<template>
  <div class="aggregate-round">
    <div class="round-header">
      <poll class="round-icon" :size="36" fillColor="white" />
      <div class="round-info">
        <h2>{{ $t('Aggregate Round') }}</h2>
      </div>
    </div>

    <div class="card-container">
      <cdx-card style="margin-top: 24px">
        <template #supporting-text>
          <div class="form-container">

            <cdx-field>
              <cdx-text-input v-model="formData.name" />
              <template #label>{{ $t('Aggregate Name') }}</template>
            </cdx-field>

            <cdx-field>
              <template #label>{{ $t('Aggregate Source Rounds') }}</template>
              <template #description>
              </template>
              <div class="round-checkboxes">
                <cdx-checkbox
                  v-for="rnd in finalizableRounds"
                  :key="rnd.id"
                  v-model="formData.source_round_ids"
                  :input-value="rnd.id"
                >
                  {{ rnd.name }} ({{ rnd.vote_method }})
                </cdx-checkbox>
              </div>
            </cdx-field>

            <cdx-field>
              <cdx-text-input
                v-model="formData.max_length"
                input-type="number"
                placeholder="Leave blank for all"
              />
              <template #label>{{ $t('Aggregate max-length') }}</template>
              <template #description>
              </template>
            </cdx-field>

          </div>

          <div class="button-group">
            <cdx-button
              action="progressive"
              weight="primary"
              :disabled="isLoading || formData.source_round_ids.length === 0"
              @click="runPreview"
            >
              <eye class="icon-small" /> {{ $t('Aggregate preview') }}
            </cdx-button>
            <cdx-button action="default" @click="$emit('cancel')">
              <close class="icon-small" /> {{ $t('montage-btn-cancel') }}
            </cdx-button>
          </div>
        </template>
      </cdx-card>
    </div>

    <!-- Preview results panel -->
    <div class="card-container">
        <AggregatePreview
            v-if="previewResult"
            :result="previewResult"
            :is-loading="isLoading"
            @commit="runCommit"
            @repreview="runPreview"
        />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxCard, CdxButton, CdxField, CdxTextInput, CdxCheckbox } from '@wikimedia/codex'
import Poll from 'vue-material-design-icons/Poll.vue'
import Eye from 'vue-material-design-icons/Eye.vue'
import Close from 'vue-material-design-icons/Close.vue'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import AggregatePreview from './AggregatePreview.vue'

const { t: $t } = useI18n()

const props = defineProps({
  rounds: { type: Array, required: true },
  campaignId: { type: [String, Number], required: true }
})

const emit = defineEmits(['cancel', 'committed'])

const isLoading = ref(false)
const previewResult = ref(null)

const committedResult = ref(null)

onMounted(() => {
    adminService
        .getAggregateResults(props.campaignId)
        .then((resp) => {
            if (resp.data) {
                // show committed result in the preview panel
                previewResult.value = resp.data.results
                committedResult.value = resp.data
            }
        })
        .catch(() => {
            // No saved preview yet
        })
})

const formData = ref({
  name: '',
  source_round_ids: [],
  max_length: null
})

// Only finalized rounds can be aggregated
const finalizableRounds = computed(() =>
  props.rounds.filter((r) => r.status === 'finalized')
)

function buildPayload() {
  return {
    name: formData.value.name,
    source_round_ids: formData.value.source_round_ids,
    max_length: formData.value.max_length ? parseInt(formData.value.max_length) : null
  }
}

function runPreview() {
  if (formData.value.source_round_ids.length === 0) {
    alertService.error({ message: $t('Aggregate Select Rounds') })
    return
  }
  isLoading.value = true
  adminService
    .previewAggregate(props.campaignId, buildPayload())
    .then((resp) => {
      previewResult.value = resp.data
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
}

function runCommit() {
  isLoading.value = true
  adminService
    .commitAggregate(props.campaignId, buildPayload())
    .then(() => {
      alertService.success($t('Aggregate Committed'))
      emit('committed')
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
}
</script>

<style scoped>
.aggregate-round {
  display: flex;
  flex-direction: column;
}
.round-header {
  display: flex;
  align-items: center;
}
.round-icon {
  background-color: blue;
  height: 56px;
  padding: 10px;
  border-radius: 50%;
}
.round-info {
  margin-left: 24px;
}
.card-container {
  margin-left: 80px;
}
.form-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.round-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.button-group {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  margin-bottom: 12px;
}
.icon-small {
  font-size: 6px;
}

.form-container :deep(.cdx-label__label) {
	font-size: 16px;
	font-weight: 600;
}
</style>