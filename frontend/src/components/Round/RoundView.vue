<template>
  <div class="round-info-container">
    <div style="display: flex">
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
      <div style="margin-left: 24px; display: flex; width: 100%; align-items: center">
        <div>
          <h2>{{ round.name }}</h2>
          <p>
            {{
              round.vote_method === 'yesno'
                ? $t('montage-round-yesno')
                : round.vote_method === 'rating'
                  ? $t('montage-round-rating')
                  : $t('montage-round-ranking')
            }}
            . {{ round.status }}
          </p>
        </div>
        <div style="margin-left: auto">
          <cdx-button @click="toggleEditing()">
            <cog style="font-size: 6px" v-if="!isRoundEditing" />
            <close style="font-size: 6px" v-else />
            {{ isRoundEditing ? $t('montage-btn-cancel') : $t('montage-round-edit') }}
          </cdx-button>
        </div>
      </div>
    </div>
    <div style="margin-left: 80px">
      <cdx-card style="margin-top: 24px" class="information-card">
        <template #description>
          <round-info :round="round" v-if="!isRoundEditing" />
          <round-edit :round="round" v-else v-model:isRoundEditing="isRoundEditing" />
        </template>
      </cdx-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// Components
import { CdxCard, CdxButton } from '@wikimedia/codex'

import RoundInfo from './RoundInfo.vue'
import RoundEdit from './RoundEdit.vue'

// Icons
import ThumbsUpDown from 'vue-material-design-icons/ThumbsUpDown.vue'
import StarOutline from 'vue-material-design-icons/StarOutline.vue'
import Sort from 'vue-material-design-icons/Sort.vue'
import Cog from 'vue-material-design-icons/Cog.vue'
import Close from 'vue-material-design-icons/Close.vue'

const props = defineProps({
  round: Object
})

const isRoundEditing = ref(false)

const toggleEditing = () => {
  isRoundEditing.value = !isRoundEditing.value
}
</script>

<style scoped>
.round {
  display: flex;
  flex-direction: column;
}

.juror-campaign-round-icon {
  background-color: blue;
  height: 56px;
  padding: 10px;
  border-radius: 50%;
}

.information-card .cdx-card__text {
  width: 100% !important;
}

.info-accordion {
  margin-top: 16px;
}
</style>
