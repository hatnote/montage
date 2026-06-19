<template>
    <div class="detail-page">
  
      <cdx-button action="progressive" weight="quiet" @click="$router.back()" style="margin-bottom: 1.5rem;">
        <cdx-icon :icon="cdxIconArrowPrevious" style="padding-right: 5px;" />
        {{ $t('back') }}
      </cdx-button>
  
      <div v-if="loading" class="state-placeholder">
        <clip-loader size="40px" />
      </div>
  
      <div v-else-if="loadError" class="state-placeholder">
        <cdx-message type="error" inline>{{ loadError }}</cdx-message>
      </div>
  
      <template v-else-if="req">
  
        <div class="detail-header">
          <div>
            <span class="request-id-label">{{ req.request_id }}</span>
            <h1>{{ req.campaign_name }}</h1>
            <p class="submitter">
              {{ $t('campaign-request-detail-submitted-by') }}
              <strong>{{ req.submitter_username }}</strong>
              · {{ formatRelative(req.create_date) }}
            </p>
          </div>
          <StatusBadge :status="req.status" size="lg" />
        </div>

        <div v-if="req.status === 'needs_clarification' && req.clarification_note" class="clarification-banner" role="note">
          <!--add !isSuperUser on v-if lster-->
          <p class="banner-title">
            <i class="ti ti-message-circle" aria-hidden="true"></i>
            <strong>{{ $t('campaign-request-clarification-note') }}</strong>
          </p>
          <p>{{ req.clarification_note }}</p>
          <router-link :to="`/requests/${req.request_id}/resubmit`">
            <cdx-button action="progressive" weight="normal">
              <i class="ti ti-edit" aria-hidden="true"></i>
              {{ $t('campaign-request-resubmit') }}
            </cdx-button>
          </router-link>
        </div>
  
        <cdx-message v-if="req.status === 'approved'" type="success" style="margin-bottom: 1.5rem;">
          {{ $t('campaign-request-approved-notice') }}
          <router-link v-if="req.campaign_id" :to="`/campaign/${req.campaign_id}`" class="campaign-link">
            {{ $t('campaign-request-view-campaign') }}
            <i class="ti ti-arrow-right" aria-hidden="true"></i>
          </router-link>
        </cdx-message>
  
          <div class="detail-card">
            <p class="card-label">{{ $t('campaign-request-field-coordinator') }}</p>
            <ul class="juror-list">
              <li v-for="juror in jurorList" :key="juror" class="juror-item">
                <i class="ti ti-user" aria-hidden="true"></i>
                {{ juror }}
                <a
                  :href="`https://commons.wikimedia.org/wiki/User:${juror}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="ext-link"
                  :aria-label="`View ${juror} on Wikimedia Commons`"
                >
                  <i class="ti ti-external-link" aria-hidden="true"></i>
                </a>
              </li>
            </ul>
          </div>
  
          <div class="detail-card">
            <p class="card-label">{{ $t('campaign-request-field-commons') }}</p>
            <p class="card-value text-wrap">{{ req.commons_category }}</p>
          </div>
  
          <div class="detail-card timeline-card">
            <p class="card-label">
              {{ $t('campaign-request-section-timeline') }}
              <span class="utc-pill">UTC</span>
            </p>
            <div class="timeline-dates">
              <div class="date-block">
                <span class="date-role">{{ $t('campaign-request-field-open-date') }}</span>
                <strong>{{ formatDateTime(req.open_date) }}</strong>
              </div>
              <i class="ti ti-arrow-right" aria-hidden="true"></i>
              <div class="date-block">
                <span class="date-role">{{ $t('campaign-request-field-close-date') }}</span>
                <strong>{{ formatDateTime(req.close_date) }}</strong>
              </div>
            </div>
            <!-- Maintainer or Superuser ? -->
            <div v-if="isSuperuser" class="tz-preview">
              <p class="tz-preview-label">
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
                    <td class="tz-name">{{ tz.label }}</td>
                    <td>{{ formatInTz(req.open_date, tz.id) }}</td>
                    <td>{{ formatInTz(req.close_date, tz.id) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
  
          <div class="detail-card" :class="{ 'card-warn': req.estimated_image_volume < 30 }">
            <p class="card-label">{{ $t('campaign-request-field-volume') }}</p>
            <p class="card-value card-value-lg">
              {{ req.estimated_image_volume }}
              <span class="volume-unit">{{ $t('campaign-request-images') }}</span>
            </p>
            <p v-if="req.estimated_image_volume < 30" class="warn-hint">
              <i class="ti ti-alert-triangle" aria-hidden="true"></i>
              {{ $t('campaign-request-volume-low-detail') }}
            </p>
          </div>
  
          <div class="detail-card purpose-card">
            <p class="card-label">{{ $t('campaign-request-field-purpose') }}</p>
            <p class="card-value text-wrap">{{ req.purpose }}</p>
          </div>
  
        <!-- Maintainers action, -->
        <div v-if="isSuperuser " class="action-section">
          <h2>{{ $t('campaign-request-actions-title') }}</h2>
  
          <div class="action-tabs" role="tablist">
            <cdx-button
              :action="activeAction === 'approve' ? 'progressive' : 'default'"
              :weight="activeAction === 'approve' ? 'primary' : 'normal'"
              @click="activeAction = 'approve'"
            >
              <i class="ti ti-circle-check" aria-hidden="true"></i>
              {{ $t('campaign-request-action-approve') }}
            </cdx-button>
            <cdx-button
              :action="activeAction === 'advise' ? 'progressive' : 'default'"
              :weight="activeAction === 'advise' ? 'primary' : 'normal'"
              @click="activeAction = 'advise'"
            >
              <i class="ti ti-message-circle" aria-hidden="true"></i>
              {{ $t('campaign-request-action-advise') }}
            </cdx-button>
          </div>
  
          <div v-if="activeAction === 'approve'" class="action-panel" role="tabpanel">
            <cdx-message v-if="req.estimated_image_volume < 30" type="warning" style="margin-bottom: 1rem;">
              <strong>{{ $t('campaign-request-low-volume-header') }}</strong>
              <p style="margin: 4px 0 0; font-size: 13px;">{{ $t('campaign-request-low-volume-advice') }}</p>
            </cdx-message>
            <p class="action-description">{{ $t('campaign-request-approve-description') }}</p>
            <div class="action-row">
              <cdx-button action="progressive" weight="primary" :disabled="approving" @click="approveRequest">
                <i v-if="approving" class="ti ti-loader-2 spin" aria-hidden="true"></i>
                <i v-else class="ti ti-circle-check" aria-hidden="true"></i>
                {{ approving ? $t('campaign-request-approving') : $t('campaign-request-action-approve') }}
              </cdx-button>
            </div>
            <p v-if="actionError" class="action-error" role="alert">{{ actionError }}</p>
          </div>
  
          <div v-if="activeAction === 'advise'" class="action-panel" role="tabpanel">
            <p class="action-description">{{ $t('campaign-request-advise-description') }}</p>
  
            <div class="template-chips">
              <span class="template-label">{{ $t('campaign-request-templates') }}</span>
              <button
                v-for="tpl in NOTE_TEMPLATES"
                :key="tpl.key"
                class="chip"
                @click="adviseNote = $t(tpl.key)"
              >
                {{ $t(tpl.labelKey) }}
              </button>
            </div>
  
            <cdx-field style="margin-bottom: 0.75rem;">
              <cdx-text-area v-model="adviseNote" :placeholder="$t('campaign-request-advise-placeholder')" :autosize="true" />
              <template #help-text>{{ $t('campaign-request-advise-hint') }}</template>
            </cdx-field>

            <div class="action-row">
              <cdx-button action="progressive" weight="normal" :disabled="advising || !adviseNote.trim()" @click="sendAdvice">
                <i v-if="advising" class="ti ti-loader-2 spin" aria-hidden="true"></i>
                <i v-else class="ti ti-send" aria-hidden="true"></i>
                {{ advising ? $t('campaign-request-sending') : $t('campaign-request-action-send-note') }}
              </cdx-button>
            </div>
            <cdx-message v-if="actionError" type="error" inline style="margin-top: 8px;">{{ actionError }}</cdx-message>
          </div>
        </div>
  
        <cdx-message v-if="actionSuccess" type="success" style="margin-top: 1rem;">
          {{ actionSuccess }}
        </cdx-message>
  
      </template>
    </div>
  </template>
  
  <script setup>
  import { ref, computed ,onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useI18n } from 'vue-i18n'
  import { CdxButton, CdxMessage, CdxTextArea, CdxField, CdxIcon } from '@wikimedia/codex'
  import { cdxIconArrowPrevious } from '@wikimedia/codex-icons'
  import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
  import dayjs from 'dayjs'
  import relativeTime from 'dayjs/plugin/relativeTime'
  import adminService from '@/services/adminService'
  import StatusBadge from '@/views/Statusbadge.vue'
  
  dayjs.extend(relativeTime)
  
  const { t } = useI18n()
  const route = useRoute()
  const router = useRouter()
  
  const props = defineProps({
    isSuperuser: { type: Boolean, default: false },
  })
  const isSuperuser = true;
  
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
  
  const NOTE_TEMPLATES = [
    { key: 'campaign-request-template-low-volume',    labelKey: 'campaign-request-template-low-volume-label' },
    { key: 'campaign-request-template-check-dates',   labelKey: 'campaign-request-template-check-dates-label' },
    { key: 'campaign-request-template-missing-info',  labelKey: 'campaign-request-template-missing-info-label' },
  ]
  
  
  const req = ref(null)
  const loading = ref(false)
  const loadError = ref('')
  const activeAction = ref('approve')
  const adviseNote = ref('')
  const approving = ref(false)
  const advising = ref(false)
  const actionError = ref('')
  const actionSuccess = ref('')

  const jurorList = computed(() => {
  const jurors = req.value?.jury_coordinator_username
    if (Array.isArray(jurors)) return jurors
    return jurors ? [jurors] : []
  })
    
  async function loadRequest() {
    loading.value = true
    loadError.value = ''
    console.log(route.params)
    console.log("the request id is (outer try)",route.params.requestId) // To-do: Change it back to requestId
    
    try {
      const res = await adminService.getCampaignRequest(route.params.requestId)
      req.value = res.data.data || res.data || null
      console.log("the request id is", route.params.requestId)
    } catch (err) {
      loadError.value = err?.response?.data?.description || t('load-error')
    } finally {
      loading.value = false
    }
  }
  
  
  async function approveRequest() {
    approving.value = true
    actionError.value = ''
    actionSuccess.value = ''
    try {
      await adminService.approveCampaignRequest(req.value.request_id)
      actionSuccess.value = t('campaign-request-approve-success')
      await loadRequest() 
    } catch (err) {
      actionError.value = err?.response?.data?.description || t('action-error')
    } finally {
      approving.value = false
    }
  }
  
  async function sendAdvice() {
    if (!adviseNote.value.trim()) return
    advising.value = true
    actionError.value = ''
    actionSuccess.value = ''
    try {
      await adminService.adviseCampaignRequest(req.value.request_id, adviseNote.value)
      actionSuccess.value = t('campaign-request-advise-success')
      adviseNote.value = ''
      await loadRequest()
    } catch (err) {
      actionError.value = err?.response?.data?.description || t('action-error')
    } finally {
      advising.value = false
    }
  }
    
  function formatDateTime(iso) {
    if (!iso) return '—'
    return dayjs(iso).format('D MMM YYYY, HH:mm') + ' UTC'
  }
  
  function formatRelative(iso) {
    return iso ? dayjs(iso).fromNow() : ''
  }
  
  function formatInTz(iso, tzId) {
    if (!iso) return '—'
    try {
      return new Intl.DateTimeFormat('en-GB', {
        timeZone: tzId,
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(iso))
    } catch {
      return '—'
    }
  }
  
  onMounted(loadRequest)
  </script>
  
  <style scoped>
  .detail-page {
    max-width: 820px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }
  
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  
  .request-id-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--color-text-secondary);
    letter-spacing: 0.05em;
  }
  
  .detail-header h1 {
    font-size: 22px;
    font-weight: 500;
    margin: 4px 0 6px;
  }
  
  .submitter { font-size: 13px; color: var(--color-text-secondary); margin: 0; }
  
  .clarification-banner {
    background: #fdf2d5;
    border: 1px solid #f0c533;
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
    color: #ac6600;
  }
  
  .banner-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
    font-size: 14px;
    margin-bottom: 0.5rem;
  }
  
  .clarification-banner p { margin: 0 0 1rem; font-size: 14px; line-height: 1.6; }
  
  .campaign-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #14866d;
    text-decoration: underline;
  }
  
  .details-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    margin-bottom: 2rem;
  }
  
  .detail-card {
    background: var(--color-background-primary);
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: var(--border-radius-lg);
    padding: 1rem 1.25rem;
  }
  
  .detail-card.card-warn {
    border-color: var(--color-border-warning);
    background: var(--color-background-warning);
  }
  
  .timeline-card, .purpose-card {
    grid-column: 1 / -1;
  }
  
  .card-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text-secondary);
    margin: 0 0 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  .card-value {
    font-size: 15px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--color-text-primary);
  }
  
  .card-value-lg {
    font-size: 24px;
    font-weight: 500;
  }
  
  .text-wrap { white-space: pre-wrap; word-break: break-word; }
  
  .volume-unit { font-size: 14px; font-weight: 400; color: var(--color-text-secondary); }
  
  .warn-hint {
    font-size: 12px;
    color: var(--color-text-warning);
    margin: 6px 0 0;
    display: flex;
    align-items: flex-start;
    gap: 5px;
  }
  
  .ext-link { color: var(--color-text-secondary); font-size: 14px; }
  
  .utc-pill {
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border-radius: var(--border-radius-md);
    font-size: 10px;
    padding: 1px 6px;
  }
  
  .timeline-dates {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }
  
  .date-block {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  
  .date-role { font-size: 11px; color: var(--color-text-secondary); }
  .date-block strong { font-size: 14px; font-weight: 500; }
  
  .tz-preview {
    margin-top: 1rem;
    background: var(--color-background-secondary);
    border-radius: var(--border-radius-md);
    border: 0.5px solid var(--color-border-tertiary);
    padding: 0.75rem 1rem;
  }
  
  .tz-preview-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text-secondary);
    margin: 0 0 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  .tz-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .tz-table th {
    text-align: left;
    color: var(--color-text-secondary);
    font-weight: 500;
    padding: 3px 8px 3px 0;
    border-bottom: 0.5px solid var(--color-border-tertiary);
  }
  .tz-table td {
    padding: 4px 8px 4px 0;
    border-bottom: 0.5px solid var(--color-border-tertiary);
    color: var(--color-text-primary);
  }
  .tz-name { color: var(--color-text-secondary); }
  
  .action-section {
    border-top: 0.5px solid var(--color-border-tertiary);
    padding-top: 1.5rem;
  }
  
  .action-section h2 {
    font-size: 16px;
    font-weight: 500;
    margin: 0 0 1rem;
  }
  
  .action-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 1.25rem;
  }
  
  .action-panel { padding: 0; }
  
  .action-description {
    font-size: 14px;
    color: var(--color-text-secondary);
    margin: 0 0 1rem;
    line-height: 1.5;
  }
  
  .template-chips {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }
  
  .template-label { font-size: 12px; color: var(--color-text-secondary); }
  
  .chip {
    padding: 3px 10px;
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: var(--border-radius-md);
    background: var(--color-background-secondary);
    font-size: 12px;
    cursor: pointer;
    color: var(--color-text-secondary);
  }
  
  .chip:hover { color: var(--color-text-primary); border-color: var(--color-border-secondary); }
    
  .action-row { display: flex; gap: 10px; flex-wrap: wrap; }
  
  .state-placeholder {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-secondary);
    font-size: 32px;
  }
  
  </style>