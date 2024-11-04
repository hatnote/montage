<template>
  <div style="display: flex">
    <div style="flex: 6">
      <div>
        <h3>Voting deadline</h3>
        <p>
          <span style="color: black">{{ round.deadline_date.split('T')[0] }}</span> · in
          <span>{{ remainingDays }}</span> days
        </p>
      </div>
      <div style="margin-top: 24px; min-height: 80px">
        <h3>Directions</h3>
        <p v-if="round.directions">{{ round.directions }}</p>
        <p v-else>No directions provided.</p>
      </div>
      <!-- <div style="margin-top: 24px">
        <h3>Quorum</h3>
        <p>{{ round.quorum }} jurors per photo</p>
      </div> -->
      <div style="margin-top: 24px">
        <h3>Jurors</h3>
        <div style="display: flex; flex-wrap: wrap">
          <div v-for="juror in round.jurors" :key="juror.username" style="
              width: 220px;
              display: flex;
              flex-direction: column;
              margin-top: 16px;
              margin-bottom: 16px;
            ">
            <user-avatar-with-name :coordinators="[juror]" />
            <div style="display: flex; flex-direction: column; margin-top: 8px">
              <!-- <p style="font-size: 26px">
                {{
                  (
                    ((juror.stats.total_tasks - juror.stats.total_open_tasks) /
                      juror.stats.total_tasks) *
                    100
                  ).toFixed(0)
                }}
                %
              </p> -->
              <!-- <p style="color: black">
                {{ juror.stats.total_tasks - juror.stats.total_open_tasks }} out of
                {{ juror.stats.total_tasks }}
              </p>
              <p>{{ juror.stats.total_open_tasks }} remaining</p> -->
            </div>
          </div>
        </div>
      </div>
    </div>
    <div style="flex: 4">
      <div class="round__file-info">
        <h4>Round File Information</h4>
        <p><strong>File types:</strong> {{ round.config.allowed_filetypes.join(', ') }}</p>
        <!-- <p>
          <strong>Percentage of opened tasks:</strong> {{ round.details.percentage_opened_tasks }}%
        </p>
        <p><strong>Cancelled tasks:</strong> {{ round.details.cancelled_tasks }}</p>
        <p><strong>Disqualified files:</strong> {{ round.details.disqualified_files }}</p>
        <p><strong>Open tasks:</strong> {{ round.details.open_tasks }}</p>
        <p><strong>Files:</strong> {{ round.details.files }}</p>
        <p><strong>Tasks:</strong> {{ round.details.tasks }}</p>
        <p><strong>Uploaders:</strong> {{ round.details.uploaders }}</p> -->
      </div>
      <cdx-accordion class="info-accordion">
        <p v-for="(value, key) in round.config" :key="key" style="display: flex">
          <span v-if="key !== 'allowed_filetypes'">{{ key }}</span>
          <span v-if="key !== 'allowed_filetypes'" style="margin-left: auto">
            {{ value }}
          </span>
        </p>
        <template #title> Round File Settings </template>
      </cdx-accordion>
      <cdx-accordion class="info-accordion">
        <p>TODO: Voting</p>
        <template #title> Voting Details </template>
      </cdx-accordion>
    </div>
  </div>
  <div class="round__actions" style="display: flex; justify-content: end; gap: 16px; margin-top: 16px">
    <cdx-button v-if="round.status === 'paused'" @click="activateRound" action="progressive">
      <play style="font-size: 6px" />Activate
    </cdx-button>

    <cdx-button v-if="round.status === 'active'" @click="pauseRound">
      <pause style="font-size: 6px" /> Pause
    </cdx-button>

    <cdx-button :disabled="round.status === 'active'" @click="finalizeRound" action="progressive" weight="primary">
      <check style="font-size: 6px" />Finalize
    </cdx-button>

    <cdx-button @click="downloadResults">
      <download style="font-size: 6px" /> Download Results
    </cdx-button>

    <cdx-button @click="downloadEntries">
      <image-multiple style="font-size: 6px" /> Download Entries
    </cdx-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
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

const props = defineProps({
  round: Object
})

console.log(props.round)

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
        alertService.success('Round activated successfully.')
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
        alertService.success('Round paused successfully.')
      }

      // Refresh the page
      location.reload()
    })
    .catch(alertService.error);
}

const finalizeRound = () => {
  console.log('Finalize round')
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
</style>
