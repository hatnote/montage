<template>
  <div class="new-campaign">
    <h2 class="new-campaig-heading">New Campaign</h2>
    <cdx-card class="new-campaign-card">
      <template #supporting-text>
        <cdx-field :status="errors.name ? 'error' : 'default'" :messages="{ error: errors.name }">
          <cdx-text-input v-model="formField.name" :required="true" placeholder="Name" />
        </cdx-field>

        <cdx-field :status="errors.url ? 'error' : 'default'" :messages="{ error: errors.url }">
          <cdx-text-input v-model="formField.url" :required="true" placeholder="Campaign URL*" />
          <template #description>
            Enter URL of campaign landing page, e.g., on Commons or local Wiki Loves.
          </template>
        </cdx-field>
        <cdx-field :is-fieldset="true">
          <template #label>Date Range</template>
          <template #description>
            Once the images are imported to the first round, changing date and time won't affect the
            images your jury can view. However, changing these values before the import to round 1
            will ensure that only photos uploaded before the end date and time are visible to your
            jury.
          </template>
          <div class="open-date-fields">
            <cdx-field
              :status="errors.openDate ? 'error' : 'default'"
              :messages="{ error: errors.openDate }"
            >
              <template #label>Open Date:</template>
              <cdx-text-input input-type="date" v-model="formField.openDate" />
            </cdx-field>

            <cdx-field
              :status="errors.openTime ? 'error' : 'default'"
              :messages="{ error: errors.openTime }"
            >
              <template #label>Open Time:</template>
              <cdx-text-input input-type="time" v-model="formField.openTime" />
            </cdx-field>
          </div>
          <div class="close-date-fields">
            <cdx-field
              :status="errors.closeDate ? 'error' : 'default'"
              :messages="{ error: errors.closeDate }"
            >
              <template #label>Close Date:</template>
              <cdx-text-input input-type="date" v-model="formField.closeDate" />
            </cdx-field>

            <cdx-field
              :status="errors.closeTime ? 'error' : 'default'"
              :messages="{ error: errors.closeTime }"
            >
              <template #label>Close Time:</template>
              <cdx-text-input input-type="time" v-model="formField.closeTime" />
            </cdx-field>
          </div>
        </cdx-field>
        <cdx-field
          :status="errors.coordinators ? 'error' : 'default'"
          :messages="{ error: errors.coordinators }"
        >
          <template #label>Campaign Coordinators</template>
          <template #description>
            Coordinators are people who have access to edit the campaign, rounds, and round
            statistics.
          </template>
          <UserList
            :users="formField.coordinators"
            @update:selectedUsers="formField.coordinators = $event"
          />
        </cdx-field>

        <cdx-button @click="submitForm" action="progressive" weight="primary" class="create-button">
          Create Campaign
        </cdx-button>
        <RouterLink to="/">
          <cdx-button action="destructive">Cancel</cdx-button>
        </RouterLink>
      </template>
    </cdx-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { z } from 'zod'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import { CdxTextInput, CdxButton, CdxCard, CdxField } from '@wikimedia/codex'
import UserList from '@/components/UserList.vue'

const router = useRouter()

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
  name: z.string().min(1, 'Name is required'),
  url: z.string().url('Invalid URL').min(1, 'URL is required'),
  openDate: z.string().refine((val) => !isNaN(Date.parse(val)), 'Open date is required'),
  openTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), 'Open time is required'),
  closeDate: z.string().refine((val) => !isNaN(Date.parse(val)), 'Close date is required'),
  closeTime: z
    .string()
    .refine((val) => /^([01]\d|2[0-3]):?([0-5]\d)$/.test(val), 'Close time is required'),
  coordinators: z.array(z.string()).min(1, 'At least one coordinator is required')
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

  adminService
    .addCampaign(payload)
    .then((res) => {
      console.log(res)
      if (res.status === 'success') {
        alertService.success('Campaign added successfully')
        router.push({
          name: 'campaign',
          params: {
            id: [res.data.id, res.data.url_name].join('-')
          }
        })
      } else {
        alertService.error('Something went wrong. Please try again.')
      }
    })
    .catch(alertService.error)
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
