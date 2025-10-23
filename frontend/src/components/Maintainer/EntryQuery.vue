<template>
  <div class="entry-query-page">
    <div class="page-header">
      <h1>{{ $t('montage-entry-query') }}</h1>
      <p v-if="roundInfo">
        {{ $t('montage-round-name') }}: <strong>{{ roundInfo.name }}</strong> (ID: {{ roundId }})
      </p>
      <p v-else>{{ $t('montage-search-and-remove-entries') }}</p>
    </div>

    <!-- Search Form -->
    <div class="search-box">
      <cdx-field :label="$t('montage-image-name-optional')">
        <cdx-text-input 
          v-model="searchTerm" 
          :placeholder="$t('montage-search-by-filename')"
          @keyup.enter="search"
        />
      </cdx-field>

      <cdx-button 
        action="progressive" 
        weight="primary" 
        @click="search"
        :disabled="!roundId"
      >
        <magnify class="icon-small" />
        {{ $t('montage-search') }}
      </cdx-button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <cdx-progress-bar :inline="true" />
      <p>{{ $t('montage-searching') }}...</p>
    </div>

    <!-- Results -->
    <div v-if="results.length > 0 && !loading" class="results">
      <h2>{{ $t('montage-results') }} ({{ total }})</h2>
      
      <table class="results-table">
        <thead>
          <tr>
            <th>{{ $t('montage-thumbnail') }}</th>
            <th>{{ $t('montage-image-name') }}</th>
            <th>{{ $t('montage-uploader') }}</th>
            <th>{{ $t('montage-votes') }}</th>
            <th>{{ $t('montage-actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in results" :key="entry.id">
            <td>
              <img :src="entry.url_sm" :alt="entry.name" class="thumb" />
            </td>
            <td>
              <a :href="entry.url" target="_blank">{{ truncate(entry.name) }}</a>
            </td>
            <td>{{ entry.upload_user_text }}</td>
            <td>{{ entry.completed_votes || 0 }} / {{ entry.active_votes || 0 }}</td>
            <td>
              <cdx-button 
                action="destructive" 
                weight="quiet" 
                @click="confirmRemove(entry)"
              >
                <delete-icon class="icon-small" />
                {{ $t('montage-remove') }}
              </cdx-button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="pagination" v-if="total > pageSize">
        <cdx-button @click="prevPage" :disabled="page === 1">
          {{ $t('montage-previous') }}
        </cdx-button>
        <span>{{ $t('montage-page') }} {{ page }} {{ $t('montage-of') }} {{ Math.ceil(total / pageSize) }}</span>
        <cdx-button @click="nextPage" :disabled="page >= Math.ceil(total / pageSize)">
          {{ $t('montage-next') }}
        </cdx-button>
      </div>
    </div>

    <!-- No Results -->
    <div v-if="results.length === 0 && searched && !loading" class="no-results">
      <p>{{ $t('montage-no-results-found') }}</p>
    </div>

    <!-- Remove Dialog -->
    <cdx-dialog
      v-model:open="showDialog"
      :title="$t('montage-confirm-removal')"
      :primary-action="{ label: $t('montage-remove'), actionType: 'destructive' }"
      :default-action="{ label: $t('montage-cancel') }"
      @primary="remove"
      @default="showDialog = false"
    >
      <p v-if="selectedEntry">
        {{ $t('montage-remove-entry-confirm', { name: selectedEntry.name }) }}
      </p>
      
      <cdx-field :label="$t('montage-reason-optional')">
        <cdx-text-area 
          v-model="reason" 
          :placeholder="$t('montage-enter-reason')" 
          rows="3" 
        />
      </cdx-field>

      <cdx-message type="warning" :inline="true">
        {{ $t('montage-removal-warning') }}
      </cdx-message>
    </cdx-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { 
  CdxField, 
  CdxTextInput, 
  CdxTextArea, 
  CdxButton, 
  CdxDialog, 
  CdxMessage, 
  CdxProgressBar 
} from '@wikimedia/codex'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'

// Icons
import Magnify from 'vue-material-design-icons/Magnify.vue'
import Delete from 'vue-material-design-icons/Delete.vue'

const route = useRoute()
const { t: $t } = useI18n()

const roundId = ref(null)
const roundInfo = ref(null)
const searchTerm = ref('')
const loading = ref(false)
const searched = ref(false)
const results = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)

const showDialog = ref(false)
const selectedEntry = ref(null)
const reason = ref('')

// Get round ID from query parameter
onMounted(async () => {
  const queryRoundId = route.query.roundId
  
  if (queryRoundId) {
    roundId.value = parseInt(queryRoundId)
    
    // Fetch round info
    try {
      const response = await adminService.getRound(roundId.value)
      roundInfo.value = response.data
      
      // Auto-search on mount
      search()
    } catch (error) {
      alertService.error($t('montage-error-loading-round'))
    }
  } else {
    alertService.error($t('montage-no-round-specified'))
  }
})

const search = async () => {
  if (!roundId.value) return
  
  loading.value = true
  searched.value = true
  page.value = 1
  
  try {
    const params = {
      search: searchTerm.value,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value
    }
    
    const response = await adminService.searchRoundEntries(roundId.value, params)
    results.value = response.data.entries
    total.value = response.data.total
  } catch (error) {
    alertService.error(error)
    results.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const confirmRemove = (entry) => {
  selectedEntry.value = entry
  reason.value = ''
  showDialog.value = true
}

const remove = async () => {
  if (!selectedEntry.value) return
  
  try {
    await adminService.removeEntry(
      roundId.value,
      selectedEntry.value.id,
      { reason: reason.value }
    )
    
    alertService.success($t('montage-entry-removed-successfully'))
    showDialog.value = false
    search() // Refresh results
  } catch (error) {
    alertService.error(error)
  }
}

const truncate = (name) => {
  return name.length > 50 ? name.substring(0, 47) + '...' : name
}

const prevPage = () => {
  if (page.value > 1) {
    page.value--
    search()
  }
}

const nextPage = () => {
  if (page.value < Math.ceil(total.value / pageSize.value)) {
    page.value++
    search()
  }
}
</script>

<style scoped>
.entry-query-page {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.page-header p {
  color: #666;
  font-size: 16px;
}

.search-box {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  margin: 24px 0;
  display: flex;
  gap: 16px;
  align-items: flex-end;
  max-width: 800px;
}

.search-box .cdx-field {
  flex: 1;
}

.loading {
  text-align: center;
  padding: 40px;
}

.results {
  margin-top: 32px;
}

.results h2 {
  margin-bottom: 16px;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border-radius: 8px;
  overflow: hidden;
}

.results-table th,
.results-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.results-table th {
  background: #f5f5f5;
  font-weight: 600;
}

.results-table tbody tr:hover {
  background: #f8f9fa;
}

.thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.no-results {
  text-align: center;
  padding: 60px;
  color: #666;
}

.icon-small {
  font-size: 16px;
}
</style>