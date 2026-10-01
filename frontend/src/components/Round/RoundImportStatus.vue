<template>
  <div v-if="job" class="round-import-status">
    <h4>{{ $t('montage-import-status-' + job.status) }}</h4>
    <template v-if="job.status === 'queued'">
      <p>{{ $t('montage-import-queued-since', [formatUtcDateTime(job.create_date)]) }}</p>
      <p class="greyed">{{ $t('montage-import-refresh-hint') }}</p>
    </template>
    <template v-else-if="job.status === 'running'">
      <p>{{ $t('montage-import-started-at', [formatUtcDateTime(job.start_date)]) }}</p>
      <p class="greyed">{{ $t('montage-import-refresh-hint') }}</p>
    </template>
    <template v-else-if="job.status === 'succeeded'">
      <p>{{ $t('montage-import-finished-at', [formatUtcDateTime(job.finish_date)]) }}</p>
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
      <p>{{ $t('montage-import-finished-at', [formatUtcDateTime(job.finish_date)]) }}</p>
      <p v-if="details?.error" class="round-import-error">
        {{ $t('montage-import-error', [details.error]) }}
      </p>
      <p v-if="importState.blocks_activation">{{ $t('montage-import-failed-next-step') }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import adminService from '@/services/adminService'
import { formatUtcDateTime } from '@/utils'

const props = defineProps({
  roundId: Number,
  importState: Object
})

const job = computed(() => props.importState?.job || null)
const details = ref(null)

// warnings are dicts ({'duplicate import': '...'}) or plain strings
const warnings = computed(() =>
  (details.value?.warnings || []).map((warning) =>
    typeof warning === 'string' ? warning : Object.values(warning).join(' ')
  )
)

// One details fetch on load for a finished import; no polling (#622)
onMounted(() => {
  if (job.value && ['succeeded', 'failed'].includes(job.value.status)) {
    adminService
      .getImportJob(props.roundId, job.value.id)
      .then((response) => {
        details.value = response.data
      })
      .catch(() => {
        details.value = null
      })
  }
})
</script>

<style scoped>
.round-import-status {
  margin-bottom: 16px;
}

.round-import-warning {
  white-space: pre-line;
}

.round-import-error {
  color: #bf3c2c;
  white-space: pre-line;
}
</style>
