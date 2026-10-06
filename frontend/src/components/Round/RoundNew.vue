<template>
  <div class="juror-campaign-round-card">
    <div class="round-header">
      <thumbs-up-down
        v-if="formData.vote_method === 'yesno'"
        class="juror-campaign-round-icon"
        :size="36"
        fillColor="white"
        style="background-color: grey"
      />
      <star-outline
        v-if="formData.vote_method === 'rating'"
        class="juror-campaign-round-icon"
        :size="36"
        fillColor="white"
        style="background-color: grey"
      />
      <sort
        v-if="formData.vote_method === 'ranking'"
        class="juror-campaign-round-icon"
        :size="36"
        fillColor="white"
        style="background-color: grey"
      />
      <div class="round-info">
        <h2>{{ formData.name }}</h2>
        <p>{{ $t(getVotingName(formData.vote_method)) }}</p>
      </div>
    </div>

    <div class="card-container" :aria-busy="isLoading || isChecking">
      <cdx-card class="information-card" style="margin-top: 24px">
        <template #supporting-text>
          <div class="form-container">
            <div class="form-left">
              <cdx-field>
                <cdx-text-input v-model="formData.name" />
                <template #label>{{ $t('montage-round-name') }}</template>
              </cdx-field>
              <div class="flex-row">
                <cdx-field>
                  <date-picker
                    v-model:value="formData.deadline_date"
                    type="date"
                    format="YYYY-MM-DD"
                    placeholder="YYYY-MM-DD"
                    value-type="format"
                  ></date-picker>
                  <template #label>{{ $t('montage-round-deadline') }}</template>
                </cdx-field>
                <cdx-field>
                  <cdx-select
                    v-model:selected="formData.vote_method"
                    :menu-items="
                      voteMethods.map((method) => ({
                        label: $t(getVotingName(method)),
                        value: method
                      }))
                    "
                  />
                  <template #label>{{ $t('montage-round-vote-method') }}</template>
                </cdx-field>
              </div>
              <cdx-field v-if="roundIndex === 0" :disabled="sourceLocked">
                <cdx-radio
                  v-for="source in importSourceMethods"
                  :key="'radio-' + source.value"
                  v-model="selectedImportSource"
                  :input-value="source.value"
                >
                  {{ source.label }}
                </cdx-radio>
                <template #label>{{ $t('montage-round-source') }}</template>
                <template #help-text>
                  <p v-if="selectedImportSource === 'category'" class="help-text">
                    {{ $t('montage-round-source-category-help') }}
                  </p>
                  <p v-if="selectedImportSource === 'csv'" class="help-text">
                    {{ $t('montage-round-source-csv-help') }}
                  </p>
                  <p v-if="selectedImportSource === 'selected'" class="help-text">
                    {{ $t('montage-round-source-selected-help') }}
                  </p>
                </template>
              </cdx-field>
              <cdx-field
                v-if="roundIndex === 0 && selectedImportSource === 'category'"
                :disabled="sourceLocked"
              >
                <cdx-lookup
                  data-testid="montage-round-category"
                  v-model:selected="importSourceValue.category"
                  v-model:input-value="categoryInput"
                  :menu-items="categoryOptions"
                  :placeholder="$t('montage-round-category-placeholder')"
                  @input="searchCategory"
                >
                  <template #label>{{ $t('montage-round-category-label') }}</template>
                  <template #no-results>{{ $t('montage-round-no-category') }}</template>
                </cdx-lookup>
                <template v-if="categoryInput && !importSourceValue.category" #help-text>
                  <p class="help-text">{{ $t('montage-round-category-pick') }}</p>
                </template>
              </cdx-field>
              <cdx-field
                v-if="roundIndex === 0 && selectedImportSource === 'csv'"
                :disabled="sourceLocked"
              >
                <cdx-text-input input-type="url" v-model="importSourceValue.csv_url" />
                <template #label>{{ $t('montage-round-file-url') }}</template>
              </cdx-field>
              <cdx-field
                v-if="roundIndex === 0 && selectedImportSource === 'selected'"
                :disabled="sourceLocked"
              >
                <cdx-text-area v-model="importSourceValue.file_names" rows="5" />
                <template #label>{{ $t('montage-round-file-list') }}</template>
              </cdx-field>
              <div v-if="roundIndex === 0" class="import-check">
                <cdx-button
                  data-testid="check-source-button"
                  :disabled="isChecking || isLoading || !sourceFilled"
                  @click="runCheck()"
                >
                  {{
                    isChecking
                      ? $t('montage-round-check-running')
                      : $t('montage-round-check-source')
                  }}
                </cdx-button>
                <p v-if="!checkResult && !checkError" class="help-text">
                  {{ $t('montage-round-check-required') }}
                </p>
                <import-check-result
                  v-if="checkResult || checkError"
                  ref="checkResultPanel"
                  :result="checkResult"
                  :error="checkError"
                  :error-detail="checkErrorDetail"
                  :download-url="checkDownloadUrl"
                  :issues-url="checkIssuesUrl"
                />
              </div>
              <cdx-field v-if="roundIndex === 0">
                <cdx-text-area v-model="formData.directions" rows="3" />
                <template #label>{{ $t('montage-directions') }}</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0">
                <cdx-radio
                  v-for="source in showStatsOptions"
                  :key="'show_stats-' + source.value"
                  v-model="formData.show_stats"
                  :input-value="source.value"
                >
                  {{ source.label }}
                </cdx-radio>
                <template #label>{{ $t('montage-label-round-stats') }}</template>
                <template #description>
                  <p>{{ $t('montage-description-round-stats') }}</p>
                </template>
              </cdx-field>
              <cdx-field>
                <cdx-text-input v-model="formData.quorum" input-type="number" />
                <template #label>{{ $t('montage-label-round-quorum') }}</template>
                <template #description>
                  <p>{{ $t('montage-round-quorum-description') }}</p>
                </template>
              </cdx-field>
              <cdx-field>
                <UserList
                  :users="formData.jurors"
                  @update:selectedUsers="formData.jurors = $event"
                  data-testid="userlist-search"
                />
                <template #label>{{ $t('montage-label-round-jurors') }}</template>
                <template #help-text>
                  <p>{{ $t('montage-round-jurors-description') }}</p>
                </template>
              </cdx-field>
              <cdx-field v-if="thresholds">
                <cdx-select
                  v-model:selected="formData.threshold"
                  :menu-items="thresholdOptions"
                  :default-label="$t('montage-round-threshold-default')"
                />
                <template #label>{{ $t('montage-round-threshold') }}</template>
                <template #description>
                  <p>{{ $t('montage-round-threshold-description') }}</p>
                </template>
              </cdx-field>
            </div>
            <div class="form-right" v-if="roundIndex === 0">
              <p>{{ $t('montage-round-file-setting') }}</p>
              <cdx-field>
                <cdx-checkbox
                  v-for="key in fileSettingsOptions"
                  :key="key"
                  v-model="formData.config[key]"
                >
                  {{ $t('montage-round-' + key.replaceAll('_', '-')) }}
                </cdx-checkbox>
              </cdx-field>
              <cdx-field v-if="formData.config.dq_by_resolution">
                <cdx-text-input
                  v-model="formData.config.min_resolution"
                  input-type="number"
                  :min="100000"
                  :step="100000"
                  placeholder="2000000"
                />
                <template #label>{{ $t('montage-round-min-resolution') }}</template>
                <template #help-text>
                  <p>{{ $t('montage-round-min-resolution-help') }}</p>
                </template>
              </cdx-field>
            </div>
          </div>
          <!-- announced to screen readers: check results, errors, changes -->
          <p class="visually-hidden" role="status" aria-live="polite">{{ announcement }}</p>
          <cdx-message v-if="saveError" type="error" class="save-error">
            <p>{{ saveError }}</p>
            <p v-if="saveErrorDetail" class="save-error-detail" lang="en" dir="ltr">
              {{ saveErrorDetail }}
            </p>
          </cdx-message>
          <div class="button-group">
            <p v-if="saveHint" id="round-save-hint" class="help-text save-hint">{{ saveHint }}</p>
            <cdx-button
              :disabled="isLoading || (roundIndex !== 0 && !thresholds) || !!saveHint"
              :aria-describedby="saveHint ? 'round-save-hint' : undefined"
              action="progressive"
              weight="primary"
              data-testid="add-round-button"
              @click="submitRound()"
            >
              <check class="icon-small" />
              {{
                isLoading && roundIndex === 0
                  ? $t('montage-round-saving-with-files')
                  : $t('montage-round-add')
              }}
            </cdx-button>
            <cdx-button
              action="destructive"
              :disabled="isLoading"
              @click="cancelRound()"
              data-testid="cancel-round-button"
            >
              <close class="icon-small" /> {{ $t('montage-btn-cancel') }}
            </cdx-button>
          </div>
        </template>
      </cdx-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import alertService from '@/services/alertService'
