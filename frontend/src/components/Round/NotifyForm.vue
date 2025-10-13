<template>
  <div class="notify-users-container">
    <div class="notify-users-form">
      <h3 class="form-title">{{ $t('montage-notify-jurors') }}</h3>

      <!-- Campaign and Round Name in a Row -->
      <div class="campaign-round-info-row">
        <p><strong>{{ $t('montage-campaign-name') }}:</strong> {{ campaignName }}</p>
        <p><strong>{{ $t('montage-round-name') }}:</strong> {{ roundName }}</p>
      </div>

      <!-- Jurors List -->
      <div class="jurors-list" v-if="jurorsList.length>0">
        <h4>{{ $t('montage-jurors-list') }}</h4>
        <ul>
          <li v-for="juror in jurorsList" :key="juror">{{ juror}}</li>
        </ul>
      </div>

      <!-- Notification Form -->
      <div class="form-group">
        <label for="title">{{ $t('montage-notify-title') }}</label>
        <input
          id="title"
          v-model="notificationTitle"
          type="text"
          :placeholder="$t('montage-notify-title-placeholder')"
          class="form-input"
        />
      </div>
      <div class="form-group">
        <label for="description">{{ $t('montage-notify-description') }}</label>
        <textarea
          id="description"
          v-model="notificationDescription"
          :placeholder="$t('montage-notify-description-placeholder')"
          class="form-textarea"
          rows="6"
        ></textarea>
      </div>
      <button @click="sendNotification" class="send-button">
        {{ $t('montage-send-notification') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import { useRoute, useRouter } from 'vue-router'
import jurorService from '@/services/jurorService'

const { t: $t } = useI18n()
const router = useRouter()
const route = useRoute()

const notificationTitle = ref('')
const notificationDescription = ref('')
const campaignName = ref('')
const roundName = ref('')
const roundInfo = ref([])
const jurorsList = ref([])

function sendNotification() {
  if (!notificationTitle.value || !notificationDescription.value) {
    alertService.error($t('montage-notify-error'))
    return
  }

  const payload = {
    title: notificationTitle.value,
    description: notificationDescription.value,
    jurorsList: jurorsList.value,
  };

  jurorService
    .sendNotification(payload)
    .then(() => {
      alertService.success($t('montage-notify-success'))
      router.push('/') 
    })
    .catch(alertService.error)
}

// Fetch campaign, round, and jurors data
async function fetchData() {
  try {
    // Fetch campaign details
    const campaignResponse = await adminService.getCampaign(route.params.campaignId)
    campaignName.value = campaignResponse.data.name

    // Fetch round details
    const roundResponse = await adminService.getRound(route.params.roundId)
    console.log('Round Response:', roundResponse.data) // Debugging
    roundName.value = roundResponse.data.name

    // Process jurors list from round details
    if (roundResponse.data && roundResponse.data.jurors) {
      jurorsList.value = roundResponse.data.jurors
        .filter(juror => juror.stats && juror.stats.total_tasks > 0) // Filter jurors with tasks
        .map(juror => juror.username) // Map to juror usernames
    } else {
      console.error('Jurors data not found in round details')
    }
  } catch (error) {
    console.error('Error fetching data:', error) // Log the error for debugging
    alertService.error($t('montage-fetch-error'))
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.notify-users-container {
  display: flex;
  justify-content: center; /* Center horizontally */
  align-items: center; /* Center vertically */
  min-height: calc(100vh - var(--topbar-height) - var(--bottombar-height)); /* Ensure it fills the available space */
  background-color: #f9f9f9;
  overflow: hidden;
  padding-top: 15vh;
}

.notify-users-form {
  background: #fff;
  padding: 32px;
  border: 1px solid #ddd;
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.campaign-round-info-row {
  display: flex; /* Display campaign and round name in a row */
  justify-content: space-between; /* Add space between the two items */
  margin-bottom: 16px;
}

.jurors-list {
  margin-bottom: 24px;
}

.jurors-list ul {
  list-style: none;
  padding: 0;
}

.jurors-list li {
  margin-bottom: 8px;
}

.form-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 24px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus,
.form-textarea:focus {
  border-color: #007bff;
}

.send-button {
  display: block;
  width: 100%;
  padding: 12px;
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: background-color 0.2s;
}

.send-button:hover {
  background-color: #0056b3;
}
</style>