<template>
    <vote-yes-no v-if="round && round.vote_method === 'yesno'" :round="round" :tasks="tasks" />
    <vote-rating v-else-if="round && round.vote_method === 'rating'" :round="round" :tasks="tasks" />
    <vote-ranking v-else-if="round && round.vote_method === 'ranking'" :round="round" :tasks="tasks" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import jurorService from '@/services/jurorService'
import VoteYesNo from '@/components/Vote/VoteYesNo.vue'
import VoteRating from '@/components/Vote/VoteRating.vue'
import VoteRanking from '@/components/Vote/VoteRanking.vue'

const route = useRoute()
const voteId = route.params.id

const round = ref(null)
const tasks = ref(null)

onMounted(() => {
    jurorService.getRound(voteId).then((response) => {
        round.value = response.data
    })
    jurorService.getRoundTasks(voteId).then((response) => {
        tasks.value = response.data
    })
})

</script>