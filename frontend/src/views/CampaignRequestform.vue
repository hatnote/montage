<template>
  <div class="request-form-page">
    <div v-if="isResubmission" class="resubmit-banner">
      <i class="ti ti-info-circle" aria-hidden="true"></i>
      {{ $t('campaign-request-resubmitting-for') }} <strong>{{ prefillRequestId }}</strong
      >.
      {{ $t('campaign-request-address-clarification') }}
    </div>

    <div class="page-header">
      <h1>{{ $t('campaign-request-form-title') }}</h1>
      <p class="subtitle">{{ $t('campaign-request-form-subtitle') }}</p>
    </div>

    <div v-if="submitted" class="success-card">
      <div class="success-icon">
        <i class="ti ti-circle-check" aria-hidden="true"></i>
      </div>

      <h2>{{ $t('campaign-request-submitted-title') }}</h2>

      <p>{{ $t('campaign-request-submitted-body') }}</p>

      <div class="success-actions">
        <div class="request-id-pill">
          <span class="label">
            {{ $t('campaign-request-tracking-id') }}
          </span>
          <strong>{{ submittedRequestId }}</strong>
        </div>

        <cdx-button weight="normal" @click="resetForm">
          {{ $t('campaign-request-submit-another') }}
        </cdx-button>
      </div>
    </div>

    <form v-else class="request-form" @submit.prevent="handleSubmit" novalidate>
      <fieldset class="form-section">
        <legend>{{ $t('campaign-request-section-campaign') }}</legend>

        <cdx-field
          :status="errors.campaign_name ? 'error' : 'default'"
          :messages="{ error: errors.campaign_name }"
          class="field-margin"
        >
          <template #label>
            {{ $t('campaign-request-field-name') }}
            <span class="required" aria-hidden="true">*</span>
          </template>
          <cdx-text-input
            v-model="form.campaign_name"
            :placeholder="$t('campaign-request-field-name-placeholder')"
            @blur="validateField('campaign_name')"
          />
        </cdx-field>

        <cdx-field
          :status="errors.commons_category ? 'error' : 'default'"
          :messages="{ error: errors.commons_category }"
          class="field-margin"
        >
          <template #label>
            {{ $t('campaign-request-field-commons') }}
            <span class="required" aria-hidden="true">*</span>
          </template>
          <template #help-text>
            {{ $t('campaign-request-field-commons-hint') }}
          </template>
          <cdx-text-input
            v-model="form.commons_category"
            :placeholder="$t('campaign-request-field-commons-placeholder')"
            @blur="validateField('commons_category')"
          />
        </cdx-field>

        <cdx-field
          :status="errors.purpose ? 'error' : 'default'"
          :messages="{ error: errors.purpose }"
          class="field-margin"
        >
          <template #label>
            {{ $t('campaign-request-field-purpose') }}
            <span class="required" aria-hidden="true">*</span>
          </template>
          <cdx-text-area
            v-model="form.purpose"
            :placeholder="$t('campaign-request-field-purpose-placeholder')"
            @blur="validateField('purpose')"
            rows="4"
          />
        </cdx-field>
      </fieldset>

      <fieldset class="form-section">
        <legend>{{ $t('campaign-request-section-coordinator') }}</legend>

        <cdx-field
          :status="errors.jury_coordinator_username ? 'error' : 'default'"
          :messages="{ error: errors.jury_coordinator_username }"
          class="field-margin"
        >
          <template #label>
            {{ $t('campaign-request-field-coordinator') }}
            <span class="required" aria-hidden="true">*</span>
          </template>
          <template #description>
            {{ $t('campaign-request-field-coordinator-hint') }}
          </template>
          <UserList
            v-if="prefillLoaded"
            :key="isResubmission ? 'prefilled' : 'new'"
            :users="coordinatorUsers"
            @update:selectedUsers="onCoordinatorSelect"
          />
        </cdx-field>
      </fieldset>

      <fieldset class="form-section">
        <legend>
          {{ $t('campaign-request-section-timeline') }}
        </legend>

        <div class="utc-notice">
          <i class="ti ti-clock-exclamation" aria-hidden="true"></i>
          <div>
            <strong>{{ $t('campaign-request-utc-notice-title') }}</strong>
            {{ $t('campaign-request-utc-notice-body') }}
          </div>
        </div>

        <div class="field-row field-margin">
          <cdx-field
            :status="errors.open_date ? 'error' : 'default'"
            :messages="{ error: errors.open_date }"
          >
            <template #label>
              {{ $t('campaign-request-field-open-date') }}
              <span class="required" aria-hidden="true">*</span>
            </template>
            <cdx-text-input
              input-type="datetime-local"
              v-model="form.open_date"
              @blur="
                validateField('open_date')
                updateTzPreview()
              "
            />
          </cdx-field>

          <cdx-field
            :status="errors.close_date ? 'error' : 'default'"
            :messages="{ error: errors.close_date }"
          >
            <template #label>
              {{ $t('campaign-request-field-close-date') }}
              <span class="required" aria-hidden="true">*</span>
            </template>
            <cdx-text-input
              input-type="datetime-local"
              v-model="form.close_date"
              @blur="
                validateField('close_date')
                updateTzPreview()
              "
            />
          </cdx-field>
        </div>

        <div v-if="tzPreview.open || tzPreview.close" class="tz-assistant">
          <p class="tz-assistant-title">
            <i class="ti ti-map-pin" aria-hidden="true"></i>
            {{ $t('campaign-request-tz-assistant-title') }}
          </p>
          <table class="tz-table" aria-label="Timezone preview">
            <thead>
              <tr>
                <th>{{ $t('campaign-request-tz-timezone') }}</th>
                <th>{{ $t('campaign-request-field-open-date') }}</th>
                <th>{{ $t('campaign-request-field-close-date') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tz in COMMON_TIMEZONES" :key="tz.id">
                <td>
                  <span class="tz-name">{{ tz.label }}</span>
                </td>
                <td>{{ tzPreview.open ? formatInTz(form.open_date, tz.id) : '—' }}</td>
                <td>{{ tzPreview.close ? formatInTz(form.close_date, tz.id) : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </fieldset>

      <fieldset class="form-section">
        <legend>{{ $t('campaign-request-section-volume') }}</legend>

        <cdx-field
          :status="errors.estimated_image_volume ? 'error' : 'default'"
          :messages="{ error: errors.estimated_image_volume }"
          class="field-margin"
        >
          <template #label>
            {{ $t('campaign-request-field-volume') }}
            <span class="required" aria-hidden="true">*</span>
          </template>
          <cdx-text-input
            input-type="number"
            v-model.number="form.estimated_image_volume"
            min="1"
            :placeholder="$t('campaign-request-field-volume-placeholder')"
            @blur="validateField('estimated_image_volume')"
          />

          <cdx-message
            v-if="form.estimated_image_volume > 0 && form.estimated_image_volume < 30"
            type="warning"
            inline
            class="margin-top-1"
          >
            {{ $t('campaign-request-volume-low-warning') }}
          </cdx-message>
        </cdx-field>
      </fieldset>

      <cdx-message v-if="submitError" type="error" class="field-margin">
        {{ submitError }}
      </cdx-message>

      <div class="form-actions">
        <cdx-button action="progressive" weight="primary" type="submit" :disabled="submitting">
          <i v-if="submitting" class="ti ti-loader-2 spin" aria-hidden="true"></i>
          <i v-else class="ti ti-send" aria-hidden="true"></i>
          {{ submitting ? $t('campaign-request-submitting') : $t('campaign-request-submit') }}
        </cdx-button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxButton, CdxTextInput, CdxTextArea, CdxField, CdxMessage } from '@wikimedia/codex'
import UserList from '@/components/UserList.vue'
import adminService from '@/services/adminService'
import { useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()

const props = defineProps({
  prefillData: { type: Object, default: null },
  prefillRequestId: { type: String, default: null }
})

const isResubmission = computed(() => !!route.params.request_id)

const COMMON_TIMEZONES = [
  { id: 'America/New_York', label: 'ET (New York)' },
  { id: 'Europe/London', label: 'BST/GMT (London)' },
  { id: 'Europe/Paris', label: 'CET (Paris)' },
  { id: 'Asia/Kolkata', label: 'IST (India)' },
  { id: 'Asia/Tokyo', label: 'JST (Tokyo)' },
  { id: 'Africa/Lagos', label: 'WAT (Lagos)' },
  { id: 'Africa/Johannesburg', label: 'CAT (Johannesburg)' },
  { id: 'Africa/Nairobi', label: 'EAT (Nairobi)' },
  { id: 'Australia/Sydney', label: 'AEDT (Sydney)' }
]

const defaultForm = () => ({
  campaign_name: '',
  commons_category: '',
  purpose: '',
  jury_coordinator_username: [],
  open_date: '',
  close_date: '',
  estimated_image_volume: null
})

function normalizeJurors(value) {
  if (Array.isArray(value)) return [...value]
  return value ? [value] : []
}

const form = reactive(
  props.prefillData ? { ...defaultForm(), ...props.prefillData } : defaultForm()
)
const errors = reactive({})
const submitError = ref('')
const submitting = ref(false)
const submitted = ref(false)
const submittedRequestId = ref('')
// const usernameStatus = ref('')
const tzPreview = reactive({ open: false, close: false })
const prefillLoaded = ref(!isResubmission.value)

const coordinatorUsers = ref(normalizeJurors(form.jury_coordinator_username))

function onCoordinatorSelect(selected) {
  // const latest = selected.length ? [selected[selected.length - 1]] : []
  coordinatorUsers.value = selected
  form.jury_coordinator_username = selected
  validateField('jury_coordinator_username')
}

onMounted(async () => {
  if (!isResubmission.value) return
  try {
    const res = await adminService.getCampaignRequest(route.params.request_id)
    const existing = res.data.data
    const jurors = normalizeJurors(existing.jury_coordinator_username)

    Object.assign(form, {
      campaign_name: existing.campaign_name,
      commons_category: existing.commons_category,
      purpose: existing.purpose,
      jury_coordinator_username: jurors,
      open_date: existing.open_date ? existing.open_date.slice(0, 16) : '',
      close_date: existing.close_date ? existing.close_date.slice(0, 16) : '',
      estimated_image_volume: existing.estimated_image_volume
    })
    coordinatorUsers.value = jurors
    updateTzPreview()
  } catch {
  } finally {
    prefillLoaded.value = true
  }
})

function validateField(field) {
  errors[field] = ''
  switch (field) {
    case 'campaign_name':
      if (!form.campaign_name.trim()) errors.campaign_name = t('validation-required')
      break
    case 'commons_category':
      if (!form.commons_category.trim()) errors.commons_category = t('validation-required')
      break
    case 'purpose':
      if (!form.purpose.trim()) errors.purpose = t('validation-required')
      break
    case 'jury_coordinator_username':
      if (!form.jury_coordinator_username || form.jury_coordinator_username.length === 0)
        errors.jury_coordinator_username = t('validation-required')
      break
    case 'open_date':
      if (!form.open_date) errors.open_date = t('validation-required')
      break
    case 'close_date':
      if (!form.close_date) {
        errors.close_date = t('validation-required')
      } else if (form.open_date && form.close_date <= form.open_date) {
        errors.close_date = t('validation-close-after-open')
      }
      break
    case 'estimated_image_volume':
      if (!form.estimated_image_volume || form.estimated_image_volume < 1)
        errors.estimated_image_volume = t('validation-volume-positive')
      break
  }
}

function validateAll() {
  const fields = [
    'campaign_name',
    'commons_category',
    'purpose',
    'jury_coordinator_username',
    'open_date',
    'close_date',
    'estimated_image_volume'
  ]
  fields.forEach(validateField)
  return !Object.values(errors).some(Boolean)
}

function formatInTz(isoLocal, tzId) {
  if (!isoLocal) return '—'
  try {
    const dt = new Date(isoLocal + 'Z')
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: tzId,
      dateStyle: 'medium',
      timeStyle: 'short'
    }).format(dt)
  } catch {
    return '—'
  }
}

function updateTzPreview() {
  tzPreview.open = !!form.open_date
  tzPreview.close = !!form.close_date
}

async function handleSubmit() {
  submitError.value = ''
  if (!validateAll()) return

  submitting.value = true
  try {
    const payload = {
      ...form,
      open_date: form.open_date ? form.open_date + ':00Z' : null,
      close_date: form.close_date ? form.close_date + ':00Z' : null,
      is_resubmission: isResubmission.value
    }

    let res
    if (isResubmission.value) {
      res = await adminService.resubmitCampaignRequest(props.prefillRequestId, payload)
    } else {
      res = await adminService.submitCampaignRequest(payload)
    }

    submittedRequestId.value = res.data.request_id || res.data.data?.requestId
    submitted.value = true
  } catch (err) {
    submitError.value = err?.response?.data?.description || t('campaign-request-submit-error')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, defaultForm())
  Object.keys(errors).forEach((k) => (errors[k] = ''))
  submitted.value = false
  submittedRequestId.value = ''
  coordinatorUsers.value = []
}
</script>

<style scoped>
.request-form-page {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1rem;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 2rem;
}
.page-header h1 {
  font-size: 32px;
  font-weight: bold;
  margin: 0 0 0.4rem;
}
.subtitle {
  font-size: 14px;
  color: #72777d;
  margin: 0;
}

.form-section {
  border: 1px solid #c8ccd1;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.form-section legend {
  font-size: 13px;
  font-weight: 500;
  color: #72777d;
  padding: 0 0.5rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.utc-notice {
  background: #a2a9b1;
  color: black;
  border-radius: 4px;
  border: 1px;
  padding: 0.75rem 1rem;
  font-size: 13px;
  margin-bottom: 1.25rem;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  line-height: 1.5;
}

.utc-label {
  display: inline-block;
  font-size: 10px;
  font-weight: 500;
  background: #fdf2d5;
  color: #ac6600;
  border-radius: 4px;
  padding: 1px 5px;
  margin-left: 6px;
  vertical-align: middle;
}

.utc-notice i {
  flex-shrink: 0;
  margin-top: 1px;
}

.required {
  color: #d73333;
  margin-left: 2px;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  align-items: end;
}

.tz-assistant {
  margin-top: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #c8ccd1;
  padding: 0.75rem 1rem;
}

.tz-assistant-title {
  font-size: 12px;
  font-weight: 500;
  color: #72777d;
  margin: 0 0 0.5rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tz-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.tz-table th {
  text-align: left;
  color: #72777d;
  font-weight: 500;
  padding: 4px 8px 4px 0;
  border-bottom: 1px solid #c8ccd1;
}

.tz-table td {
  padding: 5px 8px 5px 0;
  border-bottom: 1px solid #c8ccd1;
  color: #202122;
}

.tz-name {
  color: #72777d;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.success-card {
  border: 1px solid #a3e3d3;
  background: #259948;
  border-radius: 4px;
  padding: 2rem;
  text-align: center;
}

.success-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.success-icon {
  font-size: 40px;
  color: black;
  margin-bottom: 1rem;
}

.success-card h2 {
  font-size: 18px;
  font-weight: 500;
  color: black;
  margin: 0 0 0.5rem;
}

.success-card p {
  font-size: 14px;
  color: #202122;
  margin: 0 0 1.5rem;
}

.request-id-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #c8ccd1;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 14px;
}

.request-id-pill .label {
  color: #72777d;
}

.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
}

.field-margin {
  margin-bottom: 1.25rem;
}
.margin-top-1 {
  margin-top: 0.5rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