import dataService from '@/services/dataService'
import adminService from '@/services/adminService'
import dialogService from '@/services/dialogService'

import { useRoute } from 'vue-router'
import { getVotingName } from '@/utils'

import {
  CdxCard,
  CdxButton,
  CdxField,
  CdxTextInput,
  CdxSelect,
  CdxRadio,
  CdxTextArea,
  CdxCheckbox,
  CdxLookup,
  CdxMessage
} from '@wikimedia/codex'

// Components
import UserList from '@/components/UserList.vue'
import ImportCheckResult from '@/components/Round/ImportCheckResult.vue'

// Icons
import ThumbsUpDown from 'vue-material-design-icons/ThumbsUpDown.vue'
import StarOutline from 'vue-material-design-icons/StarOutline.vue'
import Sort from 'vue-material-design-icons/Sort.vue'
import Check from 'vue-material-design-icons/Check.vue'
import Close from 'vue-material-design-icons/Close.vue'
const { t: $t } = useI18n()

const props = defineProps({
  showAddRoundForm: Boolean,
  rounds: Array
})

const emit = defineEmits(['update:showAddRoundForm', 'reloadCampaignState'])

const route = useRoute()
const campaignId = route.params.id.split('-')[0]

const voteMethods = ['yesno', 'rating', 'ranking']
const fileSettingsOptions = [
  'dq_by_uploader',
  'dq_by_resolution',
  'dq_by_upload_date',
  'dq_coords',
  'dq_maintainers',
  'dq_organizers',
  'show_filename',
  'show_link',
  'show_resolution'
]
const showStatsOptions = [
  { label: $t('montage-option-yes'), value: true },
  { label: $t('montage-option-no'), value: false }
]
const importSourceMethods = [
  { label: $t('montage-round-source-category'), value: 'category' },
  { label: $t('montage-round-source-csv'), value: 'csv' },
  { label: $t('montage-round-source-filelist'), value: 'selected' }
]

