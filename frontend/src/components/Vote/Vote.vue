<template>
  <div v-if="!tasks || !round" class="loading-container">
    <clip-loader class="loading-bar" size="85px" />
  </div>

  <div v-else class="vote-wrapper">
    <div v-if="round.directions" class="directions-container">
      <button @click="showDirections = !showDirections" class="btn-directions">
        {{ showDirections ? 'Hide Directions' : 'View Round Directions' }}
      </button>
      
      <div v-if="showDirections" class="directions-modal">
        <div class="directions-content">
          <h3>Round Directions</h3>
          <p>{{ round.directions }}</p>
        </div>
      </div>
    </div>

    <vote-yes-no v-if="round.vote_method === 'yesno'" :round="round" :tasks="tasks" />
    <vote-rating v-else-if="round.vote_method === 'rating'" :round="round" :tasks="tasks" />
    <vote-ranking v-else-if="round.vote_method === 'ranking'" :round="round" :tasks="tasks" />
  </div>
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
const showDirections = ref(false) // Added this for the toggle

onMounted(() => {
  jurorService
    .getRound(voteId)
    .then((response) => {
      round.value = response.data
    })
    .catch(alertService.error)
  jurorService
    .getRoundTasks(voteId)
    .then((response) => {
      tasks.value = response.data
    })
    .catch(alertService.error)
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

.directions-container {
  margin-bottom: 20px;
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.btn-directions {
  background-color: #3676ab;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.directions-modal {
  background: #f9f9f9;
  border: 1px solid #ccc;
  padding: 15px;
  margin-top: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
</style>
