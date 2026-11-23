<template>
  <div class="disqualify-view">
    <div class="disqualify-header">
      <cdx-button weight="quiet" @click="goBack">
        <arrow-left class="icon-small" />
        {{ $t('montage-disqualify-back-to-round') }}
      </cdx-button>
      <h1>{{ $t('montage-disqualify-title') }}</h1>
      <p v-if="round" class="disqualify-round-name">{{ round.name }}</p>
    </div>

    <div v-if="loading" class="disqualify-loading">
      <p>{{ $t('montage-disqualify-loading') }}</p>
    </div>

    <div v-else-if="round">
      <div v-if="round.status !== 'paused'" class="disqualify-warning">
        <alert-icon class="disqualify-warning-icon" />
        <p>
          {{ $t('montage-disqualify-readonly-warning') }}
          <strong>{{ round.status }}</strong>
        </p>
      </div>
      <div class="disqualify-stats">
        <p>
          {{
            $t('montage-disqualify-stats', [
              allEntries.length,
              qualifiedEntries.length,
              disqualifiedEntries.length
            ])
          }}
        </p>
      </div>
      <div class="disqualify-filters">
        <cdx-button
          :action="currentFilter === 'all' ? 'progressive' : 'default'"
          :weight="currentFilter === 'all' ? 'primary' : 'normal'"
          @click="setFilter('all')"
        >
          {{ $t('montage-filter-all') }} ({{ allEntries.length }})
        </cdx-button>
        <cdx-button
          :action="currentFilter === 'qualified' ? 'progressive' : 'default'"
          :weight="currentFilter === 'qualified' ? 'primary' : 'normal'"
          @click="setFilter('qualified')"
        >
          {{ $t('montage-filter-qualified') }} ({{ qualifiedEntries.length }})
        </cdx-button>
        <cdx-button
          :action="currentFilter === 'disqualified' ? 'progressive' : 'default'"
          :weight="currentFilter === 'disqualified' ? 'primary' : 'normal'"
          @click="setFilter('disqualified')"
        >
          {{ $t('montage-filter-disqualified') }} ({{ disqualifiedEntries.length }})
        </cdx-button>
        <cdx-text-input
          v-model="searchQuery"
          class="disqualify-search"
          :placeholder="$t('montage-search-placeholder')"
          clearable
        >
          <template #start-icon>
            <magnify-icon class="icon-small" />
          </template>
        </cdx-text-input>
      </div>

      <DisqualifyPanel
        :entries="paginatedEntries"
        :can-modify="round.status === 'paused'"
        @disqualify="openDisqualifyDialog"
        @requalify="handleRequalify"
      />
      <div v-if="totalPages > 1" class="disqualify-pagination">
        <cdx-button :disabled="currentPage === 1" @click="prevPage">
          <chevron-left class="icon-small" />
          {{ $t('montage-pagination-previous') }}
        </cdx-button>
        <span class="disqualify-page-info">
          {{ $t('montage-pagination-page-info', [currentPage, totalPages]) }}
        </span>
        <cdx-button :disabled="currentPage === totalPages" @click="nextPage">
          {{ $t('montage-pagination-next') }}
          <chevron-right class="icon-small" />
        </cdx-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CdxButton, CdxTextInput } from '@wikimedia/codex'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import dialogService from '@/services/dialogService'
import DisqualifyPanel from '@/components/Round/DisqualifyPanel.vue'
import DisqualifyDialog from '@/components/Round/DisqualifyDialog.vue'

import ArrowLeft from 'vue-material-design-icons/ArrowLeft.vue'
import ChevronLeft from 'vue-material-design-icons/ChevronLeft.vue'
import ChevronRight from 'vue-material-design-icons/ChevronRight.vue'
import AlertIcon from 'vue-material-design-icons/Alert.vue'
import MagnifyIcon from 'vue-material-design-icons/Magnify.vue'

const route = useRoute()
const router = useRouter()
const { t: $t } = useI18n()

const loading = ref(true)
const round = ref(null)
const allEntries = ref([])
const currentFilter = ref('all')
const currentPage = ref(1)
const entriesPerPage = 50
const searchQuery = ref('')

watch(searchQuery, () => {
  currentPage.value = 1
})

const disqualifiedEntries = computed(() => {
  return allEntries.value.filter((entry) => entry.dq_user_id)
})
const qualifiedEntries = computed(() => {
  return allEntries.value.filter((entry) => !entry.dq_user_id)
})
const filteredEntries = computed(() => {
  let entries
  if (currentFilter.value === 'qualified') {
    entries = qualifiedEntries.value
  } else if (currentFilter.value === 'disqualified') {
    entries = disqualifiedEntries.value
  } else {
    entries = allEntries.value
  }
  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    entries = entries.filter((entry) => {
      return (
        entry.name?.toLowerCase().includes(query) ||
        entry.upload_user_text?.toLowerCase().includes(query)
      )
    })
  }
  return entries
})

