<template>
  <div class="campaign-container">
    <div v-if="!campaignEditMode">
      <div class="campaign-header">
        <p class="campaign-title">{{ campaign.name }}</p>
        <div class="campaign-button-group">
          <cdx-button action="destructive" weight="primary" @click="closeCampaign">
            <clipboard-check class="icon-small" /> {{ $t('montage-close-campaign') }}
          </cdx-button>
          <cdx-button action="destructive" @click="archiveCampaign" v-if="!campaign.is_archived">
            <package-down class="icon-small" /> {{ $t('montage-archive') }}
          </cdx-button>
          <cdx-button action="progressive" @click="unarchiveCampaign" v-else>
            <inbox-arrow-up class="icon-small" /> {{ $t('montage-unarchive') }}
          </cdx-button>
          <cdx-button action="progressive" @click="hangleEditCampaignBtnClick" :disabled="campaign.is_archived">
            <cog-icon class="icon-small" /> {{ $t('montage-edit-campaign') }}
          </cdx-button>
        </div>
      </div>
      <div class="campaign-dates">
        <span>{{ formatDate(campaign.open_date) }} - {{ formatDate(campaign.close_date) }}</span>
      </div>
      <div class="campaign-coordinators">
        <UserAvatarWithName :coordinators="campaign.coordinators" />
      </div>
      <div class="campaign-rounds">
        <div class="campaign-rounds-list" v-if="!showAddRoundForm">
          <round-view v-for="round in campaign.rounds" :key="round.id" :round="round" />
        </div>
        <cdx-button v-if="!showAddRoundForm" action="progressive" @click="addRound" :disabled="campaign.isArchived" icon
          class="add-round-button">
          <plus class="icon-small" /> {{ $t('montage-round-add') }}
        </cdx-button>
        <round-new :rounds="campaign.rounds" v-if="showAddRoundForm" v-model:showAddRoundForm="showAddRoundForm"
          @reloadCampaignState="reloadState" />
      </div>
    </div>
    <div v-else>
      <div class="campaign-header">
        <cdx-field class="campaign-name-field" :status="errors.name ? 'error' : 'default'"
          :messages="{ error: errors.name }">
          <cdx-text-input class="campaign-name-input" v-model="campaignFormField.name" />
        </cdx-field>
        <div class="campaign-button-group">
          <cdx-button action="progressive" @click="saveEditCampaign" class="save-button">
            <check class="icon-small" /> {{ $t('montage-btn-save') }}
          </cdx-button>
          <cdx-button action="destructive" @click="cancelEdit" class="cancel-button" v-if="!campaign.isArchived">
            <close class="icon-small" /> {{ $t('montage-btn-cancel') }}
          </cdx-button>
        </div>
      </div>
      <div class="date-time-inputs">
        <cdx-field class="open-date-field" :status="errors.openDate ? 'error' : 'default'"
          :messages="{ error: errors.openDate }">
          <template #label>{{ $t('montage-round-open-date') }}:</template>
          <cdx-text-input input-type="date" v-model="campaignFormField.openDate" />
        </cdx-field>
        <cdx-field :status="errors.openTime ? 'error' : 'default'" :messages="{ error: errors.openTime }">
          <template #label>{{ $t('montage-round-open-time') }}:</template>
          <cdx-text-input input-type="time" v-model="campaignFormField.openTime" />
        </cdx-field>
        <cdx-field :status="errors.closeDate ? 'error' : 'default'" :messages="{ error: errors.closeDate }">
          <template #label>{{ $t('montage-round-close-date') }}:</template>
          <cdx-text-input input-type="date" v-model="campaignFormField.closeDate" />
        </cdx-field>
        <cdx-field :status="errors.closeTime ? 'error' : 'default'" :messages="{ error: errors.closeTime }">
          <cdx-text-input input-type="time" v-model="campaignFormField.closeTime" />
          <template #label>{{ $t('montage-round-close-time') }}</template>
        </cdx-field>
      </div>
      <cdx-field :status="errors.coordinators ? 'error' : 'default'" :messages="{ error: errors.coordinators }">
        <template #label>{{ $t('montage-label-campaign-coordinators') }}</template>
        <UserList :users="campaignFormField.coordinators"
          @update:selectedUsers="campaignFormField.coordinators = $event" />
      </cdx-field>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@/utils'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'

import { z } from 'zod'

// Components
import RoundView from '@/components/Round/RoundView.vue'
import RoundNew from '@/components/Round/RoundNew.vue'
import UserList from '@/components/UserList.vue'
import { CdxButton, CdxTextInput, CdxField } from '@wikimedia/codex'

