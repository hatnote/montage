<template>
    <div class="request-form-page">
      <div v-if="isResubmission" class="resubmit-banner">
        <i class="ti ti-info-circle" aria-hidden="true"></i>
        {{ $t('campaign-request-resubmitting-for') }} <strong>{{ prefillRequestId }}</strong>.
        {{ $t('campaign-request-address-clarification') }}
      </div>
  
      <div class="page-header">
        <h1>{{ $t('campaign-request-form-title') }}</h1>
        <p class="subtitle">{{ $t('campaign-request-form-subtitle') }}</p>
      </div>
  
      
      <div v-if="submitted" class="success-card">
        <div class="success-icon"><i class="ti ti-circle-check" aria-hidden="true"></i></div>
        <h2>{{ $t('campaign-request-submitted-title') }}</h2>
        <p>{{ $t('campaign-request-submitted-body') }}</p>
        <div class="request-id-pill">
          <span class="label">{{ $t('campaign-request-tracking-id') }}</span>
          <strong>{{ submittedRequestId }}</strong>
        </div>
        <button class="btn-secondary" @click="resetForm">
          {{ $t('campaign-request-submit-another') }}
        </button>
      </div>
  
      <form v-else class="request-form" @submit.prevent="handleSubmit" novalidate>
  
        <fieldset class="form-section">
          <legend>{{ $t('campaign-request-section-campaign') }}</legend>
  
          <div class="field">
            <label for="campaign_name">
              {{ $t('campaign-request-field-name') }}
              <span class="required" aria-hidden="true">*</span>
            </label>
            <input
              id="campaign_name"
              v-model="form.campaign_name"
              type="text"
              :placeholder="$t('campaign-request-field-name-placeholder')"
              :class="{ error: errors.campaign_name }"
              @blur="validateField('campaign_name')"
            />
            <p v-if="errors.campaign_name" class="field-error" role="alert">
              {{ errors.campaign_name }}
            </p>
          </div>
  
          <div class="field">
            <label for="commons_category">
              {{ $t('campaign-request-field-commons') }}
              <span class="required" aria-hidden="true">*</span>
            </label>
            <input
              id="commons_category"
              v-model="form.commons_category"
              type="text"
              :placeholder="$t('campaign-request-field-commons-placeholder')"
              :class="{ error: errors.commons_category }"
              @blur="validateField('commons_category')"
            />
            <p class="field-hint">{{ $t('campaign-request-field-commons-hint') }}</p>
            <p v-if="errors.commons_category" class="field-error" role="alert">
              {{ errors.commons_category }}
            </p>
          </div>
  
          <div class="field">
            <label for="purpose">
              {{ $t('campaign-request-field-purpose') }}
              <span class="required" aria-hidden="true">*</span>
            </label>
            <textarea
              id="purpose"
              v-model="form.purpose"
              rows="4"
              :placeholder="$t('campaign-request-field-purpose-placeholder')"
              :class="{ error: errors.purpose }"
              @blur="validateField('purpose')"
            ></textarea>
            <p v-if="errors.purpose" class="field-error" role="alert">
              {{ errors.purpose }}
            </p>
          </div>
        </fieldset>
  
        <fieldset class="form-section">
          <legend>{{ $t('campaign-request-section-coordinator') }}</legend>
  
          <div class="field">
            <label for="jury_coordinator_username">
              {{ $t('campaign-request-field-coordinator') }}
              <span class="required" aria-hidden="true">*</span>
            </label>
            <div class="input-with-badge">
              <input
                id="jury_coordinator_username"
                v-model="form.jury_coordinator_username"
                type="text"
                :placeholder="$t('campaign-request-field-coordinator-placeholder')"
                :class="{ error: errors.jury_coordinator_username }"
                @blur="checkWikimediaUser"
              />
              <span
                v-if="usernameStatus === 'checking'"
                class="badge badge-neutral"
              >
                <i class="ti ti-loader-2 spin" aria-hidden="true"></i>
                {{ $t('campaign-request-checking') }}
              </span>
              <span
                v-else-if="usernameStatus === 'valid'"
                class="badge badge-success"
              >
                <i class="ti ti-check" aria-hidden="true"></i>
                {{ $t('campaign-request-user-found') }}
              </span>
              <span
                v-else-if="usernameStatus === 'invalid'"
                class="badge badge-danger"
              >
                <i class="ti ti-x" aria-hidden="true"></i>
                {{ $t('campaign-request-user-not-found') }}
              </span>
            </div>
            <p class="field-hint">{{ $t('campaign-request-field-coordinator-hint') }}</p>
            <p v-if="errors.jury_coordinator_username" class="field-error" role="alert">
              {{ errors.jury_coordinator_username }}
            </p>
          </div>
        </fieldset>
  
        <fieldset class="form-section">
          <legend>
            {{ $t('campaign-request-section-timeline') }}
            <span class="utc-badge">
              <i class="ti ti-world" aria-hidden="true"></i>
              UTC
            </span>
          </legend>
  
          <div class="utc-notice">
            <i class="ti ti-clock-exclamation" aria-hidden="true"></i>
            <strong>{{ $t('campaign-request-utc-notice-title') }}</strong>
            {{ $t('campaign-request-utc-notice-body') }}
          </div>
  
          <div class="field-row">
            <div class="field">
              <label for="open_date">
                {{ $t('campaign-request-field-open-date') }}
                <span class="required" aria-hidden="true">*</span>
                <span class="utc-label">UTC</span>
              </label>
              <input
                id="open_date"
                v-model="form.open_date"
                type="datetime-local"
                :class="{ error: errors.open_date }"
                @change="validateField('open_date'); updateTzPreview()"
              />
              <p v-if="errors.open_date" class="field-error" role="alert">
                {{ errors.open_date }}
              </p>
            </div>
  
            <div class="field">
              <label for="close_date">
                {{ $t('campaign-request-field-close-date') }}
                <span class="required" aria-hidden="true">*</span>
                <span class="utc-label">UTC</span>
              </label>
              <input
                id="close_date"
                v-model="form.close_date"
                type="datetime-local"
                :class="{ error: errors.close_date }"
                @change="validateField('close_date'); updateTzPreview()"
              />
              <p v-if="errors.close_date" class="field-error" role="alert">
                {{ errors.close_date }}
              </p>
            </div>
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
                  <td><span class="tz-name">{{ tz.label }}</span></td>
                  <td>{{ tzPreview.open ? formatInTz(form.open_date, tz.id) : '—' }}</td>
                  <td>{{ tzPreview.close ? formatInTz(form.close_date, tz.id) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </fieldset>
  
        <fieldset class="form-section">
          <legend>{{ $t('campaign-request-section-volume') }}</legend>
  
          <div class="field">
            <label for="estimated_image_volume">
              {{ $t('campaign-request-field-volume') }}
              <span class="required" aria-hidden="true">*</span>
            </label>
            <input
              id="estimated_image_volume"
              v-model.number="form.estimated_image_volume"
              type="number"
              min="1"
              :placeholder="$t('campaign-request-field-volume-placeholder')"
              :class="{ error: errors.estimated_image_volume }"
              @blur="validateField('estimated_image_volume')"
            />
            <p v-if="errors.estimated_image_volume" class="field-error" role="alert">
              {{ errors.estimated_image_volume }}
            </p>
            <div
              v-if="form.estimated_image_volume > 0 && form.estimated_image_volume < 30"
              class="volume-warning"
              role="note"
            >
              <i class="ti ti-alert-triangle" aria-hidden="true"></i>
              {{ $t('campaign-request-volume-low-warning') }}
            </div>
          </div>
        </fieldset>
  
        <div v-if="submitError" class="global-error" role="alert">
          <i class="ti ti-circle-x" aria-hidden="true"></i>
          {{ submitError }}
        </div>
  
        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="submitting">
            <i v-if="submitting" class="ti ti-loader-2 spin" aria-hidden="true"></i>
            <i v-else class="ti ti-send" aria-hidden="true"></i>
            {{ submitting ? $t('campaign-request-submitting') : $t('campaign-request-submit') }}
          </button>
        </div>
      </form>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import adminService from '@/services/adminService'
  import { onMounted } from 'vue'
  import { useRoute } from 'vue-router'
  
  const { t } = useI18n()
  const route = useRoute()
  
  const props = defineProps({
    
    prefillData: { type: Object, default: null },
    prefillRequestId: { type: String, default: null },
  })
  
  const isResubmission = computed(() => !!route.params.request_id)
  
  const COMMON_TIMEZONES = [
    { id: 'America/New_York', label: 'ET (New York)' },
    { id: 'Europe/London',    label: 'BST/GMT (London)' },
    { id: 'Europe/Paris',     label: 'CET (Paris)' },
    { id: 'Asia/Kolkata',     label: 'IST (India)' },
    { id: 'Asia/Tokyo',       label: 'JST (Tokyo)' },
    { id: 'Africa/Lagos',     label: 'WAT (Lagos)' },
    { id: 'Africa/Johannesburg', label: 'CAT (Johannesburg)' }, 
    { id: 'Africa/Nairobi',   label: 'EAT (Nairobi)' },
    { id: 'Australia/Sydney', label: 'AEDT (Sydney)' },
  ]
    
  const defaultForm = () => ({
    campaign_name: '',
    commons_category: '',
    purpose: '',
    jury_coordinator_username: '',
    open_date: '',
    close_date: '',
    estimated_image_volume: null,
  })
  
  const form = reactive(props.prefillData ? { ...defaultForm(), ...props.prefillData } : defaultForm())
  const errors = reactive({})
  const submitError = ref('')
  const submitting = ref(false)
  const submitted = ref(false)
  const submittedRequestId = ref('')
  const usernameStatus = ref('')
  const tzPreview = reactive({ open: false, close: false })

  onMounted(async () => {
  if (!isResubmission.value) return
  try {
    const res = await adminService.getCampaignRequest(route.params.request_id)
    const existing = res.data.data
    
    Object.assign(form, {
      campaign_name: existing.campaign_name,
      commons_category: existing.commons_category,
      purpose: existing.purpose,
      jury_coordinator_username: existing.jury_coordinator_username,
      open_date: existing.open_date ? existing.open_date.slice(0, 16) : '',
      close_date: existing.close_date ? existing.close_date.slice(0, 16) : '',
      estimated_image_volume: existing.estimated_image_volume,
    })
    updateTzPreview()
  } catch {

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
        if (!form.jury_coordinator_username.trim())
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
      'campaign_name', 'commons_category', 'purpose',
      'jury_coordinator_username', 'open_date', 'close_date', 'estimated_image_volume',
    ]
    fields.forEach(validateField)
    return !Object.values(errors).some(Boolean)
  }
  
  // wikimedia username checker
  
  let usernameDebounceTimer = null
  async function checkWikimediaUser() {
    validateField('jury_coordinator_username')
    const username = form.jury_coordinator_username.trim()
    if (!username) return
  
    clearTimeout(usernameDebounceTimer)
    usernameDebounceTimer = setTimeout(async () => {
      usernameStatus.value = 'checking'
      try {
        const res = await adminService.validateWikimediaUser(username)
        usernameStatus.value = res.data.data.exists ? 'valid' : 'invalid'
        if (!res.data.data.exists) {
          errors.jury_coordinator_username = t('campaign-request-user-not-found-error')
        }
      } catch {
        usernameStatus.value = ''
      }
    }, 500)
  }
    
  function formatInTz(isoLocal, tzId) {
    if (!isoLocal) return '—'
    try {
      const dt = new Date(isoLocal + 'Z')  // treat input as UTC
      return new Intl.DateTimeFormat('en-GB', {
        timeZone: tzId,
        dateStyle: 'medium',
        timeStyle: 'short',
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
        is_resubmission: isResubmission.value,
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
      submitError.value =
        err?.response?.data?.description || t('campaign-request-submit-error')
    } finally {
      submitting.value = false
    }
  }
  
  function resetForm() {
    Object.assign(form, defaultForm())
    Object.keys(errors).forEach(k => (errors[k] = ''))
    submitted.value = false
    submittedRequestId.value = ''
    usernameStatus.value = ''
  }
  </script>
  
  <style scoped>
  .request-form-page {
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }
  
  .page-header { margin-bottom: 2rem; }
  .page-header h1 { font-size: 22px; font-weight: 500; margin: 0 0 0.4rem; }
  .subtitle { font-size: 14px; color: var(--color-text-secondary); margin: 0; }
  
  .resubmit-banner {
    background: var(--color-background-info);
    color: var(--color-text-info);
    border: 0.5px solid var(--color-border-info);
    border-radius: var(--border-radius-md);
    padding: 0.75rem 1rem;
    margin-bottom: 1.5rem;
    font-size: 14px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  
  .form-section {
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: var(--border-radius-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
  }
  
  .form-section legend {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text-secondary);
    padding: 0 0.5rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .utc-badge {
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border: 0.5px solid var(--color-border-warning);
    border-radius: var(--border-radius-md);
    font-size: 11px;
    padding: 2px 8px;
    font-weight: 500;
  }
  
  .utc-notice {
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border-radius: var(--border-radius-md);
    border: 0.5px solid var(--color-border-warning);
    padding: 0.75rem 1rem;
    font-size: 13px;
    margin-bottom: 1.25rem;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    line-height: 1.5;
  }
  
  .utc-notice i { flex-shrink: 0; margin-top: 1px; }
  
  .field { margin-bottom: 1.25rem; }
  .field:last-child { margin-bottom: 0; }
  
  .field label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 6px;
    color: var(--color-text-primary);
  }
  
  .utc-label {
    display: inline-block;
    font-size: 10px;
    font-weight: 500;
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border-radius: 4px;
    padding: 1px 5px;
    margin-left: 6px;
    vertical-align: middle;
  }
  
  .required { color: var(--color-text-danger); margin-left: 2px; }
  
  input[type="text"],
  input[type="number"],
  input[type="datetime-local"],
  textarea {
    width: 100%;
    box-sizing: border-box;
  }
  
  input.error, textarea.error {
    border-color: var(--color-border-danger);
  }
  
  .field-hint {
    font-size: 12px;
    color: var(--color-text-secondary);
    margin: 4px 0 0;
  }
  
  .field-error {
    font-size: 12px;
    color: var(--color-text-danger);
    margin: 4px 0 0;
  }
  
  .input-with-badge {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .input-with-badge input { flex: 1; min-width: 0; }
  
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: var(--border-radius-md);
    white-space: nowrap;
    flex-shrink: 0;
  }
  
  .badge-neutral {
    background: var(--color-background-secondary);
    color: var(--color-text-secondary);
  }
  
  .badge-success {
    background: var(--color-background-success);
    color: var(--color-text-success);
  }
  
  .badge-danger {
    background: var(--color-background-danger);
    color: var(--color-text-danger);
  }
  
  .field-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }
  
  .tz-assistant {
    margin-top: 1rem;
    background: var(--color-background-secondary);
    border-radius: var(--border-radius-md);
    border: 0.5px solid var(--color-border-tertiary);
    padding: 0.75rem 1rem;
  }
  
  .tz-assistant-title {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text-secondary);
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
    color: var(--color-text-secondary);
    font-weight: 500;
    padding: 4px 8px 4px 0;
    border-bottom: 0.5px solid var(--color-border-tertiary);
  }
  
  .tz-table td {
    padding: 5px 8px 5px 0;
    border-bottom: 0.5px solid var(--color-border-tertiary);
    color: var(--color-text-primary);
  }
  
  .tz-name { color: var(--color-text-secondary); }
  
  .volume-warning {
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border: 0.5px solid var(--color-border-warning);
    border-radius: var(--border-radius-md);
    padding: 0.6rem 0.75rem;
    font-size: 13px;
    margin-top: 8px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  
  .global-error {
    background: var(--color-background-danger);
    color: var(--color-text-danger);
    border: 0.5px solid var(--color-border-danger);
    border-radius: var(--border-radius-md);
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 14px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  
  .form-actions {
    display: flex;
    justify-content: flex-end;
  }
  
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.55rem 1.25rem;
    background: var(--color-background-primary);
    border: 0.5px solid var(--color-border-secondary);
    border-radius: var(--border-radius-md);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    color: var(--color-text-primary);
  }
  
  .btn-primary:hover { background: var(--color-background-secondary); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.5rem 1.1rem;
    background: transparent;
    border: 0.5px solid var(--color-border-secondary);
    border-radius: var(--border-radius-md);
    font-size: 13px;
    cursor: pointer;
    color: var(--color-text-secondary);
  }
  
  .success-card {
    border: 0.5px solid var(--color-border-success);
    background: var(--color-background-success);
    border-radius: var(--border-radius-lg);
    padding: 2.5rem;
    text-align: center;
  }
  
  .success-icon {
    font-size: 40px;
    color: var(--color-text-success);
    margin-bottom: 1rem;
  }
  
  .success-card h2 {
    font-size: 18px;
    font-weight: 500;
    color: var(--color-text-success);
    margin: 0 0 0.5rem;
  }
  
  .success-card p {
    font-size: 14px;
    color: var(--color-text-success);
    margin: 0 0 1.5rem;
  }
  
  .request-id-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--color-background-primary);
    border: 0.5px solid var(--color-border-success);
    border-radius: var(--border-radius-md);
    padding: 0.5rem 1rem;
    margin-bottom: 1.5rem;
    font-size: 14px;
  }
  
  .request-id-pill .label { color: var(--color-text-secondary); }
  
  .spin {
    animation: spin 1s linear infinite;
    display: inline-block;
  }
  
  @keyframes spin { to { transform: rotate(360deg); } }
  </style>