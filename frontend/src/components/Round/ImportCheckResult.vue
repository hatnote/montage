<template>
  <div ref="root" class="import-check-result" tabindex="-1" data-testid="import-check-result">
    <cdx-message v-if="error" type="error">
      <p>{{ error }}</p>
      <p v-if="errorDetail" class="import-check-detail" lang="en" dir="ltr">{{ errorDetail }}</p>
    </cdx-message>
    <template v-if="result">
      <p class="import-check-summary">{{ summaryText }}</p>
      <ul class="import-check-counts">
        <li v-for="status in shownStatuses" :key="status">
          {{ $t('montage-round-check-count', [statusLabel(status), result.counts[status]]) }}
        </li>
      </ul>
      <cdx-message v-if="result.blocking" type="error">
        {{ $t('montage-round-check-blocking') }}
      </cdx-message>
      <cdx-message v-else-if="!result.importable_count" type="error">
        {{ $t('montage-round-check-nothing-to-import') }}
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
            isCategory
              ? $t('montage-round-check-same-name-category')
              : $t('montage-round-check-same-name-list')
          }}
        </p>
        <ul class="import-check-groups">
          <li v-for="(group, index) in result.same_name_groups" :key="'group-' + index">
            <span v-for="(member, i) in group" :key="member.row">
              <template v-if="i > 0">
                <span class="import-check-separator" aria-hidden="true"> ⟷ </span>
                <span class="visually-hidden">{{ ' ' + $t('montage-round-check-and') + ' ' }}</span>
              </template>
              <span v-if="isCategory" class="import-check-name">{{ member.commons_name }}</span>
              <span v-else class="import-check-name">{{
                $t('montage-round-check-group-member', [member.commons_name, member.row])
              }}</span>
            </span>
          </li>
        </ul>
      </div>

      <template v-if="result.issues && result.issues.length">
        <p v-if="result.issues_truncated">
          {{ $t('montage-round-check-truncated', [result.issues.length, result.issues_total]) }}
        </p>
        <div
          class="import-check-table-wrapper"
          tabindex="0"
          role="region"
          :aria-label="$t('montage-round-check-issues-label')"
        >
          <table class="import-check-table">
            <caption class="visually-hidden">
              {{
                $t('montage-round-check-issues-label')
              }}
            </caption>
            <thead>
              <tr>
                <th scope="col">{{ $t('montage-round-check-col-row') }}</th>
                <th scope="col">{{ $t('montage-round-check-col-name') }}</th>
                <th scope="col">{{ $t('montage-round-check-col-file-id') }}</th>
                <th scope="col">{{ $t('montage-round-check-col-commons-name') }}</th>
                <th scope="col">{{ $t('montage-round-check-col-status') }}</th>
                <th scope="col">{{ $t('montage-round-check-col-reason') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="issue in result.issues"
                :key="issue.row"
                :class="{ 'import-check-blocking-row': blocks(issue) }"
              >
                <td>{{ issue.row }}</td>
                <td>{{ issue.name_as_written }}</td>
                <td>{{ issue.file_id_as_written }}</td>
                <td>{{ issue.commons_name }}</td>
                <td>
                  {{ statusLabel(issue.status) }}
                  <strong v-if="blocks(issue)">{{ $t('montage-round-check-blocks') }}</strong>
                </td>
                <td lang="en" dir="ltr">{{ issue.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <p v-if="downloadUrl && result.importable_count">
        <a :href="downloadUrl" download>{{ $t('montage-round-check-download') }}</a>
      </p>
      <p v-if="issuesUrl && result.issues_total">
        <a :href="issuesUrl" download>{{ $t('montage-round-check-download-issues') }}</a>
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxMessage } from '@wikimedia/codex'

const { t: $t } = useI18n()

const props = defineProps({
  result: { type: Object, default: null },
  error: { type: String, default: null },
  errorDetail: { type: String, default: null },
  downloadUrl: { type: String, default: null },
  issuesUrl: { type: String, default: null }
})

const root = ref(null)
// RoundNew moves focus here once a check has finished
defineExpose({ focus: () => root.value?.focus() })

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

const isCategory = computed(() => props.result?.import_method === 'category')

// statuses with at least one row; 'ok' always
const shownStatuses = computed(() =>
  allStatuses.filter((status) => status === 'ok' || props.result?.counts?.[status])
)

const summaryText = computed(() => {
  const result = props.result
  return isCategory.value
    ? $t('montage-round-check-summary-category', [result.total_rows, result.importable_count])
    : $t('montage-round-check-summary', [result.total_rows, result.importable_count])
})

// a row blocks only where the check as a whole blocks (lists, not categories)
const blocks = (issue) => !!props.result?.blocking && blockingStatuses.includes(issue.status)

// montage-round-check-status-ok, -renamed, -duplicate, -unknown-name,
// -unknown-file-id, -malformed-file-id, -same-name
const statusLabel = (status) => $t('montage-round-check-status-' + status.replaceAll('_', '-'))
</script>

<style scoped>
.import-check-result {
  margin-top: 12px;
  margin-bottom: 12px;
}

.import-check-result:focus {
  outline: none;
}

.import-check-counts {
  margin: 4px 0 8px;
  padding-left: 20px;
}

.import-check-detail {
  white-space: pre-line;
  font-size: 0.875em;
}

.import-check-table-wrapper {
  max-height: 320px;
  overflow: auto;
  margin-top: 8px;
}

.import-check-table-wrapper:focus-visible {
  outline: 2px solid #36c;
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

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
