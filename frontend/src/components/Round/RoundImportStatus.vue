<template>
  <div v-if="job" class="round-import-status">
    <h4>{{ $t('montage-import-status-' + job.status) }}</h4>
    <template v-if="job.status === 'queued'">
      <p>{{ $t('montage-import-queued-since', [formatUtcDateTime(job.create_date, locale)]) }}</p>
      <p class="greyed">{{ $t('montage-import-refresh-hint') }}</p>
    </template>
    <template v-else-if="job.status === 'running'">
      <p>{{ $t('montage-import-started-at', [formatUtcDateTime(job.start_date, locale)]) }}</p>
      <p class="greyed">{{ $t('montage-import-refresh-hint') }}</p>
    </template>
    <template v-else-if="job.status === 'succeeded'">
      <p>{{ $t('montage-import-finished-at', [formatUtcDateTime(job.finish_date, locale)]) }}</p>
      <p>
        {{
          $t('montage-import-counts', [
            job.entry_count,
            job.new_round_entry_count,
            job.disqualified_count
          ])
        }}
      </p>
      <div v-if="warnings.length">
        <strong>{{ $t('montage-import-warnings') }}</strong>
        <ul>
          <li v-for="(warning, index) in warnings" :key="index" class="round-import-warning">
            {{ warning }}
          </li>
        </ul>
      </div>
    </template>
    <template v-else-if="job.status === 'failed'">
      <p>{{ $t('montage-import-finished-at', [formatUtcDateTime(job.finish_date, locale)]) }}</p>
      <p v-if="details?.error" class="round-import-error">
        {{ $t('montage-import-error', [details.error]) }}
      </p>
      <p v-if="job.dismissed" class="greyed">{{ $t('montage-import-dismissed-note') }}</p>
      <template v-if="roundStatus === 'paused'">
        <!-- activation needs files: promise it only when the round has some -->
        <p v-if="entryCount === 0">{{ $t('montage-import-failed-next-step-empty') }}</p>
        <p v-else-if="entryCount > 0 && !job.dismissed">
          {{ $t('montage-import-failed-next-step') }}
        </p>
        <div class="round-import-actions">
          <cdx-button action="progressive" :disabled="busy" @click="retryImport">
            {{ $t('montage-import-retry') }}
          </cdx-button>
          <cdx-button v-if="!job.dismissed" :disabled="busy" @click="dismissImport">
            {{ $t('montage-import-dismiss') }}
          </cdx-button>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxButton } from '@wikimedia/codex'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import { formatUtcDateTime, formatImportWarning } from '@/utils'

const props = defineProps({
  roundId: Number,
  roundStatus: String,
  importState: Object,
  // files in the round (from the admin round details); null until loaded
  entryCount: { type: Number, default: null }
})

const { t: $t, locale } = useI18n()

const job = computed(() => props.importState?.job || null)
const details = ref(null)
const busy = ref(false)

const warnings = computed(() => (details.value?.warnings || []).map(formatImportWarning))

// Retry: a new job with the failed job's method and params (#621/#622)
const retryImport = () => {
  busy.value = true
  adminService
    .retryImportJob(props.roundId, job.value.id)
    .then(() => {
      alertService.success($t('montage-import-retry-started'))
      location.reload()
    })
    .catch(alertService.error)
    .finally(() => {
      busy.value = false
    })
}

// Dismiss: the failed import no longer blocks activation
const dismissImport = () => {
  busy.value = true
  adminService
    .dismissImportJob(props.roundId, job.value.id)
    .then(() => {
      alertService.success($t('montage-import-dismissed'))
      location.reload()
    })
    .catch(alertService.error)
    .finally(() => {
      busy.value = false
    })
}

// One details fetch per finished job state; no polling (#622). Watched,
// not onMounted: a campaign reload reuses this component with new props.
watch(
  () => (job.value ? `${job.value.id}:${job.value.status}` : null),
  () => {
    details.value = null
    if (job.value && ['succeeded', 'failed'].includes(job.value.status)) {
      const jobId = job.value.id
      adminService
        .getImportJob(props.roundId, jobId)
        .then((response) => {
          if (job.value && job.value.id === jobId) details.value = response.data
        })
        .catch(() => {
          details.value = null
        })
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.round-import-status {
  margin-bottom: 16px;
}

.round-import-warning {
  white-space: pre-line;
}

.round-import-actions {
  display: flex;
  gap: 8px;
}

.round-import-error {
  color: #bf3c2c;
  white-space: pre-line;
}
</style>
