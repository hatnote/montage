<template>
  <cdx-accordion open class="juror-campaign-accordion">
    <template #title>
      <h3>{{ campaign[0].campaign.name }}</h3>
    </template>
    <div v-for="(round, index) in campaign" :key="index" class="juror-campaign-round-card">
      <div class="round-header">
        <ThumbsUpDown class="juror-campaign-round-icon" :size="36" fillColor="white" />
        <div class="round-info">
          <p>{{ round.name }}</p>
          <p>({{ getVotingName(round.vote_method) }} · {{ round.status }})</p>
        </div>
      </div>
      <div class="card-container">
        <cdx-card class="information-card">
          <template #supporting-text>
            <div class="supporting-info">
              <div class="directions">
                <p><strong>Voting deadline:</strong> {{ round.deadline_date?.split('T')[0] }}</p>
                <p><strong>Directions:</strong> {{ round.directions }}</p>
              </div>
              <div class="progress-info">
                <p>
                  <strong>Your Progress:</strong> {{ (100 - round.percent_tasks_open).toFixed(1) }}%
                  ({{ round.total_open_tasks ?? 0 }} out of {{ round.total_tasks ?? 0 }})
                </p>
                <div class="actions">
                  <cdx-button
                    action="progressive"
                    weight="primary"
                    class="vote-button"
                    @click="goRoundVoting(round, 'vote')"
                    >Vote</cdx-button
                  >
                  <cdx-button action="progressive" @click="goRoundVoting(round, 'vote-edit')"
                    >Edit Previous Votes</cdx-button
                  >
                </div>
              </div>
            </div>
          </template>
        </cdx-card>
      </div>
    </div>
  </cdx-accordion>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { getVotingName } from '@/utils'

// Components
import { CdxCard, CdxAccordion, CdxButton } from '@wikimedia/codex'

// Icons
import ThumbsUpDown from 'vue-material-design-icons/ThumbsUpDown.vue'

defineProps({
  campaign: Object
})

const router = useRouter()

const goRoundVoting = (round, type) => {
  router.push({ name: type, params: { id: [round.id, round.canonical_url_name].join('-') } })
}
</script>

<style scoped>
.juror-campaign-accordion {
  border-bottom: none;
}

.juror-campaign-round-card {
  display: flex;
  flex-direction: column;
}

.round-header {
  display: flex;
  align-items: center;
}

.juror-campaign-round-icon {
  background-color: blue;
  height: 56px;
  padding: 10px;
  border-radius: 50%;
}

.round-info {
  margin-left: 24px;
}

.card-container {
  margin-left: 80px;
}

.information-card .cdx-card__text {
  width: 100% !important;
}

.supporting-info {
  display: flex;
}

.directions {
  flex: 6;
}

.progress-info {
  margin-left: auto;
  flex: 4;
  display: flex;
  flex-direction: column;
  align-items: end;
}

.actions {
  margin-top: 10px;
}

.vote-button {
  margin-right: 16px;
}
</style>
