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
            :action="currentFilter === 'all' ? 'progressive' : ''"
            :weight="currentFilter === 'all' ? 'primary' : 'normal'"
            @click="setFilter('all')"
          >
            {{ $t('montage-filter-all') }} ({{ allEntries.length }})
          </cdx-button>
          <cdx-button
            :action="currentFilter === 'qualified' ? 'progressive' : ''"
            :weight="currentFilter === 'qualified' ? 'primary' : 'normal'"
            @click="setFilter('qualified')"
          >
            {{ $t('montage-filter-qualified') }} ({{ qualifiedEntries.length }})
          </cdx-button>
          <cdx-button
            :action="currentFilter === 'disqualified' ? 'progressive' : ''"
            :weight="currentFilter === 'disqualified' ? 'primary' : 'normal'"
            @click="setFilter('disqualified')"
          >
            {{ $t('montage-filter-disqualified') }} ({{ disqualifiedEntries.length }})
          </cdx-button>
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
            Previous
          </cdx-button>
          <span class="disqualify-page-info">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <cdx-button :disabled="currentPage === totalPages" @click="nextPage">
            Next
            <chevron-right class="icon-small" />
          </cdx-button>
        </div>
      </div>
    </div>
  </template>

  <script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useI18n } from 'vue-i18n'
  import { CdxButton } from '@wikimedia/codex'
  import adminService from '@/services/adminService'
  import alertService from '@/services/alertService'
  import dialogService from '@/services/dialogService'
  import DisqualifyPanel from '@/components/Round/DisqualifyPanel.vue'
  import DisqualifyDialog from '@/components/Round/DisqualifyDialog.vue'
  
  import ArrowLeft from 'vue-material-design-icons/ArrowLeft.vue'
  import ChevronLeft from 'vue-material-design-icons/ChevronLeft.vue'
  import ChevronRight from 'vue-material-design-icons/ChevronRight.vue'
  import AlertIcon from 'vue-material-design-icons/Alert.vue'
 
  const route = useRoute()
  const router = useRouter()
  const { t: $t } = useI18n()
  
  const loading = ref(true)
  const round = ref(null)
  const allEntries = ref([])
  const currentFilter = ref('all')
  const currentPage = ref(1)
  const entriesPerPage = 50
  
  const disqualifiedEntries = computed(() => {
    return allEntries.value.filter((entry) => entry.dq_user_id)
  })
  const qualifiedEntries = computed(() => {
    return allEntries.value.filter((entry) => !entry.dq_user_id)
  })
  const filteredEntries = computed(() => {
    if (currentFilter.value === 'qualified') {
      return qualifiedEntries.value
    } else if (currentFilter.value === 'disqualified') {
      return disqualifiedEntries.value
    }
    return allEntries.value
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
  const fetchData = async () => {
    const roundId = route.params.roundId
    loading.value = true
    try {
        const roundResponse = await adminService.getRound(roundId)
        round.value = roundResponse.data
        
        const entriesResponse = await adminService.getRoundEntries(roundId)
        const rawEntries = entriesResponse.file_infos || []
        
        const disqualifiedResponse = await adminService.getDisqualified(roundId)
        const disqualifiedData = disqualifiedResponse.data || []
        
        const dqMap = new Map()
        disqualifiedData.forEach((dq) => {
        dqMap.set(dq.entry.id, {
            dq_user_id: dq.dq_user_id,
            dq_reason: dq.dq_reason
        })
        })
        
        allEntries.value = rawEntries.map((entry) => {
        const entryId = entry.img_id
        const dqInfo = dqMap.get(entryId)
        return {
            id: entry.img_id,
            name: entry.img_name,
            width: entry.img_width,
            height: entry.img_height,
            mime_major: entry.img_major_mime,
            mime_minor: entry.img_minor_mime,
            upload_user_text: entry.img_user_text,
            dq_user_id: dqInfo?.dq_user_id || null,
            dq_reason: dqInfo?.dq_reason || null
        }
    })} catch (error) {
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

      const index = allEntries.value.findIndex((e) => e.id === entry.id)
      if (index !== -1) {
        allEntries.value[index].dq_user_id = 1
        allEntries.value[index].dq_reason = reason
      }
    } catch (error) {
      alertService.error(error)
    }
  }
  const handleRequalify = async (entry) => {
    const roundId = route.params.roundId
    try {
      await adminService.requalifyEntry(roundId, entry.id)
      alertService.success($t('montage-requalify-success'))
      const index = allEntries.value.findIndex((e) => e.id === entry.id)
      if (index !== -1) {
        allEntries.value[index].dq_user_id = null
        allEntries.value[index].dq_reason = null
      }
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
</style>