const roundIndex = props.rounds.length
const prevRound = roundIndex ? props.rounds[roundIndex - 1] : null
const thresholds = ref(null)
const thresholdOptions = ref(null)
const isLoading = ref(false)

const formData = ref({
  name: `Round ${roundIndex + 1}`,
  vote_method: roundIndex !== 0 && roundIndex < 3 ? voteMethods[roundIndex] : 'yesno',
  deadline_date: null,
  show_stats: false,
  quorum: 1,
  threshold: null,
  jurors: roundIndex !== 0 ? prevRound.jurors.map((juror) => juror.username) : [],
  directions: '',
  config: {
    dq_by_resolution: false,
    min_resolution: 2000000,
    dq_by_uploader: true,
    dq_by_upload_date: false,
    dq_coords: false,
    dq_maintainers: false,
    dq_organizers: false,
    show_filename: false,
    show_link: false,
    show_resolution: false
  }
})

// States for import source
const selectedImportSource = ref('category')
const importSourceValue = ref({
  category: '',
  csv_url: '',
  file_names: ''
})

// Import check (#510): the source is checked before the round is saved; the
// import then takes exactly the checked list (check_token).
const checkResult = ref(null)
const checkError = ref(null)
const checkErrorDetail = ref(null) // server text (English), shown with the message
const isChecking = ref(false)
let checkRequestCount = 0
const checkResultPanel = ref(null)
const categoryInput = ref('')
// the round could not be saved (shown next to Save)
const saveError = ref(null)
const saveErrorDetail = ref(null)
const announcement = ref('')

// the source cannot change while it is checked or saved: the save would
// still send the old check
const sourceLocked = computed(() => isChecking.value || isLoading.value)

// why Save is disabled for a first round (also its aria-describedby)
const saveHint = computed(() => {
  if (roundIndex !== 0 || isChecking.value) return null
  if (!checkResult.value) return $t('montage-round-check-required')
  if (checkResult.value.blocking) return $t('montage-round-check-blocking')
  if (!checkResult.value.importable_count) return $t('montage-round-check-nothing-to-import')
  return null
})

const announce = (text) => {
  announcement.value = ''
  nextTick(() => {
    announcement.value = text
  })
}

const sourceFilled = computed(() => {
  const value = importSourceValue.value
  if (selectedImportSource.value === 'category') return !!value.category
  if (selectedImportSource.value === 'csv') return !!value.csv_url.trim()
  return !!value.file_names.trim()
})

const checkDownloadUrl = computed(() =>
  checkResult.value ? adminService.downloadImportCheck(campaignId, checkResult.value.token) : null
)
const checkIssuesUrl = computed(() =>
  checkResult.value
    ? adminService.downloadImportCheckIssues(campaignId, checkResult.value.token)
    : null
)

