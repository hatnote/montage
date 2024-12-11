<template>
  <div
    class="edit-vote-screen"
    v-if="round?.campaign.status === 'active' && votes?.length"
    @scroll="handleScroll"
    ref="editVoteContainer"
  >
    <div class="round-header">
      <div>
        <h2
          v-html="$t('montage-vote-edit-for', [`<a href='#/vote/${round.link}'>${round.name}</a>`])"
        ></h2>
        <p style="color: gray">
          {{ $t('montage-vote-round-part-of-campaign', [round.campaign.name]) }}
        </p>
      </div>
      <div class="order-by" v-if="!isVoting('ranking')">
        <p style="font-size: 16px; color: gray">{{ $t('montage-vote-order-by') }}</p>
        <cdx-select
          v-model:selected="sort.order_by"
          :menu-items="menuItemsOrder"
          @update:selected="reorderList"
        />
        <cdx-select
          v-model:selected="sort.sort"
          :menu-items="menuItemsSort"
          @update:selected="reorderList"
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
          <image-size-select-actual style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-large') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 2 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(2)"
        >
          <image-size-select-large style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-medium') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 1 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(1)"
        >
          <image-size-select-small style="font-size: 6px" />
          {{ $t('montage-vote-grid-size-small') }}
        </cdx-button>
      </div>

      <cdx-button
        weight="quiet"
        action="progressive"
        v-if="!isVoting('ranking')"
        :disabled="!edits.length"
        @click="save"
      >
        <content-save-outline style="font-size: 6px" /> {{ $t('montage-round-save') }} ({{
          edits.length
        }})
      </cdx-button>

      <cdx-button
        weight="quiet"
        action="progressive"
        v-if="isVoting('ranking')"
        @click="saveRanking"
      >
        <content-save-outline style="font-size: 6px" /> {{ $t('montage-round-save') }}
      </cdx-button>
    </div>
    <div class="image-grid" :class="'grid-size-' + gridSize" v-if="!isVoting('ranking')">
      <div
        v-for="image in votes"
        :key="image.id"
        class="gallery-image link"
        :class="getImageSizeClass()"
      >
        <div class="gallery-image-fav" v-if="image.is_fave">
          <heart />
        </div>
        <div class="gallery-image-container">
          <img :src="getImageName(image)" />
        </div>
        <div style="font-size: 14px; color: gray">
          <p>{{ $t('montage-voted-time', [dayjs(image.date).fromNow()]) }}</p>
          <p>{{ dayjs(image.date).utc().format('D MMM YYYY [at] H:mm [UTC]') }}</p>
        </div>
        <!-- Yes/No voting edit -->
        <div class="image-grid-vote-action" v-if="isVoting('yesno')">
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
        <!-- Rating vote editing -->
        <div class="image-grid-vote-action" v-if="isVoting('rating')">
          <span v-for="rate in [1, 2, 3, 4, 5]" :key="rate">
            <cdx-button weight="quiet" @click="setRate(image, rate)">
              <star :style="{ color: rate <= image.value ? '#3cb371' : '' }" />
            </cdx-button>
          </span>
        </div>
      </div>
    </div>
    <!-- Ranking vote editing -->
    <div class="image-grid" :class="'grid-size-' + gridSize" v-if="isVoting('ranking')">
      <draggable class="gallery" v-model="votes">
        <div
          v-for="(image, index) in votes"
          :key="image.id"
          class="gallery-image link gallery-image-ranking"
          :class="getImageSizeClass()"
        >
          <div class="vote-gallery-expand-icon" @click="openImage(image)">
            <arrow-expand-all />
          </div>
          <div class="gallery-image-ranking-container">
            <img :src="getImageName(image)" />
          </div>
          <div class="gallery-footer">
            <h3 class="gallery-footer-name">
              <div>
                <strong>
                  {{ $t('montage-vote-ordinal-place', [getOrdinal(index + 1)]) }}
                </strong>
              </div>
            </h3>
          </div>
          <div style="font-size: 14px; color: gray; margin-top: 8px">
            <p>{{ $t('montage-voted-time', [dayjs(image.date).fromNow()]) }}</p>
            <p>{{ dayjs(image.date).utc().format('D MMM YYYY [at] H:mm [UTC]') }}</p>
          </div>
        </div>
      </draggable>
    </div>
  </div>
  <div v-if="round?.campaign.status === 'active' && !votes?.length">
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
import { onMounted, onUnmounted, ref, watch } from 'vue'
import _ from 'lodash'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import 'dayjs/locale/en'
import 'dayjs/locale/hi'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'
import dialogService from '@/services/dialogService'

