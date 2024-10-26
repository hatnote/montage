<template>
  <div class="vote-view-container">
    <vote-yes-no v-if="voteId === '1'" />
    <vote-rating v-if="voteId === '2'" />
    <vote-ranking v-if="voteId === '3'" />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import VoteYesNo from '@/components/Vote/VoteYesNo.vue'
import VoteRating from '@/components/Vote/VoteRating.vue'
import VoteRanking from '@/components/Vote/VoteRanking.vue'

const route = useRoute()
const voteId = route.params.id
</script>

<style scoped>
.vote-view-container {
  padding: 20px;
}
</style>
