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
        <p>
          {{ getVotingName(formData.vote_method) }}
        </p>
      </div>
    </div>

    <div class="card-container">
      <cdx-card class="information-card" style="margin-top: 24px">
        <template #supporting-text>
          <div class="form-container">
            <div class="form-left">
              <cdx-field>
                <cdx-text-input v-model="formData.name" />
                <template #label>Round Name</template>
              </cdx-field>
              <div class="flex-row">
                <cdx-field>
                  <cdx-text-input input-type="date" v-model="formData.deadline_date" />
                  <template #label>Voting Deadline</template>
                </cdx-field>
                <cdx-field>
                  <cdx-select v-model:selected="formData.vote_method" :menu-items="voteMethods.map((method) => ({ label: getVotingName(method), value: method }))
                    " />
                  <template #label>Vote Method</template>
                </cdx-field>
              </div>
              <cdx-field v-if="roundIndex === 0">
                <cdx-radio v-for="source in importSourceMethods" :key="'radio-' + source.value"
                  v-model="selectedImportSource" :input-value="source.value">
                  {{ source.label }}
                </cdx-radio>
                <template #label>Source</template>
                <template #help-text>
                  <p v-if="selectedImportSource === 'category'" class="help-text">
                    Category on Wikimedia Commons that gathers all contest images. Example of such
                    category may be e.g. "Images from Wiki Loves Monuments 2017 in Ghana".
                  </p>
                  <p v-if="selectedImportSource === 'csv'" class="help-text">
                    List of files saved as CSV and uploaded as a Google Sheet or Gist.
                  </p>
                  <p v-if="selectedImportSource === 'selected'" class="help-text">
                    List of files, one each line without File: prefix
                  </p>
                </template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'category'">
                <cdx-lookup v-model:selected="importSourceValue.category" :menu-items="categoryOptions"
                  placeholder="Enter category" @input="searchCategory">
                  <template #label>Enter category</template>
                  <template #no-results>No categories found.</template>
                </cdx-lookup>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'csv'">
                <cdx-text-input input-type="url" v-model="importSourceValue.csv_url" />
                <template #label>Enter File URL</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0 && selectedImportSource === 'selected'">
                <cdx-text-area v-model="importSourceValue.file_names" rows="5" />
                <template #label>List (One file per line)</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0">
                <cdx-text-area v-model="formData.directions" rows="3" />
                <template #label>Directions</template>
              </cdx-field>
              <cdx-field v-if="roundIndex === 0">
                <cdx-radio v-for="source in showStatsOptions" :key="'show_stats-' + source.value"
                  v-model="formData.show_stats" :input-value="source.value">
                  {{ source.label }}
                </cdx-radio>
                <template #label>Show own statistics (Beta)</template>
                <template #description>
                  <p>
                    Whether to show own voting statistics (e.g. number of accepted or declined
                    images) of juror for the round.
                  </p>
                </template>
              </cdx-field>
              <cdx-field>
                <cdx-text-input v-model="formData.quorum" input-type="number" />
                <template #label>Quorum</template>
                <template #description>
                  <p>The number of jurors that must vote on each image</p>
                </template>
              </cdx-field>
              <cdx-field>
                <UserList :users="formData.jurors" @update:selectedUsers="formData.jurors = $event" />
                <template #label>Jurors</template>
                <template #help-text>
                  <p>Enter the username of the juror you want to add to this round.</p>
                </template>
              </cdx-field>
              <cdx-field v-if="thresholds">
                <cdx-select v-model:selected="formData.threshold" :menu-items="thresholdOptions"
                  default-label="Choose an threshold" />
                <template #label>Threshold</template>
                <template #description>
                  <p>Minimal average rating for photo</p>
                </template>
              </cdx-field>
            </div>
            <div class="form-right" v-if="roundIndex === 0">
              <p>Round File Setting</p>
              <cdx-field>
                <cdx-checkbox v-for="key in fileSettingsOptions" :key="key" v-model="formData.config[key]">
                  {{ $t(key) }}
                </cdx-checkbox>
              </cdx-field>
              <cdx-field v-if="formData.config.dq_by_resolution">
                <cdx-text-input v-model="formData.config.min_resolution" input-type="number" />
                <template #label>Minimal resolution</template>
              </cdx-field>
            </div>
          </div>
          <div class="button-group">
            <cdx-button action="progressive" weight="primary" @click="submitRound()">
              <check class="icon-small" /> Add Round
            </cdx-button>
            <cdx-button action="destructive" @click="cancelRound()">
              <close class="icon-small" /> Cancel
            </cdx-button>
          </div>
        </template>
      </cdx-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
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

const props = defineProps({
  showAddRoundForm: Boolean,
  rounds: Array
})

const emit = defineEmits(['update:showAddRoundForm', 'reloadCampaignState'])

const route = useRoute()
const campaignId = route.params.id.split('-')[0]

const voteMethods = ['yesno', 'rating', 'ranking']
const fileSettingsOptions = [
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
  { label: 'Yes', value: true },
  { label: 'No', value: false }
]
const importSourceMethods = [
  { label: 'Category on Wikimedia Commons', value: 'category' },
  { label: 'File List URL', value: 'csv' },
  { label: 'File List', value: 'selected' }
]

const roundIndex = props.rounds.length
const prevRound = roundIndex ? props.rounds[roundIndex - 1] : null
const thresholds = ref(null)
const thresholdOptions = ref(null)

const formData = ref({
  name: `Round ${roundIndex + 1}`,
  vote_method: roundIndex !== 0 ? voteMethods[roundIndex] : 'yesno',
  deadline_date: null,
  show_stats: false,
  quorum: 1,
  threshold: null,
  jurors: roundIndex !== 0 ? prevRound.jurors.map((juror) => juror.username) : [],
  directions: '',
  config: {
    dq_by_resolution: false,
    min_resolution: 2000000,
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

    adminService
      .addRound(campaignId, payload)
      .then((resp) => {
        alertService.success('Round added successfully')

        if (selectedImportSource.value === 'selected') {
          importSourceValue.value.file_names = importSourceValue.value.file_names
            .split('\n')
            .filter((elem) => elem)
        }

        importCategory(resp.data.id)
      })
      .catch(alertService.error)
  } else {
    if (!prevRound.id) {
      alertService.error('Something went wrong. Please try again.')
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
      threshold: 0.5 //formData.value.threshold
    }

    adminService
      .advanceRound(prevRound.id, payload)
      .then(() => {
        alertService.success('Round added successfully')
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
}

watch(thresholds, (value) => {
  thresholdOptions.value = Object.entries(value).map(([key, value]) => ({
    label: `${(key * 10).toFixed(2)} / 10 (${value} images total)`,
    value: key
  }))
})

onMounted(() => {
  if (prevRound) {
    adminService.previewRound(prevRound.id).then((resp) => {
      thresholds.value = resp.data.thresholds
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
