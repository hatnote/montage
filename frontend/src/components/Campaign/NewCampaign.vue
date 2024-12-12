<template>
  <div class="new-campaign">
    <h2 class="new-campaig-heading">{{ $t('montage-new-campaig-heading') }}</h2>
    <cdx-card class="new-campaign-card">
      <template #supporting-text>
        <cdx-field :status="errors.name ? 'error' : 'default'" :messages="{ error: errors.name }">
          <template #description> {{ $t('montage-description-campaign-name') }}: </template>
          <cdx-text-input
            v-model="formField.name"
            :required="true"
            :placeholder="$t('montage-placeholder-campaign-name')"
          />
        </cdx-field>

        <cdx-field :status="errors.url ? 'error' : 'default'" :messages="{ error: errors.url }">
          <cdx-text-input
            v-model="formField.url"
            :required="true"
            :placeholder="$t('montage-placeholder-campaign-url')"
          />
          <template #description>
            {{ $t('montage-description-campaign-url') }}
          </template>
        </cdx-field>
        <cdx-field :is-fieldset="true">
          <template #label>{{ $t('montage-label-date-range') }}</template>
          <template #description>
            {{ $t('montage-description-date-range') }}
          </template>
          <div class="open-date-fields">
            <cdx-field
              :status="errors.openDate ? 'error' : 'default'"
              :messages="{ error: errors.openDate }"
            >
              <template #label>{{ $t('montage-label-open-date') }}:</template>
              <cdx-text-input input-type="date" v-model="formField.openDate" />
            </cdx-field>

            <cdx-field
              :status="errors.openTime ? 'error' : 'default'"
              :messages="{ error: errors.openTime }"
            >
              <template #label>{{ $t('montage-label-open-time') }}:</template>
                <cdx-text-input input-type="time" v-model="formField.openTime" />
            </cdx-field>
          </div>
          <div class="close-date-fields">
            <cdx-field
              :status="errors.closeDate ? 'error' : 'default'"
              :messages="{ error: errors.closeDate }"
            >
              <template #label>{{ $t('montage-label-close-date') }}:</template>
              <cdx-text-input input-type="date" v-model="formField.closeDate" />
            </cdx-field>

            <cdx-field
              :status="errors.closeTime ? 'error' : 'default'"
              :messages="{ error: errors.closeTime }"
            >
              <template #label>{{ $t('montage-label-close-time') }}:</template>
              <cdx-text-input input-type="time" v-model="formField.closeTime" />
            </cdx-field>
          </div>
        </cdx-field>
        <cdx-field
          :status="errors.coordinators ? 'error' : 'default'"
          :messages="{ error: errors.coordinators }"
        >
          <template #label>{{ $t('montage-label-campaign-coordinators') }}</template>
          <template #description>
            {{ $t('montage-description-campaign-coordinators') }}
          </template>
          <UserList
            :users="formField.coordinators"
            @update:selectedUsers="formField.coordinators = $event"
          />
        </cdx-field>

        <cdx-button
          :disabled="isLoading"
          @click="submitForm"
          action="progressive"
          weight="primary"
          class="create-button"
        >
          {{ $t('montage-btn-create-campaign') }}
        </cdx-button>
        <RouterLink to="/">
          <cdx-button action="destructive">{{ $t('montage-btn-cancel') }}</cdx-button>
        </RouterLink>
      </template>
    </cdx-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { z } from 'zod'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import { CdxTextInput, CdxButton, CdxCard, CdxField } from '@wikimedia/codex'
import UserList from '@/components/UserList.vue'

const router = useRouter()
const { t: $t } = useI18n()

// State
const isLoading = ref(false)
const formField = ref({
  name: '',
  url: '',
  openDate: '',
  openTime: '',
  closeDate: '',
  closeTime: '',
  coordinators: []
})

const errors = ref({
  name: '',
  url: '',
  openDate: '',
  openTime: '',
  closeDate: '',
  closeTime: '',
  coordinators: ''
})

const schema = z.object({
  name: z.string().min(1, $t('montage-required-campaign-name')),
  url: z
    .string()
    .url($t('montage-invalid-campaign-url'))
    .min(1, $t('montage-required-campaign-url')),
  openDate: z.string().refine((val) => !isNaN(Date.parse(val)), $t('montage-required-open-date')),
  openTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), $t('montage-required-open-time')),
  closeDate: z.string().refine((val) => !isNaN(Date.parse(val)), $t('montage-required-close-date')),
  closeTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), $t('montage-required-close-time')),
  coordinators: z.array(z.string()).min(1, $t('montage-required-campaign-coordinators'))
})

const submitForm = () => {
  Object.keys(errors.value).forEach((key) => {
    errors.value[key] = ''
  })

  const result = schema.safeParse(formField.value)
  if (!result.success) {
    result.error.errors.forEach((error) => {
      errors.value[error.path[0]] = error.message
    })
    return
  }

  const payload = {
    name: formField.value.name,
    url: formField.value.url,
    open_date: `${formField.value.openDate} ${formField.value.openTime}`,
    close_date: `${formField.value.closeDate} ${formField.value.closeTime}`,
    coordinators: formField.value.coordinators
  }

  isLoading.value = true
  adminService
    .addCampaign(payload)
    .then((res) => {
      console.log(res)
      if (res.status === 'success') {
        alertService.success($t('montage-campaign-added-success'))
        router.push({
          name: 'campaign',
          params: {
            id: [res.data.id, res.data.url_name].join('-')
          }
        })
      } else {
        alertService.error($t('montage-something-went-wrong'))
      }
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
}
</script>

<style scoped>
.new-campaign {
  padding: 40px;
}

.new-campaig-heading {
  margin-bottom: 16px;
}

.new-campaign-card {
  width: 75%;
}

.open-date-fields,
.close-date-fields {
  display: flex;
  gap: 24px;
}

.open-date-fields > .cdx-field,
.close-date-fields > .cdx-field {
  margin-top: 16px;
}

.create-button {
  margin-top: 16px;
  margin-right: 16px;
}
</style>
