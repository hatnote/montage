<template>
  <div class="requests-page">
    <div class="page-header">
      <div>
        <h1>{{ $t('campaign-requests-title') }}</h1>
        <p class="subtitle">{{ $t('campaign-requests-subtitle') }}</p>
      </div>
      <router-link to="/requests/new">
        <cdx-button action="progressive" weight="primary">
          <cdx-icon :icon="cdxIconAdd" />
          {{ $t('campaign-request-new') }}
        </cdx-button>
      </router-link>
    </div>
    <!-- Add v-if="isSuperuser" clause for this div later -->
    <div class="filters" role="group" aria-label="Filter by status">
      <cdx-button
        v-for="f in STATUS_FILTERS"
        :key="f.value"
        :action="activeFilter === f.value ? 'progressive' : 'default'"
        :weight="activeFilter === f.value ? 'primary' : 'normal'"
        @click="setFilter(f.value)"
      >
        {{ $t(f.labelKey) }}
        <span v-if="counts[f.value] != null" class="filter-count">{{ counts[f.value] }}</span>
      </cdx-button>
    </div>

    <div v-if="loading" class="state-placeholder">
      <clip-loader size="40px" />
    </div>

    <div v-else-if="loadError" class="state-placeholder state-error">
      <cdx-message type="error" inline>
        <cdx-icon :icon="cdxIconError" />
        {{ loadError }}
      </cdx-message>
    </div>

    <div v-else-if="filteredRequests.length === 0" class="state-placeholder">
      <cdx-message type="notice" inline>
        {{ $t('campaign-requests-empty') }}
      </cdx-message>
      <router-link to="/requests/new">
        <cdx-button action="progressive" weight="normal">
          {{ $t('campaign-request-new') }}
        </cdx-button>
      </router-link>
    </div>

    <ul v-else class="request-list" role="list">
      <li
        v-for="req in filteredRequests"
        :key="req.id"
        class="request-card"
        @click="viewRequest(req.request_id)"
        role="button"
        tabindex="0"
        :aria-label="`${req.request_id} — ${req.campaign_name}`"
        @keydown.enter="viewRequest(req.request_id)"
        @keydown.space.prevent="viewRequest(req.request_id)"
      >
        <div class="card-left">
          <span class="request-id">{{ req.request_id }}</span>
          <h2 class="campaign-name">{{ req.campaign_name }}</h2>
          <p class="campaign-meta">
            <span class="meta-group">
              <cdx-icon :icon="cdxIconUserAvatar" size="small" />
              {{ req.submitter_username }}
            </span>

            <span class="meta-group">
              <cdx-icon :icon="cdxIconCalendar" size="small" />
              {{ formatDate(req.open_date) }} — {{ formatDate(req.close_date) }}
            </span>
          </p>
        </div>

        <div class="card-right">
          <StatusBadge :status="req.status" />
          <div class="volume-info">
            <i class="ti ti-photo" aria-hidden="true"></i>
            {{ req.estimated_image_volume }}
            <span
              v-if="req.estimated_image_volume < 30"
              class="low-volume-pill"
              :title="$t('campaign-request-volume-low-warning')"
            >
              <cdx-icon :icon="cdxIconAlert" size="x-small" />
              {{ $t('campaign-request-low') }}
            </span>
          </div>
          <span class="submit-date">
            {{ $t('campaign-requests-submitted') }} {{ formatRelative(req.create_date) }}
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CdxButton, CdxToggleButtonGroup, CdxMessage, CdxIcon } from '@wikimedia/codex'
import {
  cdxIconAdd,
  cdxIconUserAvatar,
  cdxIconCalendar,
  cdxIconAlert,
  cdxIconError
} from '@wikimedia/codex-icons'
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import adminService from '@/services/adminService'
import StatusBadge from '@/views/Statusbadge.vue'

dayjs.extend(relativeTime)

const { t } = useI18n()
const router = useRouter()

const props = defineProps({
  isSuperuser: { type: Boolean, default: false }
})

const STATUS_FILTERS = [
  { value: null, labelKey: 'status-all' },
  { value: 'pending', labelKey: 'status-pending' },
  { value: 'needs_clarification', labelKey: 'status-needs-clarification' },
  { value: 'approved', labelKey: 'status-approved' }
]

const requests = ref([])
const loading = ref(false)
const loadError = ref('')
const activeFilter = ref(null)

const counts = computed(() => {
  const c = { null: requests.value.length }
  requests.value.forEach((r) => {
    c[r.status] = (c[r.status] || 0) + 1
  })
  return c
})

const filteredRequests = computed(() => {
  if (!activeFilter.value) return requests.value
  return requests.value.filter((r) => r.status === activeFilter.value)
})

function setFilter(val) {
  activeFilter.value = val
}

async function loadRequests() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await adminService.getCampaignRequests()
    requests.value = res.data.data || res.data || []
  } catch (err) {
    loadError.value = err?.response?.data?.description || t('load-error')
  } finally {
    loading.value = false
  }
}

function viewRequest(requestId) {
  router.push(`/requests/${requestId}`)
}

function formatDate(iso) {
  if (!iso) return '—'
  return dayjs(iso).format('D MMM YYYY')
}

function formatRelative(iso) {
  if (!iso) return ''
  return dayjs(iso).fromNow()
}

onMounted(loadRequests)
</script>

<style scoped>
.requests-page {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.75rem;
  flex-wrap: wrap;
}

.page-header h1 {
  font-size: 32px;
  font-weight: bold;
  margin: 0 0 0.3rem;
  color: #202122;
}

.subtitle {
  font-size: 14px;
  color: #72777d;
  margin: 0;
}

.filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.filter-count {
  border-radius: 10px;
  font-size: 13px;
  padding: 1px 7px;
}

.request-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.request-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  background: #ffffff;
  border: 1px solid #c8ccd1;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: border-color 0.15s ease-in-out;
}

.request-card:hover {
  border-color: #72777d;
}

.request-card:focus-visible {
  outline: 2px solid #3366cc;
  outline-offset: 2px;
}

.card-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.request-id {
  font-size: 11px;
  font-weight: 500;
  color: #72777d;
  letter-spacing: 0.04em;
}

.campaign-name {
  font-size: 15px;
  font-weight: bold;
  margin: 3px 0 5px;
  white-space: normal;
  word-break: break-word;
  color: #202122;
}

.campaign-meta {
  font-size: 12px;
  color: #72777d;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.meta-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  opacity: 0.4;
}

.card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.volume-info {
  font-size: 12px;
  color: #72777d;
  display: flex;
  align-items: center;
  gap: 5px;
}

.low-volume-pill {
  font-size: 11px;
  background: #fdf2d5;
  color: #ac6600;
  border-radius: 4px;
  padding: 1px 6px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.submit-date {
  font-size: 11px;
  color: #72777d;
}

.state-placeholder {
  text-align: center;
  padding: 4rem 1rem;
  color: #72777d;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.state-placeholder i {
  font-size: 32px;
  opacity: 0.5;
}

.state-error {
  color: #d73333;
}

.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .request-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .card-right {
    align-items: flex-start;
    width: 100%;
    border-top: 1px solid #c8ccd1;
    padding-top: 0.75rem;
  }
}
</style>
