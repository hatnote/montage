<template>
    <div class="requests-page">
      <div class="page-header">
        <div>
          <h1>{{ $t('campaign-requests-title') }}</h1>
          <p class="subtitle">{{ $t('campaign-requests-subtitle') }}</p>
        </div>
        <router-link to="/requests/new" class="btn-primary">
          <i class="ti ti-plus" aria-hidden="true"></i>
          {{ $t('campaign-request-new') }}
        </router-link>
      </div>
  
      <div v-if="isSuperuser" class="filters" role="group" aria-label="Filter by status">
        <button
          v-for="f in STATUS_FILTERS"
          :key="f.value"
          class="filter-btn"
          :class="{ active: activeFilter === f.value }"
          @click="setFilter(f.value)"
        >
          {{ $t(f.labelKey) }}
          <span v-if="counts[f.value] != null" class="filter-count">{{ counts[f.value] }}</span>
        </button>
      </div>
  
      <div v-if="loading" class="state-placeholder">
        <i class="ti ti-loader-2 spin" aria-hidden="true"></i>
        {{ $t('loading') }}
      </div>
  
      <div v-else-if="loadError" class="state-placeholder state-error">
        <i class="ti ti-circle-x" aria-hidden="true"></i>
        {{ loadError }}
      </div>
  
      <div v-else-if="filteredRequests.length === 0" class="state-placeholder">
        <i class="ti ti-inbox" aria-hidden="true"></i>
        <p>{{ $t('campaign-requests-empty') }}</p>
        <router-link to="/requests/new" class="btn-secondary">
          {{ $t('campaign-request-new') }}
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
              <i class="ti ti-user" aria-hidden="true"></i>
              {{ req.jury_coordinator_username }}
              <span class="dot">·</span>
              <i class="ti ti-calendar" aria-hidden="true"></i>
              {{ formatDate(req.open_date) }} — {{ formatDate(req.close_date) }}
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
                <i class="ti ti-alert-triangle" aria-hidden="true"></i>
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
  import dayjs from 'dayjs'
  import relativeTime from 'dayjs/plugin/relativeTime'
  import adminService from '@/services/adminService'
  import StatusBadge from '@/views/Statusbadge.vue'
  
  dayjs.extend(relativeTime)
  
  const { t } = useI18n()
  const router = useRouter()
  
  const props = defineProps({
    isSuperuser: { type: Boolean, default: false },
  })
  
  const STATUS_FILTERS = [
    { value: null,                  labelKey: 'status-all' },
    { value: 'pending',             labelKey: 'status-pending' },
    { value: 'needs_clarification', labelKey: 'status-needs-clarification' },
    { value: 'approved',            labelKey: 'status-approved' },
  ]
  
  const requests = ref([])
  const loading = ref(false)
  const loadError = ref('')
  const activeFilter = ref(null)
  
  const counts = computed(() => {
    const c = { null: requests.value.length }
    requests.value.forEach(r => {
      c[r.status] = (c[r.status] || 0) + 1
    })
    return c
  })
  
  const filteredRequests = computed(() => {
    if (!activeFilter.value) return requests.value
    return requests.value.filter(r => r.status === activeFilter.value)
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
    max-width: 820px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }
  
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.75rem;
    flex-wrap: wrap;
  }
  
  .page-header h1 { font-size: 22px; font-weight: 500; margin: 0 0 0.3rem; }
  .subtitle { font-size: 14px; color: var(--color-text-secondary); margin: 0; }
  
  .filters {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 1.25rem;
  }
  
  .filter-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: var(--border-radius-md);
    border: 0.5px solid var(--color-border-tertiary);
    background: transparent;
    font-size: 13px;
    cursor: pointer;
    color: var(--color-text-secondary);
  }
  
  .filter-btn:hover { background: var(--color-background-secondary); }
  .filter-btn.active {
    background: var(--color-background-secondary);
    color: var(--color-text-primary);
    border-color: var(--color-border-primary);
  }
  
  .filter-count {
    background: var(--color-background-secondary);
    border-radius: 10px;
    font-size: 11px;
    padding: 1px 7px;
    color: var(--color-text-secondary);
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
    background: var(--color-background-primary);
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: var(--border-radius-lg);
    padding: 1rem 1.25rem;
    cursor: pointer;
    transition: border-color 0.15s;
  }
  
  .request-card:hover { border-color: var(--color-border-secondary); }
  .request-card:focus-visible { outline: 2px solid var(--color-border-info); outline-offset: 2px; }
  
  .card-left { flex: 1; min-width: 0; }
  
  .request-id {
    font-size: 11px;
    font-weight: 500;
    color: var(--color-text-secondary);
    letter-spacing: 0.04em;
  }
  
  .campaign-name {
    font-size: 15px;
    font-weight: 500;
    margin: 3px 0 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .campaign-meta {
    font-size: 12px;
    color: var(--color-text-secondary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 5px;
    flex-wrap: wrap;
  }
  
  .dot { opacity: 0.4; }
  
  .card-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    flex-shrink: 0;
  }
  
  .volume-info {
    font-size: 12px;
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: 5px;
  }
  
  .low-volume-pill {
    font-size: 11px;
    background: var(--color-background-warning);
    color: var(--color-text-warning);
    border-radius: var(--border-radius-md);
    padding: 1px 6px;
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
  
  .submit-date {
    font-size: 11px;
    color: var(--color-text-secondary);
  }
  
  .state-placeholder {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-secondary);
    font-size: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }
  
  .state-placeholder i { font-size: 32px; opacity: 0.5; }
  .state-error { color: var(--color-text-danger); }
  
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.5rem 1.1rem;
    border: 0.5px solid var(--color-border-secondary);
    border-radius: var(--border-radius-md);
    background: var(--color-background-primary);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    color: var(--color-text-primary);
    text-decoration: none;
  }
  
  .btn-primary:hover { background: var(--color-background-secondary); }
  
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.5rem 1rem;
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: var(--border-radius-md);
    background: transparent;
    font-size: 13px;
    cursor: pointer;
    color: var(--color-text-secondary);
    text-decoration: none;
  }
  
  .spin { animation: spin 1s linear infinite; display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
  </style>