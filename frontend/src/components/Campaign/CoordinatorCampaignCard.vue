<template>
  <router-link :to="link" class="card-router-link">
    <cdx-card class="coordinator-campaign-card" :icon="cdxIconImageLayoutFrameless">
      <template #title>
        {{ campaign.name }}
      </template>
      <template #description>
        <span class="coordinator-campaign-dates">
          {{ formatDate(campaign.open_date) }} - {{ formatDate(campaign.close_date) }}
        </span>
      </template>
      <template #supporting-text>
        <div class="coordinator-campaign-card-info">
          <p class="coordinator-campaign-card-info-label">Latest Round:</p>
          <p class="coordinator-campaign-card-latest-round">
            {{
              lastRound
                ? getVotingName(lastRound.round.vote_method) + ' - ' + lastRound.round.status
                : '-'
            }}
          </p>
          <p class="coordinator-campaign-card-info-label">
            Coordinators ({{ campaign.coordinators.length }})
          </p>
          <div class="coordinators-initials-container">
            <div
              v-for="(coordinator, index) in campaign.coordinators"
              :key="index"
              class="coordinator-initial"
              :style="{ backgroundColor: getAvatarColor(coordinator.username) }"
            >
              {{ coordinator.username[0] }}
            </div>
          </div>
        </div>
      </template>
    </cdx-card>
  </router-link>
</template>

<script setup>
import { CdxCard } from '@wikimedia/codex'
import { cdxIconImageLayoutFrameless } from '@wikimedia/codex-icons'
import { getAvatarColor, formatDate, getVotingName } from '@/utils'

const props = defineProps({
  campaign: {
    type: Object,
    required: true
  }
})

const link = 'campaign/' + [props.campaign.id, props.campaign.url_name].join('-')

let lastRound = null
if (props.campaign.rounds && props.campaign.rounds.length) {
  lastRound = {
    number: props.campaign.rounds.length,
    round: props.campaign.rounds[props.campaign.rounds.length - 1]
  }
}
</script>

<style scoped>
.card-router-link {
  text-decoration: none;
  cursor: pointer;
}

.coordinator-campaign-card {
  width: 320px;
}

.coordinator-campaign-dates {
  color: #666;
  font-size: 14px;
}

.coordinator-campaign-card-info-label {
  font-weight: bold;
  margin-bottom: 4px;
  color: black;
}

.coordinator-campaign-card-latest-round {
  margin-bottom: 8px;
}

.coordinators-initials-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.coordinator-initial {
  color: #fff;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}
</style>
