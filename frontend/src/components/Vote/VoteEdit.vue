<template>
  <!-- Loading state -->
  <div v-if="!round || !votes" class="loading-container">
    <clip-loader class="loading-bar" size="85px" />
  </div>

  <!-- Main edit screen -->
  <div
    v-else-if="round.campaign.status === 'active' && votes.length"
    class="edit-vote-screen"
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
          <CommonsImage :image="image" :width="640" loading="lazy" />
        </div>
        <div style="font-size: 14px; color: gray">
          <p>{{ $t('montage-voted-time', [dayjs.utc(image.date).fromNow()]) }}</p>
          <p>{{ dayjs.utc(image.date).format('D MMM YYYY [at] H:mm [UTC]') }}</p>
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
            <cdx-button weight="quiet" action="default" @click="setRate(image, rate)">
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
            <CommonsImage :image="image" :width="640" loading="lazy" />
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
            <p>{{ $t('montage-voted-time', [dayjs.utc(image.date).fromNow()]) }}</p>
            <p>{{ dayjs.utc(image.date).format('D MMM YYYY [at] H:mm [UTC]') }}</p>
          </div>
        </div>
      </draggable>
    </div>
    <div v-if="!isVoting('ranking')" class="pagination-bar">
      <cdx-button
        action="default"
        weight="quiet"
        :disabled="currentPage <= 1 || loadingMore"
        @click="goPrevPage"
      >
        <chevron-left class="pagination-icon" />
        {{ $t('montage-pagination-previous') }}
      </cdx-button>
      <span class="pagination-page">{{ $t('montage-pagination-page', [currentPage]) }}</span>
      <cdx-button
        action="default"
        weight="quiet"
        :disabled="!hasNextPage || loadingMore"
        @click="goNextPage"
      >
        {{ $t('montage-pagination-next') }}
        <chevron-right class="pagination-icon" />
      </cdx-button>
    </div>
  </div>

  <!-- No votes yet -->
  <div v-else-if="round.campaign.status === 'active' && !votes.length">
    <div>
      <h3>{{ $t('montage-no-votes-yet') }}</h3>
      <p class="greyed">{{ $t('montage-no-votes-this-round') }}</p>
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
import 'dayjs/locale/hi'
import relativeTime from 'dayjs/plugin/relativeTime'
import utc from 'dayjs/plugin/utc'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'
import dialogService from '@/services/dialogService'
import CommonsImage from '@/components/CommonsImage.vue'

// Components
import { CdxButton, CdxSelect } from '@wikimedia/codex'
import { VueDraggableNext as draggable } from 'vue-draggable-next'
import ImageReviewDialog from './ImageReviewDialog.vue'

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
import ChevronLeft from 'vue-material-design-icons/ChevronLeft.vue'
import ChevronRight from 'vue-material-design-icons/ChevronRight.vue'

// Hooks
const { t: $t } = useI18n()
const router = useRouter()
const route = useRoute()
const { locale } = useI18n()

const voteId = route.params.id.split('-')[0]
dayjs.extend(relativeTime)
dayjs.extend(utc)
dayjs.locale(locale.value)

const pageSize = 50

const round = ref(null)
const votes = ref(null)
const loadingMore = ref(false)
const editVoteContainer = ref(null)
const currentPage = ref(1)
const hasNextPage = ref(false)

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
    title: $t('montage-vote-image-review', [image.entry.id]),
    props: {
      image: image,
      onSave: (newValue) => (image.review = newValue)
    },
    content: ImageReviewDialog,
    primaryAction: {
      label: 'Save',
      actionType: 'progressive'
    },
    defaultAction: {
      label: 'Cancel'
    },
    onDefault: () => console.log('Canceled'),
    maxWidth: '56rem'
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
  return jurorService
    .getRound(id)
    .then((response) => {
      const r = response.data
      round.value = r
      round.value.link = [r.id, r.canonical_url_name].join('-')
    })
    .catch(alertService.error)
}

const VOTES_CHUNK_SIZE = 10000

function fetchAllPastVotes(id, orderBy, sort) {
  let offset = 0
  const accumulate = (acc) => {
    return jurorService
      .getPastVotes(id, offset, orderBy, sort, 0)
      .then((response) => {
        const chunk = response.data.map((vote) => ({
          ...vote,
          value: vote.value * 4 + 1
        }))
        const next = acc.concat(chunk)
        offset += chunk.length
        if (chunk.length >= VOTES_CHUNK_SIZE) {
          return accumulate(next)
        }
        return next
      })
  }
  return accumulate([])
}

function loadPage(roundId, page) {
  loadingMore.value = true
  const offset = (page - 1) * pageSize
  return jurorService
    .getPastVotes(roundId, offset, sort.value.order_by, sort.value.sort, pageSize)
    .then((response) => {
      votes.value = response.data.map((vote) => ({
        ...vote,
        value: vote.value * 4 + 1
      }))
      hasNextPage.value = response.data.length >= pageSize
    })
    .catch(alertService.error)
    .finally(() => {
      loadingMore.value = false
    })
}

function getPastVotes(id) {
  loadingMore.value = true
  if (round.value && round.value.vote_method === 'ranking') {
    fetchAllPastVotes(id, sort.value.order_by, sort.value.sort)
      .then((data) => {
        votes.value = data
      })
      .catch(alertService.error)
      .finally(() => {
        loadingMore.value = false
      })
  } else {
    currentPage.value = 1
    loadPage(id, 1)
  }
}

const isVoting = (type) => {
  return round.value && round.value.vote_method === type
}

const goPrevPage = () => {
  if (currentPage.value <= 1 || loadingMore.value) return
  currentPage.value--
  loadPage(round.value.id, currentPage.value)
}

const goNextPage = () => {
  if (!hasNextPage.value || loadingMore.value) return
  currentPage.value++
  loadPage(round.value.id, currentPage.value)
}

const reorderList = () => {
  votes.value = []
  if (round.value && round.value.vote_method === 'ranking') {
    loadingMore.value = true
    fetchAllPastVotes(round.value.id, sort.value.order_by, sort.value.sort)
      .then((data) => {
        votes.value = data
      })
      .catch(alertService.error)
      .finally(() => {
        loadingMore.value = false
      })
  } else {
    currentPage.value = 1
    loadPage(round.value.id, 1)
  }
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
  getRoundDetails(voteId).then(() => getPastVotes(voteId))

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

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 24px;
  padding: 16px;
}

.pagination-page {
  font-size: 14px;
  color: #54595d;
}

.pagination-icon {
  font-size: 20px;
  vertical-align: middle;
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
