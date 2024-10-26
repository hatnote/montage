<template>
  <div style="display: flex">
    <div style="flex: 6; margin-right: 120px">
      <cdx-field>
        <cdx-text-input v-model="formData.name" />
        <template #label>Round Name</template>
      </cdx-field>
      <div style="display: flex">
        <cdx-field>
          <cdx-text-input input-type="date" v-model="formData.deadline_date" />
          <template #label>Voting Deadline</template>
        </cdx-field>
      </div>
      <cdx-field>
        <cdx-text-area v-model="formData.directions" rows="3" />
        <template #label>Directions</template>
      </cdx-field>
      <cdx-field>
        <cdx-radio
          v-for="source in showStatsOptions"
          :key="'show_stats-' + source.value"
          v-model="formData.show_stats"
          :input-value="source.value"
        >
          {{ source.label }}
        </cdx-radio>
        <template #label>Show own statistics (Beta)</template>
        <template #description>
          <p>
            Whether to show own voting statistics (e.g. number of accepted or declined images) of
            juror for the round.
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
        <UserList :users="formData.jurors" @update:selectedUsers="updateJurors" />
        <template #label>Jurors</template>
        <template #help-text>
          <p>Enter the username of the juror you want to add to this round.</p>
        </template>
      </cdx-field>
    </div>
    <div style="flex: 4">
      <h4>Round File Setting</h4>
      <cdx-field>
        <p v-for="(value, key) in fileSettingsOptions" :key="key" style="display: flex">
          <span>{{ value.label }}</span>
          <span style="margin-left: auto">{{ formData.config[key] }}</span>
        </p>
      </cdx-field>
      <cdx-field v-if="round.config.dq_by_resolution">
        <cdx-text-input v-model="formData.config.min_resolution" input-type="number" disabled />
        <template #label>Minimal resolution</template>
      </cdx-field>
    </div>
  </div>
  <div style="display: flex; margin-top: 16px">
    <cdx-button action="destructive" weight="primary" @click="deleteRound">
      <delete style="font-size: 6px" /> Delete Round
    </cdx-button>

    <cdx-button
      @click="saveRound"
      action="progressive"
      weight="primary"
      style="margin-left: auto; margin-right: 24px"
    >
      <check style="font-size: 6px" /> Save
    </cdx-button>

    <cdx-button @click="cancelRound"> <close style="font-size: 6px" /> Cancel </cdx-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UserList from '@/components/UserList.vue'

import { CdxButton, CdxField, CdxTextInput, CdxRadio, CdxTextArea } from '@wikimedia/codex'

// Icons
import Check from 'vue-material-design-icons/Check.vue'
import Close from 'vue-material-design-icons/Close.vue'
import Delete from 'vue-material-design-icons/Delete.vue'
import alertService from '@/services/alertService'
import adminService from '@/services/adminService'

const props = defineProps({
  round: Object,
  isRoundEditing: Boolean
})

console.log(props.round)
const formData = ref({
  name: props.round.name,
  directions: props.round.directions,
  quorum: props.round.quorum,
  deadline_date: props.round.deadline_date.split('T')[0],
  config: props.round.config,
  show_stats: props.round.show_stats,
  jurors: props.round.jurors.map((juror) => juror.username)
})

const showStatsOptions = ref([
  { label: 'Yes', value: true },
  { label: 'No', value: false }
])

const fileSettingsOptions = ref({
  allowed_filetypes: { label: 'Allowed filetypes' },
  dq_by_filetype: { label: 'Disqualify by filetype' },
  dq_by_resolution: { label: 'Disqualify by resolution' },
  dq_by_upload_date: { label: 'Disqualify by upload date' },
  dq_by_juror: { label: 'Disqualify jurors' },
  dq_coords: { label: 'Disqualify coordinators' },
  dq_maintainers: { label: 'Disqualify maintainers' },
  dq_organizers: { label: 'Disqualify organizers' },
  show_filename: { label: 'Show filename' },
  show_link: { label: 'Show link' },
  show_resolution: { label: 'Show resolution' }
})

function updateJurors(selectedUsers) {
  formData.value.jurors = selectedUsers
}

const emit = defineEmits(['update:isRoundEditing'])

// Methods
const cancelRound = () => {
  emit('update:isRoundEditing', false)
}

const saveRound = () => {
  const round = {
    id: props.round.id,
    name: formData.value.name,
    quorum: formData.value.quorum,
    directions: formData.value.directions,
    show_stats: formData.value.show_stats,
    deadline_date: formData.value.deadline_date + 'T00:00:00',
    new_jurors: formData.value.jurors
  }

  adminService
    .editRound(round.id, round)
    .then(() => {
      emit('update:isRoundEditing', false)
    })
    .catch(alertService.error)
}

const deleteRound = () => {
  adminService
    .cancelRound(props.round.id)
    .then(() => {
      emit('update:isRoundEditing', false)
    })
    .catch(alertService.error)
}
</script>
