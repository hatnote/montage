<template>
  <div class="notify-users-container">
    <div class="notify-users-form">
      <h3 class="form-title">{{ $t('montage-notify-jurors') }}</h3>
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
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/adminService'
import alertService from '@/services/alertService'
import { useRoute, useRouter } from 'vue-router'

const { t: $t } = useI18n()
const router = useRouter()
const route = useRoute()

const notificationTitle = ref('')
const notificationDescription = ref('')

function sendNotification() {
  if (!notificationTitle.value || !notificationDescription.value) {
    alertService.error($t('montage-notify-error'))
    return
  }

  adminService
    .sendNotification({
      title: notificationTitle.value,
      description: notificationDescription.value,
      roundId: route.params.roundId,
      campaignId: route.params.campaignId
    })
    .then(() => {
      alertService.success($t('montage-notify-success'))
      router.push('/round-info') // Navigate back to the round info page
    })
    .catch(alertService.error)
}
</script>

<style scoped>
.notify-users-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh; /* Full viewport height */
  background-color: #f9f9f9;
  overflow: hidden;
  
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