// Components
import { CdxButton, CdxSelect } from '@wikimedia/codex'
import { VueDraggableNext as draggable } from 'vue-draggable-next'

// Icons
import ContentSaveOutline from 'vue-material-design-icons/ContentSaveOutline.vue'
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import ThumbUp from 'vue-material-design-icons/ThumbUp.vue'
import ThumbDown from 'vue-material-design-icons/ThumbDown.vue'
import Star from 'vue-material-design-icons/Star.vue'
import ArrowExpandAll from 'vue-material-design-icons/ArrowExpandAll.vue'
import Heart from 'vue-material-design-icons/Heart.vue'

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
const votes = ref(null)
const loadingMore = ref(false)
const editVoteContainer = ref(null)

const edits = ref([])
const sort = ref({
  order_by: 'date',
  sort: 'desc'
})

const gridSize = ref(1)

const setGridSize = (size) => {
  gridSize.value = size
}

const getImageSizeClass = () => {
  return `gallery-image--size-${gridSize.value}`
}

const getOrdinal = (n) => {
  const ordinals = ['th', 'st', 'nd', 'rd']
  const value = n % 100
  return `${n}${ordinals[(value - 20) % 10] || ordinals[value] || ordinals[0]}`
}

const openImage = (image) => {
  dialogService().show({
    title: $t('montage-vote-image-review'),
    content: "<img src='" + image.entry.url + "' style='max-width: 100%; max-height: 100%;' />"
  })
}

const menuItemsOrder = [
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
  if (loadingMore.value) return

  loadingMore.value = true
  return jurorService
    .getPastVotes(round.value.id, votes.value.length, sort.value.order_by, sort.value.sort)
    .then((response) => {
      const newVotes = response.data.map((vote) => ({
        ...vote,
        value: vote.value * 4 + 1
      }))

      if (newVotes.length) {
        if (votes.value.length && newVotes[0].id === votes.value[0].id) {
          // this is ranking round
          return false
        }
        votes.value.push(...newVotes)
      }

      return true
    })
    .finally(() => {
      loadingMore.value = false
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

const handleScroll = _.throttle(() => {
  if (!editVoteContainer.value) return
  if (loadingMore.value) return

  let distanceFactor = 1
  const container = editVoteContainer.value
  const { scrollTop, scrollHeight, clientHeight } = container

  const triggerPoint = scrollHeight - clientHeight * distanceFactor

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
  getPastVotes(voteId)

  if (editVoteContainer.value) {
    editVoteContainer.value.addEventListener('scroll', handleScroll)
  }

  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (editVoteContainer.value) {
    editVoteContainer.value.removeEventListener('scroll', handleScroll)
  }

  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
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

.gallery {
  display: flex;
  flex-wrap: wrap;
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
}
.gallery-image-ranking {
  cursor: grab;
}

.vote-gallery-expand-icon {
  cursor: pointer;
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

.gallery-image-ranking-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.gallery-image-ranking-container img {
  width: 100%;
  height: auto;
  object-fit: cover;
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

.gallery-footer {
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

.gallery-footer-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gallery-footer:hover {
  height: 50%;
  background: #e0e0e0;
}

.gallery-footer-name:hover {
  white-space: normal;
  font-size: 16px;
}
</style>