const totalPages = computed(() => {
  return Math.ceil(filteredEntries.value.length / entriesPerPage)
})
const paginatedEntries = computed(() => {
  const start = (currentPage.value - 1) * entriesPerPage
  const end = start + entriesPerPage
  return filteredEntries.value.slice(start, end)
})

const goBack = () => {
  router.back()
}
const setFilter = (filter) => {
  currentFilter.value = filter
  currentPage.value = 1
}
const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}
const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}
// `/entries` only returns entries that are not disqualified in this round,
// and uses `img_*` field names.
const fromExportRow = (entry) => ({
  id: entry.img_id,
  name: entry.img_name,
  width: entry.img_width,
  height: entry.img_height,
  mime_major: entry.img_major_mime,
  mime_minor: entry.img_minor_mime,
  upload_user_text: entry.img_user_text,
  dq_user_id: null,
  dq_reason: null
})

// `/disqualified` returns the entries disqualified in this round, with the
// full entry nested under `entry`.
const fromDqRow = (dq) => ({
  id: dq.entry.id,
  name: dq.entry.name,
  width: dq.entry.width,
  height: dq.entry.height,
  mime_major: dq.entry.mime_major,
  mime_minor: dq.entry.mime_minor,
  upload_user_text: dq.entry.upload_user_text,
  dq_user_id: dq.dq_user_id,
  dq_reason: dq.dq_reason
})

// Apply the server's list of disqualified entries: entries in it get the
// stored dq fields, entries no longer in it are cleared, new ones are added.
const applyDisqualified = (disqualifiedData) => {
  const dqById = new Map(disqualifiedData.map((dq) => [dq.entry.id, dq]))
  const seen = new Set()
  const merged = allEntries.value.map((entry) => {
    seen.add(entry.id)
    const dq = dqById.get(entry.id)
    return {
      ...entry,
      dq_user_id: dq ? dq.dq_user_id : null,
      dq_reason: dq ? dq.dq_reason : null
    }
  })
  disqualifiedData.forEach((dq) => {
    if (!seen.has(dq.entry.id)) {
      merged.push(fromDqRow(dq))
    }
  })
  allEntries.value = merged
}

const refreshDisqualified = async () => {
  const disqualifiedResponse = await adminService.getDisqualified(route.params.roundId)
  applyDisqualified(disqualifiedResponse.data || [])
}

const fetchData = async () => {
  const roundId = route.params.roundId
  loading.value = true
  try {
    const [roundResponse, entriesResponse, disqualifiedResponse] = await Promise.all([
      adminService.getRound(roundId),
      adminService.getRoundEntries(roundId),
      adminService.getDisqualified(roundId)
    ])
    round.value = roundResponse.data
    allEntries.value = (entriesResponse.file_infos || []).map(fromExportRow)
    applyDisqualified(disqualifiedResponse.data || [])
  } catch (error) {
    alertService.error(error)
  } finally {
    loading.value = false
  }
}

const openDisqualifyDialog = (entry) => {
  dialogService().show({
    title: $t('montage-disqualify-confirm-title'),
    props: {
      entry: entry,
      onSave: (reason) => {
        handleDisqualify(entry, reason)
      }
    },
    content: DisqualifyDialog,
    primaryAction: {
      label: $t('montage-disqualify-action'),
      actionType: 'destructive'
    },
    defaultAction: {
      label: $t('montage-btn-cancel')
    },
    maxWidth: '40rem'
  })
}

const handleDisqualify = async (entry, reason) => {
  const roundId = route.params.roundId
  try {
    await adminService.disqualifyEntry(roundId, entry.id, reason)
    alertService.success($t('montage-disqualify-success'))
    await refreshDisqualified()
  } catch (error) {
    alertService.error(error)
  }
}
const handleRequalify = async (entry) => {
  const roundId = route.params.roundId
  try {
    await adminService.requalifyEntry(roundId, entry.id)
    alertService.success($t('montage-requalify-success'))
    await refreshDisqualified()
  } catch (error) {
    alertService.error(error)
  }
}

onMounted(() => {
  fetchData()
})
</script>
<style scoped>
.disqualify-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}
.disqualify-header {
  margin-bottom: 24px;
}
.disqualify-header h1 {
  margin: 16px 0 8px 0;
}
.disqualify-round-name {
  color: #72777d;
  margin: 0;
}
.disqualify-loading {
  text-align: center;
  padding: 48px;
  color: #72777d;
}
.disqualify-stats {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 4px;
}
.disqualify-stats p {
  margin: 0;
  font-weight: 500;
}
.disqualify-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.disqualify-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #c8ccd1;
}
.disqualify-page-info {
  color: #72777d;
}
.icon-small {
  font-size: 6px;
}
.disqualify-warning {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin-bottom: 16px;
  background: #fef6e7;
  border: 1px solid #fc3;
  border-radius: 4px;
  color: #705000;
}
.disqualify-warning-icon {
  color: #fc3;
  font-size: 24px;
  flex-shrink: 0;
}
.disqualify-warning p {
  margin: 0;
}
.disqualify-search {
  margin-left: auto;
  min-width: 240px;
}
</style>
