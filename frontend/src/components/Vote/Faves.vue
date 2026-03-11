<template>
  <!-- Loading state -->
  <div v-if="!round || !faves" class="loading-container">
    <clip-loader class="loading-bar" size="85px" />
  </div>

  <!-- Main faves screen -->
  <div v-else-if="round.campaign.status === 'active' && faves.length" class="edit-vote-screen" @scroll="handleScroll"
    ref="favesContainer">
    <div class="round-header">
      <div>
        <h2 v-html="$t('montage-faves-for', [`<a href='#/vote/${round.link}'>${round.name}</a>`])"></h2>
        <p style="color: gray">
          {{ $t('montage-vote-round-part-of-campaign', [round.campaign.name]) }}
        </p>
      </div>
      <div class="grid-size-controls" style="margin-left: 60px">
        <p style="font-size: 16px; color: gray; margin-left: 11px">
          {{ $t('montage-vote-gallery-size') }}
        </p>
        <cdx-button :action="gridSize === 3 ? 'progressive' : ''" weight="quiet" @click="setGridSize(3)">
          <image-size-select-actual style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-large') }}
        </cdx-button>
        <cdx-button :action="gridSize === 2 ? 'progressive' : ''" weight="quiet" @click="setGridSize(2)">
          <image-size-select-large style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-medium') }}
        </cdx-button>
        <cdx-button :action="gridSize === 1 ? 'progressive' : ''" weight="quiet" @click="setGridSize(1)">
          <image-size-select-small style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-small') }}
        </cdx-button>
      </div>
    </div>

    <div class="image-grid" :class="'grid-size-' + gridSize">
      <div v-for="image in faves" :key="image.id" class="gallery-image link" :class="getImageSizeClass()">
        <div class="gallery-image-fav">
          <heart style="color: red" />
        </div>
        <div class="gallery-image-container">
          <CommonsImage :image="image" :width="640" />
        </div>
        <div style="font-size: 14px; color: gray">
          <p>{{ $t('montage-voted-time', [dayjs.utc(image.fave_date).fromNow()]) }}</p>
          <p>{{ dayjs.utc(image.fave_date).format('D MMM YYYY [at] H:mm [UTC]') }}</p>
        </div>
        <div class="image-grid-vote-action">
          <cdx-button weight="quiet" action="destructive" @click="removeFave(image)">
            <heart-off class="icon-small" /> {{ $t('montage-vote-remove-favorites') }}
          </cdx-button>
        </div>
      </div>
    </div>
  </div>

  <!-- No faves yet -->
  <div v-else-if="round && faves && !faves.length" class="no-faves">
    <div>
      <heart style="font-size: 48px; color: #ccc" />
      <h3>{{ $t('montage-no-faves-yet') }}</h3>
      <p class="greyed">{{ $t('montage-no-faves-this-round') }}</p>
      <cdx-button action="progressive" @click="goVoting" style="margin-top: 10px">
        {{ $t('montage-vote') }}
      </cdx-button>
    </div>
  </div>

  <!-- Round not active -->
  <div v-else>
    <h3>{{ $t('montage-vote-round-inactive') }}</h3>
    <p class="greyed">{{ $t('montage-vote-contact-organizer') }}</p>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import _ from 'lodash'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import 'dayjs/locale/en'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'
import CommonsImage from '@/components/CommonsImage.vue'

// Components
import { CdxButton } from '@wikimedia/codex'

// Icons
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import Heart from 'vue-material-design-icons/Heart.vue'
import HeartOff from 'vue-material-design-icons/HeartOff.vue'

// Hooks
const { t: $t } = useI18n()
const router = useRouter()
const route = useRoute()
const { locale } = useI18n()

const voteId = route.params.id.split('-')[0]
dayjs.extend(relativeTime)
dayjs.extend(utc)
dayjs.locale(locale.value)

const round = ref(null)
const faves = ref(null)
const loadingMore = ref(false)
const favesContainer = ref(null)
const gridSize = ref(1)

const setGridSize = (size) => {
  gridSize.value = size
}

const getImageSizeClass = () => {
  return `gallery-image--size-${gridSize.value}`
}

const goVoting = () => {
  router.push({ name: 'vote', params: { id: route.params.id } })
}

function getRoundDetails(id) {
  jurorService
    .getRound(id)
    .then((response) => {
      const r = response.data
      round.value = r
      round.value.link = [r.id, r.canonical_url_name].join('-')
      return getFaves()
    })
    .then((data) => {
      if (data) faves.value = data
    })
    .catch(alertService.error)
}

function getFaves(offset = 0) {
  return jurorService
    .getFaves(round.value.campaign.id, offset)
    .then((response) => {
      return response.data
    })
    .catch(alertService.error)
}

const removeFave = (image) => {
  jurorService
    .unfaveImage(round.value.id, image.id)
    .then(() => {
      faves.value = faves.value.filter((f) => f.id !== image.id)
      alertService.success($t('montage-vote-removed-favorites'), 500)
    })
    .catch(alertService.error)
}

const loadMore = () => {
  if (loadingMore.value) return
  loadingMore.value = true
  return getFaves(faves.value.length)
    .then((newFaves) => {
      if (newFaves?.length) {
        faves.value.push(...newFaves)
      }
    })
    .finally(() => {
      loadingMore.value = false
    })
}

const handleScroll = _.throttle(() => {
  if (!favesContainer.value) return
  if (loadingMore.value) return

  const container = favesContainer.value
  const { scrollTop, scrollHeight, clientHeight } = container
  const triggerPoint = scrollHeight - clientHeight

  if (scrollTop >= triggerPoint) {
    loadMore()
  }
}, 500)

const handleResize = () => {
  const width = window.innerWidth
  if (width < 800) {
    setGridSize(3)
  } else if (width >= 800 && width <= 1150) {
    setGridSize(2)
  } else {
    setGridSize(1)
  }
}

watch(locale, (newLocale) => {
  dayjs.locale(newLocale)
})

onMounted(() => {
  getRoundDetails(voteId)
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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

.edit-vote-screen {
  padding: 20px;
  overflow-y: auto;
  max-height: 80vh;
}

.round-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-grid {
  margin-top: 8px;
}

.image-grid-vote-action {
  margin-bottom: 40px;
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.gallery-image {
  display: inline-block;
  position: relative;
  background: #ccc;
  width: calc((100% - 100px) / 5);
  height: 15vw;
  margin: 10px 10px 100px;
  vertical-align: top;
}

.gallery-image-fav {
  position: absolute;
  right: 0;
  color: red;
  z-index: 1;
}

.gallery-image--size-2 {
  width: calc((100% - 100px) / 3);
  height: 28vw;
}

.gallery-image--size-3 {
  width: calc((100% - 100px) / 2);
  height: 43vw;
}

.gallery-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.gallery-image-container img {
  width: 100%;
  height: auto;
  object-fit: cover;
}

.no-faves {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 156.5px);
  text-align: center;
}
</style>