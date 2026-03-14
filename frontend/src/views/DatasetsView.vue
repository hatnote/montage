<template>
  <div class="datasets-container">
    <h2 class="datasets-heading">{{ $t('montage-datasets-title') }}</h2>
    <p class="datasets-description">{{ $t('montage-datasets-description') }}</p>
    <div v-if="isLoading" class="datasets-loading">
      <cdx-progress-bar />
    </div>
    <div v-else-if="datasets.length === 0" class="datasets-empty">
      <p>{{ $t('montage-datasets-no-data') }}</p>
    </div>
    <div v-else class="datasets-list">
      <cdx-card v-for="dataset in datasets" :key="dataset.id" class="dataset-card">
        <template #title>
          {{ dataset.name }}
        </template>
        <template #supporting-text>
          <div class="dataset-info">
            <span class="dataset-status"
              >{{ $t('montage-datasets-status') }}: {{ dataset.status }}</span
            >
          </div>
          <cdx-button
            class="download-button"
            action="progressive"
            @click="downloadDataset(dataset.id)"
          >
            {{ $t('montage-datasets-download') }}
          </cdx-button>
        </template>
      </cdx-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxCard, CdxButton, CdxProgressBar } from '@wikimedia/codex'
import dataService from '@/services/dataService'
const { t: $t } = useI18n()
const isLoading = ref(true)
const datasets = ref([])
const fetchDatasets = async () => {
  isLoading.value = true
  try {
    const response = await dataService.getResearchDatasets()
    datasets.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch research datasets:', error)
    datasets.value = []
  } finally {
    isLoading.value = false
  }
}
const downloadDataset = (campaignId) => {
  const url = dataService.getResearchDatasetDownloadUrl(campaignId)
  window.open(url, '_blank')
}
onMounted(() => {
  fetchDatasets()
})
</script>

<style scoped>
.datasets-container {
  padding: 40px;
  max-width: 800px;
  margin: 0 auto;
}
.datasets-heading {
  margin-bottom: 16px;
}
.datasets-description {
  margin-bottom: 24px;
  color: #54595d;
}
.datasets-loading {
  margin-top: 24px;
}
.datasets-empty {
  margin-top: 24px;
  padding: 24px;
  background-color: #f8f9fa;
  border-radius: 4px;
  text-align: center;
}
.datasets-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.dataset-card {
  padding: 16px;
}
.dataset-info {
  margin-bottom: 12px;
}
.dataset-status {
  color: #54595d;
  font-size: 14px;
}
.download-button {
  margin-top: 8px;
}
</style>
