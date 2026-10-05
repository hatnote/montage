<template>
  <div class="import-check-result" data-testid="import-check-result">
    <cdx-message v-if="error" type="error">{{ error }}</cdx-message>
    <template v-else-if="result">
      <p class="import-check-summary">
        {{ $t('montage-round-check-summary', [result.total_rows, result.importable_count]) }}
      </p>
      <ul class="import-check-counts">
        <li v-for="status in shownStatuses" :key="status">
          {{ statusLabel(status) }}: {{ result.counts[status] }}
        </li>
      </ul>
      <cdx-message v-if="result.blocking" type="error">
        {{ $t('montage-round-check-blocking') }}
      </cdx-message>
      <cdx-message v-else-if="!result.issues_total" type="success">
        {{ $t('montage-round-check-no-issues') }}
      </cdx-message>
      <p v-if="result.columns && result.columns.ignored && result.columns.ignored.length">
        {{ $t('montage-round-check-ignored-columns', [result.columns.ignored.join(', ')]) }}
      </p>

      <div v-if="result.same_name_groups && result.same_name_groups.length">
        <h4>{{ $t('montage-round-check-same-name-title') }}</h4>
        <p>
          {{
            result.import_method === 'category'
              ? $t('montage-round-check-same-name-category')
              : $t('montage-round-check-same-name-list')
          }}
        </p>
        <ul class="import-check-groups">
          <li v-for="(group, index) in result.same_name_groups" :key="'group-' + index">
            <span v-for="(member, i) in group" :key="member.row">
              <span v-if="i > 0" class="import-check-separator"> ⟷ </span>
              <span class="import-check-name">{{ member.commons_name }}</span>
              ({{ $t('montage-round-check-col-row') }} {{ member.row }})
            </span>
          </li>
        </ul>
      </div>

      <div v-if="result.issues && result.issues.length" class="import-check-table-wrapper">
        <p v-if="result.issues_truncated">
          {{ $t('montage-round-check-truncated', [result.issues.length, result.issues_total]) }}
        </p>
        <table class="import-check-table">
          <thead>
            <tr>
              <th>{{ $t('montage-round-check-col-row') }}</th>
              <th>{{ $t('montage-round-check-col-name') }}</th>
              <th>{{ $t('montage-round-check-col-file-id') }}</th>
              <th>{{ $t('montage-round-check-col-commons-name') }}</th>
              <th>{{ $t('montage-round-check-col-status') }}</th>
              <th>{{ $t('montage-round-check-col-reason') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="issue in result.issues"
              :key="issue.row"
              :class="{ 'import-check-blocking-row': blockingStatuses.includes(issue.status) }"
            >
              <td>{{ issue.row }}</td>
              <td>{{ issue.name_as_written }}</td>
              <td>{{ issue.file_id_as_written }}</td>
              <td>{{ issue.commons_name }}</td>
              <td>{{ statusLabel(issue.status) }}</td>
              <td>{{ issue.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="downloadUrl && result.importable_count">
        <a :href="downloadUrl" target="_blank" rel="noopener">
          {{ $t('montage-round-check-download') }}
        </a>
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxMessage } from '@wikimedia/codex'

const { t: $t } = useI18n()

const props = defineProps({
  result: { type: Object, default: null },
  error: { type: String, default: null },
  downloadUrl: { type: String, default: null }
})

const allStatuses = [
  'ok',
  'renamed',
  'duplicate',
  'unknown_name',
  'unknown_file_id',
  'malformed_file_id',
  'same_name'
]
const blockingStatuses = ['unknown_file_id', 'malformed_file_id', 'same_name']

// statuses with at least one row; 'ok' always
const shownStatuses = computed(() =>
  allStatuses.filter((status) => status === 'ok' || props.result?.counts?.[status])
)

// montage-round-check-status-ok, -renamed, -duplicate, -unknown-name,
// -unknown-file-id, -malformed-file-id, -same-name
const statusLabel = (status) => $t('montage-round-check-status-' + status.replaceAll('_', '-'))
</script>

<style scoped>
.import-check-result {
  margin-top: 12px;
  margin-bottom: 12px;
}

.import-check-counts {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.import-check-table-wrapper {
  max-height: 320px;
  overflow: auto;
  margin-top: 8px;
}

.import-check-table {
  border-collapse: collapse;
  font-size: 0.875em;
  width: 100%;
}

.import-check-table th,
.import-check-table td {
  border: 1px solid #c8ccd1;
  padding: 2px 6px;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.import-check-blocking-row {
  background-color: #fee7e6;
}

.import-check-name {
  font-family: monospace;
}
</style>
