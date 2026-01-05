<template>
  <div class="juror-campaign-round-card">
    <div class="round-header">
      <thumbs-up-down v-if="formData.vote_method === 'yesno'" class="juror-campaign-round-icon" :size="36"
        fillColor="white" style="background-color: grey" />
      <star-outline v-if="formData.vote_method === 'rating'" class="juror-campaign-round-icon" :size="36"
        fillColor="white" style="background-color: grey" />
      <sort v-if="formData.vote_method === 'ranking'" class="juror-campaign-round-icon" :size="36" fillColor="white"
        style="background-color: grey" />
      <div class="round-info">
        <h2>{{ formData.name }}</h2>
        <p>{{ $t(getVotingName(formData.vote_method)) }}</p>
      </div>
    </div>

    <div class="card-container">
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
                  <date-picker v-model:value="formData.deadline_date" type="date" format="YYYY-MM-DD"
                    placeholder="YYYY-MM-DD" value-type="format"></date-picker>
                  <template #label>{{ $t('montage-round-deadline') }}</template>
                </cdx-field>
                <cdx-field>
                  <cdx-select v-model:selected="formData.vote_method" :menu-items="voteMethods.map((method) => ({
                    label: $t(getVotingName(method)),
                    value: method
                  }))
                    " />
                  <template #label>{{ $t('montage-round-vote-method') }}</template>
                </cdx-field>
              </div>
              <cdx-field v-if="roundIndex === 0">
                <cdx-radio v-for="source in importSourceMethods" :key="'radio-' + source.value"
                  v-model="selectedImportSource" :input-value="source.value">
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
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'category'">
                <cdx-lookup data-testid="montage-round-category" v-model:selected="importSourceValue.category" :menu-items="categoryOptions"
                  :placeholder="$t('montage-round-category-placeholder')" @input="searchCategory">
                  <template #label>{{ $t('montage-round-category-label') }}</template>
                  <template #no-results>{{ $t('montage-round-no-category') }}</template>
                </cdx-lookup>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'csv'">
                <cdx-text-input input-type="url" v-model="importSourceValue.csv_url" />
                <template #label>{{ $t('montage-round-file-url') }}</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'selected'">
                <cdx-text-area v-model="importSourceValue.file_names" rows="5" />
                <template #label>{{ $t('montage-round-file-list') }}</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0">
                <cdx-text-area v-model="formData.directions" rows="3" />
                <template #label>{{ $t('montage-directions') }}</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0">
                <cdx-radio v-for="source in showStatsOptions" :key="'show_stats-' + source.value"
                  v-model="formData.show_stats" :input-value="source.value">
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
                <UserList :users="formData.jurors" @update:selectedUsers="formData.jurors = $event" data-testid="userlist-search" />
                <template #label>{{ $t('montage-label-round-jurors') }}</template>
                <template #help-text>
                  <p>{{ $t('montage-round-jurors-description') }}</p>
                </template>
              </cdx-field>
              <cdx-field v-if="thresholds">
                <cdx-select v-model:selected="formData.threshold" :menu-items="thresholdOptions"
                  :default-label="$t('montage-round-threshold-default')" />
                <template #label>{{ $t('montage-round-threshold') }}</template>
                <template #description>
                  <p>{{ $t('montage-round-threshold-description') }}</p>
                </template>
              </cdx-field>
            </div>
            <div class="form-right" v-if="roundIndex === 0">
              <p>{{ $t('montage-round-file-setting') }}</p>
              <cdx-field>
                <cdx-checkbox v-for="key in fileSettingsOptions" :key="key" v-model="formData.config[key]">
                  {{ $t('montage-round-' + key.replaceAll('_', '-')) }}
                </cdx-checkbox>
              </cdx-field>
              <cdx-field v-if="formData.config.dq_by_resolution">
                <cdx-text-input v-model="formData.config.min_resolution" input-type="number" />
                <template #label>{{ $t('montage-round-min-resolution') }}</template>
              </cdx-field>
            </div>
          </div>
          <div class="button-group">
            <cdx-button :disabled="isLoading || (roundIndex !== 0 && !thresholds)" action="progressive" weight="primary" @click="submitRound()">
              <check class="icon-small" /> {{ $t('montage-round-add') }}
            </cdx-button>
            <cdx-button action="destructive" @click="cancelRound()" data-testid="cancel-round-button">
              <close class="icon-small" /> {{ $t('montage-btn-cancel') }}
            </cdx-button>
          </div>
        </template>
      </cdx-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
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
  CdxLookup
} from '@wikimedia/codex'

// Components
import UserList from '@/components/UserList.vue'

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
  emit('update:showAddRoundForm', false)
}

const submitRound = () => {
  if (!formData.value.deadline_date) {
    alertService.error({
      message: $t('montage-required-voting-deadline')
    });
    return;
  }

  if (
  !formData.value.name ||
  (formData.value.quorum > 0 && formData.value.jurors.length === 0)
) {
    alertService.error({
      message: $t('montage-required-fill-inputs')
    });
    return;
  } else {
    if (formData.value.threshold === null || formData.value.threshold === undefined) {
      alertService.error({
        message: $t('montage-round-threshold-required')
      })
      return
    }
  }

  // Check if the round is the first round
  if (roundIndex === 0) {
    const payload = {
      name: formData.value.name,
      vote_method: formData.value.vote_method,
      deadline_date: formData.value.deadline_date + 'T00:00:00',
      show_stats: formData.value.show_stats,
      quorum: formData.value.quorum,
      jurors: formData.value.jurors,
      directions: formData.value.directions,
      config: formData.value.config
    }

    isLoading.value = true
    adminService
      .addRound(campaignId, payload)
      .then((resp) => {
        alertService.success($t('montage-round-added'))

        if (selectedImportSource.value === 'selected') {
          importSourceValue.value.file_names = importSourceValue.value.file_names
            .split('\n')
            .filter((elem) => elem)
        }

        importCategory(resp.data.id)
      })
      .catch(alertService.error)
      .finally(() => {
        isLoading.value = false
      })
  } else {
    if (!prevRound.id) {
      alertService.error($t('montage-something-went-wrong'))
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

    if (!thresholds.value) {
      alertService.error({
        message: $t('montage-round-cannot-advance-no-votes')
      })
      return
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

const importCategory = (id) => {
  const payload = {
    import_method: selectedImportSource.value
  }

  if (selectedImportSource.value === 'category') {
    payload.category = importSourceValue.value.category
  } else if (selectedImportSource.value === 'csv') {
    payload.csv_url = importSourceValue.value.csv_url
  } else if (selectedImportSource.value === 'selected') {
    payload.file_names = importSourceValue.value.file_names
  }

  isLoading.value = true
  adminService
    .populateRound(id, payload)
    .then((response) => {
      if (response.data && response.data.warnings && response.data.warnings.length) {
        const { warnings = [], disqualified = [] } = response.data

        const warningsList = warnings.map((warning) => Object.values(warning).pop())
        const filesList = disqualified
          .map((image) => `${image.entry.name} – ${image.dq_reason}`.trim())
          .filter((value, index, array) => array.indexOf(value) === index)
          .join('\n')

        const text = `${warningsList.join('\n\n')}\n\n${filesList}`

        dialogService().show({
          title: 'Import Warning',
          content: text,
          primaryAction: {
            label: 'OK',
            actionType: 'progressive'
          },
          onPrimary: () => {
            emit('reload-campaign-state')
            emit('update:showAddRoundForm', false)
          }
        })
      } else {
        emit('reload-campaign-state')
        emit('update:showAddRoundForm', false)
      }
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
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
</style>
