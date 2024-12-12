<template>
  <div style="display: flex">
    <div style="flex: 6; margin-right: 120px">
      <cdx-field>
        <cdx-text-input v-model="formData.name" />
        <template #label>{{ $t('montage-round-name') }}</template>
      </cdx-field>
      <div style="display: flex">
        <cdx-field>
          <cdx-text-input input-type="date" v-model="formData.deadline_date" />
          <template #label>{{ $t('montage-round-deadline') }}</template>
        </cdx-field>
      </div>
      <cdx-field>
        <cdx-text-area v-model="formData.directions" rows="3" />
        <template #label>{{ $t('montage-directions') }}</template>
      </cdx-field>
      <cdx-field>
        <cdx-radio v-for="source in showStatsOptions" :key="'show_stats-' + source.value" v-model="formData.show_stats"
          :input-value="source.value">
          {{ source.label }}
        </cdx-radio>
        <template #label>{{ $t('montage-label-round-stats') }}</template>
        <template #description>
          <p>
            {{ $t('montage-description-round-stats') }}
          </p>
        </template>
      </cdx-field>
      <cdx-field>
        <cdx-text-input v-model="formData.quorum" input-type="number" />
        <template #label>{{ $t('montage-label-round-quorum') }}</template>
        <template #description>
          <p>{{ $t('montage-description-round-quorum') }}</p>
        </template>
      </cdx-field>
      <cdx-field>
        <UserList :users="formData.jurors" @update:selectedUsers="updateJurors" />
        <template #label>{{ $t('montage-label-round-jurors') }}</template>
        <template #help-text>
          <p>{{ $t('montage-description-round-jurors') }}</p>
        </template>
      </cdx-field>
    </div>
    <div style="flex: 4">
      <h4>{{ $t('montage-round-file-setting')}}</h4>
      <cdx-field>
        <p v-for="key in fileSettingsOptions" :key="key" style="display: flex">
          <span>{{ $t('montage-round-' + key.replaceAll('_', '-')) }}</span>
          <span style="margin-left: auto">{{ formData.config[key] }}</span>
        </p>
      </cdx-field>
      <cdx-field v-if="round.config.dq_by_resolution">
        <cdx-text-input v-model="formData.config.min_resolution" input-type="number" disabled />
        <template #label>{{ $t('montage-round-min-resolution') }}</template>
      </cdx-field>
    </div>
  </div>
  <div style="display: flex; margin-top: 16px">
    <cdx-button action="destructive" weight="primary" @click="deleteRound">
      <delete style="font-size: 6px" /> {{ $t('montage-round-delete') }}
    </cdx-button>

    <cdx-button @click="saveRound" action="progressive" weight="primary" style="margin-left: auto; margin-right: 24px">
      <check style="font-size: 6px" /> {{ $t('montage-btn-save') }}
    </cdx-button>

    <cdx-button @click="cancelRound">
      <close style="font-size: 6px" /> {{ $t('montage-btn-cancel') }}
    </cdx-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import UserList from '@/components/UserList.vue'

import { CdxButton, CdxField, CdxTextInput, CdxRadio, CdxTextArea } from '@wikimedia/codex'

// Icons
import Check from 'vue-material-design-icons/Check.vue'
import Close from 'vue-material-design-icons/Close.vue'
import Delete from 'vue-material-design-icons/Delete.vue'
import alertService from '@/services/alertService'
import adminService from '@/services/adminService'
import dialogService from '@/services/dialogService'
import { useRouter } from 'vue-router'

const router = useRouter()
const { t: $t } = useI18n()
const props = defineProps({
  round: Object,
  isRoundEditing: Boolean
})

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
  { label: $t('montage-option-yes'), value: true },
  { label: $t('montage-option-no'), value: false }
])

const fileSettingsOptions = ref([
  "allowed_filetypes",
  "dq_by_filetype",
  "dq_by_resolution",
  "dq_by_upload_date",
  "dq_by_uploader",
  "dq_coords",
  "dq_maintainers",
  "dq_organizers",
  "show_filename",
  "show_link",
  "show_resolution"
])

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

  dialogService().show({
    title: $t('montage-round-delete'),
    content: $t('montage-round-delete-confirm'),
    primaryAction: {
      label: $t('montage-round-delete'),
      actionType: 'destructive'
    },
    defaultAction: {
      label: $t('montage-btn-cancel'),
    },
    onPrimary: () => {
      adminService
        .cancelRound(props.round.id)
        .then(() => {
          emit('update:isRoundEditing', false)
          router.reload()
        })
        .catch(alertService.error)
    },
  })


}
</script>
