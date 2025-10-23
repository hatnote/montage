<template>
  <div style="display: flex">
    <div style="flex: 6">
      <div>
        <h3>{{ $t('montage-round-deadline') }}</h3>
        <p>
          <span style="color: black">{{ round.deadline_date.split('T')[0] }}</span> ·
          {{ $t('montage-round-vote-ending', [remainingDays]) }}
        </p>
      </div>
      <div style="margin-top: 24px; min-height: 80px">
        <h3>{{ $t('montage-directions') }}</h3>
        <p v-if="round.directions">{{ round.directions }}</p>
        <p v-else>{{ $t('montage-round-no-direction-given') }}</p>
      </div>
      <div style="margin-top: 24px" v-if="roundDetails?.quorum">
        <h3>{{ $t('montage-label-round-quorum') }}</h3>
        <p>{{ $t('montage-round-quorum-per-photo', [roundDetails.quorum]) }}</p>
      </div>
      <div style="margin-top: 24px">
        <h3>{{ $t('montage-label-round-jurors') }}</h3>
        <div style="display: flex; flex-wrap: wrap">
          <div
            v-for="juror in roundDetails?.jurors"
            :key="juror.username"
            style="
              width: 220px;
              display: flex;
              flex-direction: column;
              margin-top: 16px;
              margin-bottom: 16px;
            "
          >
            <user-avatar-with-name :coordinators="[juror]" />
            <div style="display: flex; flex-direction: column; margin-top: 8px">
              <p style="font-size: 26px" v-if="juror?.stats?.total_tasks">
                {{
                   (100 - juror.stats.percent_tasks_open).toFixed(1)
                }}
                %
              </p>
              <p style="font-size: 26px" v-else>N/A</p>
              <p style="color: black">
                {{
                  $t('montage-progress-status', [
                    juror.stats.total_tasks - juror.stats.total_open_tasks,
                    juror.stats.total_tasks
                  ])
                }}
              </p>
              <p class="greyed">
                {{ $t('montage-vote-image-remains', [juror?.stats.total_open_tasks]) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div style="flex: 4">
      <div class="round-file-info">
        <h4>{{ $t('montage-round-file-info') }}</h4>
        <p>
          <strong>{{ $t('montage-round-file-type') }}:</strong>
          {{ roundResults?.counts.all_mimes.join(', ') }}
        </p>
        <p>
          <strong>{{ $t('montage-round-open-task-percentage') }}:</strong>
          {{ roundResults?.counts.percent_tasks_open }}
        </p>
        <p>
          <strong>{{ $t('montage-round-cancelled-tasks') }}:</strong>
          {{ rroundResults?.counts.total_cancelled_tasks }}
        </p>
        <p>
          <strong>{{ $t('montage-round-disqualified-files') }}:</strong>
          {{ roundResults?.counts.total_disqualified_entries }}
        </p>
        <p>
          <strong>{{ $t('montage-round-open-tasks') }}:</strong>
          {{ roundResults?.counts.total_open_tasks }}
        </p>
        <p>
          <strong>{{ $t('montage-round-files') }}:</strong>
          {{ roundResults?.counts.total_round_entries }}
        </p>
        <p>
          <strong>{{ $t('montage-round-tasks') }}:</strong> {{ roundResults?.counts.total_tasks }}
        </p>
        <p>
          <strong>{{ $t('montage-round-uploaders') }}:</strong>
          {{ roundResults?.counts.total_uploaders }}
        </p>
      </div>
      <cdx-accordion class="info-accordion">
        <p v-for="(value, key) in round.config" :key="key" style="display: flex">
          <span v-if="key !== 'allowed_filetypes'">{{
            $t('montage-round-' + key.replaceAll('_', '-'))
          }}</span>
          <span v-if="key !== 'allowed_filetypes'" style="margin-left: auto">
            {{ value }}
          </span>
        </p>
        <template #title> {{ $t('montage-round-file-setting') }} </template>
      </cdx-accordion>
      <cdx-accordion class="info-accordion">
        <template #title> {{ $t('montage-round-voting-details') }} </template>
      </cdx-accordion>
    </div>
  </div>
  <div
    class="round__actions"
    style="display: flex; justify-content: end; gap: 16px; margin-top: 16px"
  >
    <cdx-button v-if="round.status === 'paused'" @click="activateRound" action="progressive">
      <play style="font-size: 6px" />{{ $t('montage-round-activate') }}
    </cdx-button>

    <cdx-button v-if="round.status === 'active'" @click="pauseRound">
      <pause style="font-size: 6px" /> {{ $t('montage-round-pause') }}
    </cdx-button>

    <cdx-button v-if="round.status !== 'finalized'" @click="finalizeRound" action="progressive">
      <check style="font-size: 6px" />{{ $t('montage-round-finalize') }}
    </cdx-button>

    <cdx-button @click="downloadResults">
      <download style="font-size: 6px" /> {{ $t('montage-round-download-results') }}
    </cdx-button>

    <cdx-button @click="downloadEntries">
      <image-multiple style="font-size: 6px" /> {{ $t('montage-round-download-entries') }}
    </cdx-button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'

// Components
import { CdxButton, CdxAccordion } from '@wikimedia/codex'
import UserAvatarWithName from '../UserAvatarWithName.vue'

// Icons
import Play from 'vue-material-design-icons/Play.vue'
import Pause from 'vue-material-design-icons/Pause.vue'
import Check from 'vue-material-design-icons/Check.vue'
import Download from 'vue-material-design-icons/Download.vue'
import ImageMultiple from 'vue-material-design-icons/ImageMultiple.vue'

const { t: $t } = useI18n()
const props = defineProps({
  round: Object
})

const roundDetails = ref(null)
const roundResults = ref(null)

const remainingDays = computed(() => {
  const deadline = new Date(props.round.deadline_date)
  const today = new Date()
  const diffTime = deadline - today
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays
})

const activateRound = () => {
  adminService
    .activateRound(props.round.id)
    .then((data) => {
      if (data.status === 'success') {
        alertService.success($t('montage-round-activated'))
      }

      // Refresh the page
      location.reload()
    })
    .catch(alertService.error)
}

const pauseRound = () => {
  adminService
    .pauseRound(props.round.id)
    .then((data) => {
      if (data.status === 'success') {
        alertService.success($t('montage-round-paused'))
      }

      // Refresh the page
      location.reload()
    })
    .catch(alertService.error)
}

const finalizeRound = () => {
  const completionPercentage = Math.round(roundDetails.value?.is_closable || 0)

  const confirmText = completionPercentage === 100
    ? "All votes are done. Click OK to confirm finalize round."
    : `Only ${completionPercentage}% of votes are complete. Click OK to finalize anyway.`

  const shouldFinalize = confirm(confirmText)

  if (shouldFinalize) {
    adminService
      .finalizeRound(props.round.id)
      .then((data) => {
        if (data.status === 'success') {
          alertService.success($t('montage-round-finalized'))
        }
        // Refresh the page
        location.reload()
      })
      .catch(alertService.error)
  }
}

function downloadResults() {
  const url = adminService.downloadRound(props.round.id)
  window.open(url)
}

function downloadEntries() {
  const url = adminService.downloadEntries(props.round.id)
  window.open(url)
}

function downloadReviews() {
  const url = adminService.downloadReviews(props.round.id)
  window.open(url)
}

function getRoundDetails(round) {
  adminService
    .getRound(round.id)
    .then((data) => {
      roundDetails.value = data.data
    })
    .catch(alertService.error)
}

function getRoundResults(round) {
  adminService
    .previewRound(round.id)
    .then((data) => {
      roundResults.value = data.data
    })
    .catch(alertService.error)
}

onMounted(() => {
  getRoundDetails(props.round)
  getRoundResults(props.round)
})
</script>

<style scoped>
.round {
  display: flex;
  flex-direction: column;
}

.juror-campaign-round-icon {
  background-color: blue;
  height: 56px;
  padding: 10px;
  border-radius: 50%;
}

.information-card .cdx-card__text {
  width: 100% !important;
}

.info-accordion {
  margin-top: 16px;
}

.round-file-info p {
  font-size: 14px;
}
</style>