const clearCheck = () => {
  const hadCheck = checkResult.value || checkError.value
  checkRequestCount += 1 // a response still on its way is ignored
  checkResult.value = null
  checkError.value = null
  checkErrorDetail.value = null
  saveError.value = null
  saveErrorDetail.value = null
  isChecking.value = false
  if (hadCheck) announce($t('montage-round-check-cleared'))
}

// any change to the source makes the check stale
watch([selectedImportSource, importSourceValue], clearCheck, { deep: true })

const buildSourcePayload = () => {
  const payload = { import_method: selectedImportSource.value }
  if (selectedImportSource.value === 'category') {
    payload.category = importSourceValue.value.category
  } else if (selectedImportSource.value === 'csv') {
    payload.csv_url = importSourceValue.value.csv_url.trim()
  } else if (selectedImportSource.value === 'selected') {
    // blank lines are kept so that row numbers match the text area's lines
    payload.file_names = importSourceValue.value.file_names.split('\n')
  }
  return payload
}

const errorText = (error) => {
  const data = error?.response?.data
  return data?.detail || data?.message || error?.message || $t('montage-something-went-wrong')
}

const checkSummary = (result) =>
  result.import_method === 'category'
    ? $t('montage-round-check-summary-category', [result.total_rows, result.importable_count])
    : $t('montage-round-check-summary', [result.total_rows, result.importable_count])

const runCheck = () => {
  checkRequestCount += 1
  const requestNumber = checkRequestCount
  checkResult.value = null
  checkError.value = null
  checkErrorDetail.value = null
  saveError.value = null
  saveErrorDetail.value = null
  isChecking.value = true
  adminService
    .checkImport(campaignId, buildSourcePayload())
    .then((response) => {
      if (requestNumber !== checkRequestCount) return
      checkResult.value = response.data
      announce(checkSummary(response.data))
    })
    .catch((error) => {
      if (requestNumber !== checkRequestCount) return
      // shown in the panel (a toast disappears): source errors and others
      checkError.value = $t('montage-round-check-failed-short')
      checkErrorDetail.value = errorText(error)
      announce(checkError.value)
    })
    .finally(() => {
      if (requestNumber === checkRequestCount) {
        isChecking.value = false
        nextTick(() => checkResultPanel.value?.focus())
      }
    })
}

const categoryOptions = ref([])
function searchCategory(name) {
  if (name.length < 2) {
    return
  }

  dataService.searchCategory(name).then((response) => {
    const cats = response[1]?.map((element) => element.substring(9))
    categoryOptions.value = cats.map((cat) => ({ label: cat, value: cat }))
  })
}

const cancelRound = () => {
  emit('reload-campaign-state')
  emit('update:showAddRoundForm', false)
}

// a check is valid for 7 days (the server refuses older ones)
const checkExpired = (result) => {
  const expires = Date.parse(result?.expires_at || '')
  return !Number.isNaN(expires) && expires - 60 * 1000 <= Date.now()
}

const submitRound = () => {
  if (!formData.value.deadline_date) {
    alertService.error({
      message: $t('montage-required-voting-deadline')
    })
    return
  }

  if (!formData.value.name || (formData.value.quorum > 0 && formData.value.jurors.length === 0)) {
    alertService.error({
      message: $t('montage-required-fill-inputs')
    })
    return
  }

  // Check if the round is the first round
  if (roundIndex === 0) {
    if (!checkResult.value || checkResult.value.blocking) {
      alertService.error({ message: $t('montage-round-check-required') })
      return
    }
    if (!checkResult.value.importable_count) {
      alertService.error({ message: $t('montage-round-check-nothing-to-import') })
      return
    }
    if (checkExpired(checkResult.value)) {
      checkResult.value = null
      checkError.value = $t('montage-round-check-expired')
      announce(checkError.value)
      return
    }
    const payload = {
      name: formData.value.name,
      vote_method: formData.value.vote_method,
      deadline_date: formData.value.deadline_date + 'T00:00:00',
      show_stats: formData.value.show_stats,
      quorum: formData.value.quorum,
      jurors: formData.value.jurors,
      directions: formData.value.directions,
      config: formData.value.config,
      // the round and its files are saved together, or not at all (#447)
      import: {
        import_method: selectedImportSource.value,
        check_token: checkResult.value.token
      }
    }

    isLoading.value = true
    saveError.value = null
    saveErrorDetail.value = null
    adminService
      .addRound(campaignId, payload)
      .then((resp) => {
        const imported = resp.data.import?.new_round_entry_count || 0
        alertService.success($t('montage-round-added-with-files', [imported]))
        showImportResult(resp.data.import)
      })
      .catch(showImportError)
      .finally(() => {
        isLoading.value = false
      })
  } else {
    if (!prevRound.id) {
      alertService.error($t('montage-something-went-wrong'))
      return
    }
    if (thresholds.value && !formData.value.threshold) {
      alertService.error({
        message: $t('montage-required-threshold')
      })
      return
    }

    const payload = {
      next_round: {
        name: formData.value.name,
        vote_method: formData.value.vote_method,
        quorum: formData.value.quorum,
        deadline_date: formData.value.deadline_date + 'T00:00:00',
        jurors: formData.value.jurors
      },
      threshold: formData.value.threshold
    }

    adminService
      .advanceRound(prevRound.id, payload)
      .then(() => {
        alertService.success($t('montage-round-added'))
        console.log('Round created successfully')
      })
      .catch(alertService.error)
      .finally(() => {
        emit('reload-campaign-state')
        emit('update:showAddRoundForm', false)
      })
  }
}

