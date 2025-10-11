<template>
  <div v-if="!tasks || !round" class="loading-container">
    <clip-loader class="loading-bar" size="85px" />
  </div>

  <template v-else>
    <vote-yes-no v-if="round.vote_method === 'yesno'" :round="round" :tasks="tasks" />
    <vote-rating v-else-if="round.vote_method === 'rating'" :round="round" :tasks="tasks" />
    <vote-ranking v-else-if="round.vote_method === 'ranking'" :round="round" :tasks="tasks" />
  </template>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import jurorService from '@/services/jurorService'
import VoteYesNo from '@/components/Vote/VoteYesNo.vue'
import VoteRating from '@/components/Vote/VoteRating.vue'
import VoteRanking from '@/components/Vote/VoteRanking.vue'
import alertService from '@/services/alertService'

const route = useRoute()
const voteId = route.params.id.split('-')[0]

const round = ref(null)
const tasks = ref(null)

onMounted(() => {
    jurorService.getRound(voteId).then((response) => {
        round.value = response.data
    }).catch(alertService.error)
    jurorService.getRoundTasks(voteId).then((response) => {
        tasks.value = response.data
    }).catch(alertService.error)
})
</script>

<style scoped>
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 156.5px);
  width: 100%;
}
</style>