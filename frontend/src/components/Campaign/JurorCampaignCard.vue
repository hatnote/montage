<template>
  <cdx-accordion open class="juror-campaign-accordion">
    <template #title>
      <h3>{{ campaign[0].campaign.name }}</h3>
    </template>
    <div v-for="(round, index) in campaign" :key="index" class="juror-campaign-round-card">
      <div class="round-header">
        <thumbs-up-down
          v-if="round.vote_method === 'yesno'"
          class="juror-campaign-round-icon"
          :size="36"
          fillColor="white"
        />
        <star-outline
          v-if="round.vote_method === 'rating'"
          class="juror-campaign-round-icon"
          :size="36"
          fillColor="white"
        />
        <sort
          v-if="round.vote_method === 'ranking'"
          class="juror-campaign-round-icon"
          :size="36"
          fillColor="white"
        />
        <div class="round-info">
          <p :class="{ strikethrough: round.status === 'cancelled' }">{{ round.name }}</p>
          <p>({{ $t(getVotingName(round.vote_method)) }} · {{ round.status }})</p>
        </div>
      </div>
      <div class="card-container">
        <cdx-card class="information-card">
          <template #supporting-text>
            <div class="supporting-info">
              <div class="directions">
                <p>
                  <strong>{{ $t('montage-voting-deadline') }}:</strong>
                  {{ round.deadline_date?.split('T')[0] }}
                </p>
                <p>
                  <strong>{{ $t('montage-directions') }}:</strong> {{ round.directions }}
                </p>
              </div>
              <div class="progress-info">
                <p>
                  <strong>{{ $t('montage-your-progress') }}:</strong>
                  {{ (100 - round.percent_tasks_open).toFixed(1) }}% ({{
                    $t('montage-progress-status', [
                      round.total_tasks - round.total_open_tasks ?? 0,
                      round.total_tasks ?? 0
                    ])
                  }})
                </p>
                <div class="actions">
                  <cdx-button
                    action="progressive"
                    weight="primary"
                    class="vote-button"
                    @click="goRoundVoting(round, 'vote')"
                    >{{ $t('montage-vote') }}</cdx-button
                  >
                  <cdx-button action="progressive" @click="goRoundVoting(round, 'vote-edit')">{{
                    $t('montage-edit-previous-vote')
                  }}</cdx-button>
                </div>
              </div>
            </div>
          </template>
        </cdx-card>
      </div>
    </div>
    <div class="faves-button-row">
      <cdx-button action="progressive" @click="goFaves()" style="font-size: 14px;">
        <span class="faves-button-content">
        {{ $t('montage-my-campaign-faves') }}<heart style=" font-size: 4px" />
        </span>
      </cdx-button>
    </div>
  </cdx-accordion>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { getVotingName } from '@/utils'
import Heart from 'vue-material-design-icons/Heart.vue'

// Components
import { CdxCard, CdxAccordion, CdxButton } from '@wikimedia/codex'

// Icons
import ThumbsUpDown from 'vue-material-design-icons/ThumbsUpDown.vue'
import StarOutline from 'vue-material-design-icons/StarOutline.vue'
import Sort from 'vue-material-design-icons/Sort.vue'

const props = defineProps({
  campaign: Object
})

const router = useRouter()

const goRoundVoting = (round, type) => {
  router.push({ name: type, params: { id: [round.id, round.canonical_url_name].join('-') } })
}

const goFaves = () => {
  const round = props.campaign[0]
  router.push({ name: 'faves', params: { id: [round.id, round.canonical_url_name].join('-') } })
}
</script>

<style scoped>
.juror-campaign-accordion {
  border-bottom: none;
  margin-bottom: 32px;
}

.juror-campaign-round-card {
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.faves-button-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.faves-button-content {
  display: flex;
  align-items: center;
  gap: 3px;
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

.strikethrough {
  text-decoration: line-through;
}
</style>