const closeForm = () => {
  emit('reload-campaign-state')
  emit('update:showAddRoundForm', false)
}

const showImportResult = (result) => {
  if (result && result.warnings && result.warnings.length) {
    const { warnings = [], disqualified = [] } = result

    const warningsList = warnings.map((warning) => Object.values(warning).pop())
    const filesList = disqualified
      .map((image) => `${image.entry.name} – ${image.dq_reason}`.trim())
      .filter((value, index, array) => array.indexOf(value) === index)
      .join('\n')

    const text = `${warningsList.join('\n\n')}\n\n${filesList}`

    dialogService().show({
      title: $t('montage-round-import-warning'),
      content: text,
      primaryAction: {
        label: $t('montage-btn-ok'),
        actionType: 'progressive'
      },
      onPrimary: closeForm,
      // closed with the X or Escape: the round is saved all the same
      onClose: closeForm
    })
  } else {
    closeForm()
  }
}

// The server refused or failed the save: nothing was saved, and the form
// stays as entered. Without a response the round may have been saved, so
// the campaign is reloaded and the coordinator told to look before saving
// again.
const showImportError = (error) => {
  const errorType = error?.response?.data?.error_type
  if (errorType === 'import_check_expired') {
    checkResult.value = null
    checkError.value = $t('montage-round-check-expired')
  } else if (errorType === 'import_check_blocked') {
    checkResult.value = null
    checkError.value = $t('montage-round-save-blocked-recheck')
    checkErrorDetail.value = errorText(error)
  } else if (errorType === 'import_empty') {
    checkResult.value = null
    checkError.value = $t('montage-round-check-nothing-to-import')
  } else if (errorType === 'import_check_required') {
    checkResult.value = null
    checkError.value = $t('montage-round-reload-page')
  } else if (!error?.response) {
    emit('reload-campaign-state')
    saveError.value = $t('montage-round-save-unknown')
  } else {
    saveError.value = $t('montage-round-not-saved')
    saveErrorDetail.value = errorText(error)
  }
  announce(checkError.value || saveError.value)
}

watch(thresholds, (value) => {
  thresholdOptions.value = Object.entries(value).map(([key, value]) => ({
    label: `${(key * 10).toFixed(2)} / 10 (${value} images total)`,
    value: key
  }))
})

onMounted(() => {
  if (prevRound && prevRound.vote_method !== 'ranking') {
    adminService
      .previewRound(prevRound.id)
      .then((resp) => {
        thresholds.value = resp.data.thresholds
      })
      .catch(() => {
        thresholds.value = null
      })
  }
})
</script>

<style scoped>
.juror-campaign-round-card {
  display: flex;
  flex-direction: column;
}

.round-header {
  display: flex;
}

.juror-campaign-round-icon {
  background-color: grey;
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
}

.form-left {
  flex: 6;
  margin-right: 120px;
}

.flex-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
}

.form-right {
  flex: 4;
}

.button-group {
  display: flex;
  gap: 12px;
  justify-content: end;
  margin-top: 24px;
  margin-bottom: 12px;
}

.information-card .cdx-card__text {
  width: 100% !important;
}

.icon-small {
  font-size: 6px;
}

.save-error {
  margin-top: 16px;
}

.save-error-detail {
  white-space: pre-line;
  font-size: 0.875em;
}

.save-hint {
  margin: 0 auto 0 0;
  align-self: center;
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

.import-check {
  margin-bottom: 16px;
}
</style>