// Icons
import CogIcon from 'vue-material-design-icons/Cog.vue'
import PackageDown from 'vue-material-design-icons/PackageDown.vue'
import ClipboardCheck from 'vue-material-design-icons/ClipboardCheck.vue'
import UserAvatarWithName from '@/components/UserAvatarWithName.vue'
import InboxArrowUp from 'vue-material-design-icons/InboxArrowUp.vue'
import Plus from 'vue-material-design-icons/Plus.vue'
import Check from 'vue-material-design-icons/Check.vue'
import Close from 'vue-material-design-icons/Close.vue'

const route = useRoute()
const { t: $t } = useI18n()
const campaignId = route.params.id.split('-')[0]

const campaignEditMode = ref(false)
const showAddRoundForm = ref(false)
const canCloseCampaign = ref(false)

const campaign = ref({})
const campaignFormField = ref({
  name: null,
  openDate: null,
  openTime: null,
  closeDate: null,
  closeTime: null,
  coordinators: []
})

const errors = ref({
  name: '',
  openDate: '',
  openTime: '',
  closeDate: '',
  closeTime: '',
  coordinators: ''
})

const schema = z.object({
  name: z.string().min(1, $t('montage-required-campaign-name')),
  openDate: z.string().refine((val) => !isNaN(Date.parse(val)), $t('montage-required-open-date')),
  openTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), $t('montage-required-open-time')),
  closeDate: z.string().refine((val) => !isNaN(Date.parse(val)),  $t('montage-required-close-date')),
  closeTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), $t('montage-required-close-time')),
  coordinators: z.array(z.string()).min(1, $t('montage-required-campaign-coordinators'))
})

const hangleEditCampaignBtnClick = () => {
  campaignEditMode.value = true

  campaignFormField.value = {
    name: campaign.value.name,
    openDate: campaign.value.open_date?.split('T')[0],
    openTime: campaign.value.open_date?.split('T')[1].substring(0, 5),
    closeDate: campaign.value.close_date?.split('T')[0],
    closeTime: campaign.value.close_date?.split('T')[1].substring(0, 5),
    coordinators: campaign.value.coordinators.map((u) => u.username)
  }
}

const validateCampaignEditForm = () => {
  Object.keys(errors.value).forEach((key) => {
    errors.value[key] = ''
  })

  const result = schema.safeParse(campaignFormField.value)
  if (!result.success) {
    result.error.errors.forEach((error) => {
      errors.value[error.path[0]] = error.message
    })
    return false
  }
  return true
}

const saveEditCampaign = () => {
  if (!validateCampaignEditForm()) {
    return
  }

  const payload = {
    name: campaignFormField.value.name,
    open_date: `${campaignFormField.value.openDate}T${campaignFormField.value.openTime}`,
    close_date: `${campaignFormField.value.closeDate}T${campaignFormField.value.closeTime}`,
    coordinators: campaignFormField.value.coordinators
  }

  adminService
    .editCampaign(campaignId, payload)
    .then((resp) => {
      if (resp.status === 'success') {
        reloadState()
      }
    })
    .catch(alertService.error)

  campaignEditMode.value = false
}

const cancelEdit = () => {
  campaignEditMode.value = false
}

const archiveCampaign = () => {
  const data = { is_archived: true }

  adminService
    .editCampaign(campaignId, data)
    .then((resp) => {
      if (resp.status === 'success') {
        reloadState()
      }
    })
    .catch(alertService.error)
}

const unarchiveCampaign = () => {
  const data = { is_archived: false }

  adminService
    .editCampaign(campaignId, data)
    .then((resp) => {
      if (resp.status === 'success') {
        reloadState()
      }
    })
    .catch(alertService.error)
}

const closeCampaign = () => {
  adminService
    .finalizeCampaign(campaignId)
    .then((resp) => {
      if (resp.status === 'success') {
        reloadState()
      }
    })
    .catch(alertService.error)
}

const addRound = () => {
  showAddRoundForm.value = true
}

const reloadState = () => {
  adminService.getCampaign(campaignId).then((response) => {
    campaign.value = response.data
    canCloseCampaign.value = response.data.status === 'active'
  })
}

onMounted(() => {
  reloadState()
})
</script>

<style scoped>
.campaign-container {
  padding: 40px;
}

.campaign-header {
  display: flex;
  align-items: center;
}

.campaign-title {
  font-size: 36px;
}

.campaign-button-group {
  display: flex;
  gap: 10px;
  margin-left: auto;
  height: 32px;
}

.campaign-coordinators {
  margin-top: 16px;
  margin-bottom: 24px;
}

.campaign-rounds {
  margin-top: 48px;
}

.campaign-name-field {
  width: 100%;
  margin-right: 56px;
}

.campaign-name-input {
  font-size: 36px;
  width: 100%;
}

.campaign-coordinators-edit {
  margin-top: 24px;
  width: 50%;
  height: 53px;
}

.date-time-inputs {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.open-date-field {
  margin-top: 16px !important;
}

.icon-small {
  font-size: 6px;
}

.add-round-button {
  margin-top: 24px;
}
</style>
