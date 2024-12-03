<template>
  <div class="ranking-screen" v-if="round?.campaign.status === 'active' && votes.length">
    <div class="round-header">
      <div>
        <h2>{{ round.name }}</h2>
        <p style="color: gray">
          {{ $t('montage-vote-round-part-of-campaign', [round.campaign.name]) }}
        </p>
      </div>
      <div class="order-by">
        <p style="font-size: 16px; color: gray">{{ $t('montage-vote-order-by') }}</p>
        <cdx-select v-model:selected="sort.order_by" :menu-items="menuItems" />
        <cdx-select
          v-model:selected="sort.sort"
          :menu-items="menuItemsSort"
          style="width: 100px !important"
        />
      </div>
      <div class="grid-size-controls" style="margin-left: 60px">
        <p style="font-size: 16px; color: gray; margin-left: 11px">
          {{ $t('montage-vote-gallery-size') }}
        </p>
        <cdx-button
          :action="gridSize === 3 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(3)"
        >
          <image-size-select-actual style="font-size: 6px" /> {{ $t('montage-vote-grid-size-large') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 2 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(2)"
        >
          <image-size-select-large style="font-size: 6px" /> {{ $t('montage-vote-grid-size-medium') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 1 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(1)"
        >
          <image-size-select-small style="font-size: 6px" /> {{ $t('montage-vote-grid-size-small') }}
        </cdx-button>
      </div>

      <cdx-button weight="quiet" action="progressive" @click="save">
        <content-save-outline style="font-size: 6px" /> {{ $t('montage-round-save') }}
      </cdx-button>
    </div>

    <div class="image-grid" :class="'grid-size-' + gridSize">
      <div
        v-for="image in votes"
        :key="image.id"
        class="gallery__image link"
        :class="getImageSizeClass()"
      >
        <div class="gallery__image-container">
          <img :src="getImageName(image)" />
        </div>
        <div style="font-size: 14px; color: gray">
          <p>{{ $t('montage-voted-time', ['a day']) }}</p>
          <p>{{ image.timestamp }}</p>
        </div>
        <div style="margin-bottom: 40px; display: flex; justify-content: center; margin-top: 8px">
          <cdx-button
            :action="image.value === 5 ? 'progressive' : ''"
            weight="quiet"
            @click="setRate(image, 5)"
          >
            <thumb-up class="icon-small" /> {{ $t('montage-vote-accept') }}
          </cdx-button>
          <cdx-button
            :action="image.value === 1 ? 'progressive' : ''"
            weight="quiet"
            @click="setRate(image, 1)"
          >
            <thumb-down class="icon-small" /> {{ $t('montage-vote-decline') }}
          </cdx-button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="round?.campaign.status === 'active' && !votes.length">
    <div>
      <h3>{{ $t('montage-no-votes-yet') }}</h3>
      <p class="greyed">{{ $t('montage-no-votes-this-round') }}</p>
    </div>
  </div>
  <div v-if="round?.campaign.status !== 'active'">
    <h3>{{ $t('montage-vote-round-inactive') }}</h3>
    <p class="greyed">{{ $t('montage-vote-contact-organizer') }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import _ from 'lodash'
import { useRouter, useRoute } from 'vue-router'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'

// Components
import { CdxButton, CdxSelect } from '@wikimedia/codex'

// Icons
import ContentSaveOutline from 'vue-material-design-icons/ContentSaveOutline.vue'
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import ThumbUp from 'vue-material-design-icons/ThumbUp.vue'
import ThumbDown from 'vue-material-design-icons/ThumbDown.vue'

// Hooks
const router = useRouter()
const route = useRoute()

const voteId = route.params.id.split('-')[0]

getRoundDetails(voteId)
getPastVotes(voteId)

const round = ref(null)
const votes = ref(null)

const edits = ref([])
const showSidebar = ref(true)
const size = ref(1)
const sort = ref({
  order_by: 'date',
  sort: 'desc'
})

const gridSize = ref(1)

const setGridSize = (size) => {
  gridSize.value = size
}

const getImageSizeClass = () => {
  return `gallery__image--size-${gridSize.value}`
}

const menuItems = [
  { label: 'vote date', value: 'date' },
  { label: 'score', value: 'value' }
]

const menuItemsSort = [
  { label: 'accending', value: 'asc' },
  { label: 'descending', value: 'desc' }
]

function getRoundDetails(id) {
  jurorService
    .getRound(id)
    .then((response) => {
      const r = response.data
      round.value = r
      round.value.link = [r.id, r.canonical_url_name].join('-')
    })
    .catch(alertService.error)
}

function getPastVotes(id) {
  jurorService
    .getPastVotes(id)
    .then((response) => {
      votes.value = response.data.map((vote) => ({
        ...vote,
        value: vote.value * 4 + 1
      }))
    })
    .catch(alertService.error)
}

const getImageName = (image) => {
  if (!image) {
    return null
  }
  return [
    '//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/',
    encodeURIComponent(image.entry.name),
    '&width=1280'
  ].join('')
}

const isVoting = (type) => {
  return round.value && round.value.vote_method === type
}

const encodeName = (image) => {
  return encodeURIComponent(image.entry.name)
}

const openURL = (url) => {
  window.open(url, '_blank')
}

const loadMore = () => {
  return jurorService
    .getPastVotes(round.value.id, votes.value.length, sort.value.order_by, sort.value.sort)
    .then((response) => {
      const newVotes = response.data.map((vote) => ({
        ...vote,
        value: vote.value * 4 + 1
      }))

      if (newVotes.length) {
        if (votes.value.length && newVotes[0].id === votes.value[0].id) {
          return false
        }
        votes.value.push(...newVotes)
      }

      return true
    })
}

const reorderList = () => {
  votes.value = []
  loadMore()
}

const save = () => {
  saveRating()
    .then(() => {
      edits.value = []
      votes.value.forEach((image) => {
        delete image.edited
      })
      alertService.success('Rating saved')
    })
    .catch(alertService.error)
}

const saveRating = () => {
  return jurorService.setRating(round.value.id, {
    ratings: edits.value.map((element) => ({
      vote_id: element.id,
      value: (element.value - 1) / 4
    }))
  })
}

const saveRanking = () => {
  const ratings = votes.value.map((image) => ({
    task_id: image.id,
    value: votes.value.indexOf(image),
    review: image.review ? image.review : null
  }))

  jurorService
    .setRating(round.value.id, { ratings })
    .then(() => {
      router.go()
    })
    .catch(alertService.error)
}

const setRate = (image, rate) => {
  image.value = rate
  image.edited = true

  edits.value = _.reject(edits.value, { id: image.id })
  edits.value.push(image)
}
</script>

<style scoped>
.ranking-screen {
  padding: 20px;
}

.round-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-grid {
  margin-top: 8px;
}

.gallery {
  display: flex;
  flex-wrap: wrap;
}

.gallery__image {
  display: inline-block;
  position: relative;
  background: #ccc;
  width: calc((100% - 100px) / 5);
  height: 15vw;
  margin: 10px 10px 100px;
  vertical-align: top;
}

.gallery__image--size-2 {
  width: calc((100% - 100px) / 3);
  height: 28vw;
}

.gallery__image--size-3 {
  width: calc((100% - 100px) / 2);
  height: 43vw;
}

.gallery__image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
  /* Ensures no overflow */
}

.gallery__image-container img {
  width: 100%;
  height: auto;
  object-fit: cover;
}

.gallery__drag-icon {
  cursor: move;
  position: absolute;
  background: rgba(0, 0, 0, 0.18);
  top: 6px;
  left: 6px;
  padding: 4px;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
}

.gallery__drag-icon > span[role='img'] {
  display: flex;
}

.gallery__footer {
  position: absolute;
  width: 100%;
  height: 26px;
  bottom: 0;
  background: rgba(0, 0, 0, 0.18);
  color: white;
  text-align: center;
  padding-top: 5px;
  transition: height 0.4s;
}

.gallery__footer-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gallery__footer:hover {
  height: 50%;
  background: #e0e0e0;
}

.gallery__footer-name:hover {
  white-space: normal;
  font-size: 16px;
}
</style>
