<template>
  <!-- RoundNew moves focus here after a check or a refused save; the
       screen reader then reads the region's name (the summary or error) -->
  <div
    ref="root"
    class="import-check-result"
    tabindex="-1"
    role="region"
    aria-labelledby="import-check-title"
    data-testid="import-check-result"
  >
    <cdx-message v-if="error" type="error">
      <p id="import-check-title">{{ error }}</p>
      <p
        v-if="errorDetail"
        class="import-check-detail"
        :lang="errorDetailEnglish ? 'en' : undefined"
        :dir="errorDetailEnglish ? 'ltr' : undefined"
      >
        {{ errorDetail }}
      </p>
    </cdx-message>
    <template v-if="result">
      <p :id="error ? undefined : 'import-check-title'" class="import-check-summary">
        {{ summaryText }}
      </p>
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
      <cdx-message v-else-if="result.issues_total" type="warning">
        {{ $t('montage-round-check-warnings-only') }}
      </cdx-message>
      <cdx-message v-else type="success">
        {{ $t('montage-round-check-no-issues') }}
      </cdx-message>
      <p v-if="result.columns && result.columns.ignored && result.columns.ignored.length">
        {{ $t('montage-round-check-ignored-columns', [result.columns.ignored.join(', ')]) }}
      </p>

      <div v-if="result.same_name_groups && result.same_name_groups.length">
        <h3 class="import-check-heading">{{ $t('montage-round-check-same-name-title') }}</h3>
        <p>
          {{
            isCategory
              ? $t('montage-round-check-same-name-category')
              : $t('montage-round-check-same-name-list')
          }}
        </p>
        <ul class="import-check-groups">
          <li v-for="(group, index) in result.same_name_groups" :key="'group-' + index">
            <span v-for="(member, i) in group" :key="member.row" class="import-check-member">
              <template v-if="i > 0">
                <span class="import-check-separator" aria-hidden="true"> ⟷ </span>
                <span class="visually-hidden">{{ ' ' + $t('montage-round-check-and') + ' ' }}</span>
              </template>
              <bdi v-if="isCategory" class="import-check-name">{{ member.commons_name }}</bdi>
              <template v-else>
                <bdi class="import-check-name">{{ member.commons_name }}</bdi
                >{{ ' '
                }}<span class="import-check-row">{{
                  $t('montage-round-check-row-ref', [member.row])
                }}</span>
              </template>
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
          aria-labelledby="import-check-issues-caption"
        >
          <table class="import-check-table">
            <caption id="import-check-issues-caption" class="visually-hidden">
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
                <th scope="row">{{ issue.row }}</th>
                <td class="import-check-name-cell">
                  <bdi>{{ issue.name_as_written }}</bdi>
                </td>
                <td>{{ issue.file_id_as_written }}</td>
                <td class="import-check-name-cell">
                  <bdi>{{ issue.commons_name }}</bdi>
                </td>
                <td>
                  {{ statusLabel(issue.status) }}
                  <strong v-if="blocks(issue)">{{ $t('montage-round-check-blocks') }}</strong>
                </td>
                <td
                  class="import-check-name-cell"
                  :lang="reason(issue).english ? 'en' : undefined"
                  :dir="reason(issue).english ? 'ltr' : undefined"
                >
                  {{ reason(issue).text }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <p v-if="downloadUrl && result.importable_count">
        <a :href="downloadUrl" download>{{
          result.blocking
            ? $t('montage-round-check-download-partial')
            : $t('montage-round-check-download')
        }}</a>
        <template v-if="result.blocking">
          <br />{{ $t('montage-round-check-download-partial-help') }}
        </template>
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
import { reasonText } from '@/components/Round/importCheckText'

const { t: $t, te } = useI18n()

const props = defineProps({
  result: { type: Object, default: null },
  error: { type: String, default: null },
  errorDetail: { type: String, default: null },
  // the detail is the server's English text (not translated)
  errorDetailEnglish: { type: Boolean, default: false },
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
  'page_id',
  'revision_id',
  'ambiguous_id',
  'same_name'
]
const blockingStatuses = [
  'unknown_file_id',
  'malformed_file_id',
  'page_id',
  'revision_id',
  'ambiguous_id',
  'same_name'
]

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

const reason = (issue) => reasonText($t, te, issue)

// montage-round-check-status-ok, -renamed, -duplicate, -unknown-name,
// -unknown-file-id, -malformed-file-id, -page-id, -revision-id, -ambiguous-id,
// -same-name
const statusLabel = (status) => $t('montage-round-check-status-' + status.replaceAll('_', '-'))
</script>

<style scoped>
.import-check-result {
  margin-top: 12px;
  margin-bottom: 12px;
}

.import-check-result:focus-visible {
  outline: 1px dotted #72777d;
  outline-offset: 2px;
}

.import-check-heading {
  font-size: 1em;
  margin: 12px 0 4px;
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
  /* on narrow screens the table scrolls sideways instead of squeezing */
  min-width: 36rem;
}

.import-check-table th,
.import-check-table td {
  border: 1px solid #c8ccd1;
  padding: 2px 6px;
  text-align: start;
  vertical-align: top;
}

.import-check-table tbody th {
  font-weight: normal;
}

.import-check-name-cell {
  overflow-wrap: anywhere;
}

.import-check-blocking-row {
  background-color: #fee7e6;
}

.import-check-name {
  font-family: monospace;
  /* Commons names have no spaces; let them wrap on narrow screens */
  overflow-wrap: anywhere;
}

@media (max-width: 600px) {
  .import-check-member {
    display: block;
  }

  /* no scroll area inside the page scroll on phones */
  .import-check-table-wrapper {
    max-height: none;
  }
}

.import-check-row {
  white-space: nowrap;
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
