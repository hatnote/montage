<template>
  <div
    class="vote-container"
    v-if="round.status === 'active' && images?.length > 0"
    @keydown="handleKeyDown"
    tabindex="0"
    ref="voteContainer"
  >
    <div class="vote-image-container" :class="showSidebar ? 'with-sidebar' : ''">
      <cdx-progress-bar class="vote-image-progress-bar" v-if="imageLoading" />
      <img
        :class="`vote-image ${imageLoading ? 'vote-image-hide' : ''}`"
        :src="getImageName(rating.current)"
        @load="handleImageLoad"
        @error="handleImageLoad"
      />
      <cdx-button
        @click="toggleSidebar"
        v-tooltip="$t(showSidebar ? 'montage-vote-hide-panel' : 'montage-vote-show-panel')"
        weight="quiet"
        class="sidebar-hide-btn"
      >
        <template v-if="showSidebar">
          <arrow-right-thick class="icon-small" />
        </template>
        <template v-else>
          <arrow-left-thick class="icon-small" />
        </template>
      </cdx-button>
    </div>
    <div class="vote-description-container" v-if="showSidebar">
      <div class="vote-file-name">
        <h1 v-if="!round.config.show_filename">
          {{ $t('montage-vote-image') }} #{{ rating.current.entry.id }}
        </h1>
        <h1 v-else>{{ rating.current.name.split('_').join(' ') }}</h1>
        <p class="greyed">{{ $t('montage-vote-image-remains', [stats.total_open_tasks]) }}</p>
      </div>
      <div class="vote-file-links">
        <a :href="rating.current.entry.url" target="_blank">
          <cdx-button weight="quiet">
            <image-icon class="icon-small" /> {{ $t('montage-vote-show-full-size') }}
          </cdx-button>
        </a>
        <a
          :href="'https://commons.wikimedia.org/wiki/File:' + rating.current.entry.name"
          target="_blank"
        >
          <cdx-button weight="quiet" class="vote-commons-button">
            <link-icon class="icon-small" /> {{ $t('montage-vote-commons-page') }}
          </cdx-button>
        </a>
      </div>
      <h3 class="vote-section-title">{{ $t('montage-vote') }}</h3>
      <div class="vote-controls">
        <div class="vote-controls-button">
          <span v-for="rate in [1, 2, 3, 4, 5]" :key="rate">
            <cdx-button weight="quiet" @click="setRate(rate)">
              <star />
            </cdx-button>
          </span>
        </div>
        <span class="greyed vote-controls-instruction">
          {{ $t('montage-vote-keyboard-instructions') }}<br />
          <span class="key">1</span>-<span class="key">5</span> –
          {{ $t('montage-vote-rating-instructions') }}<br />
          <span class="key">→</span> – {{ $t('montage-vote-skip') }}
        </span>
      </div>

      <h3 class="vote-section-title">{{ $t('montage-vote-actions') }}</h3>
      <div class="vote-actions">
        <div>
          <cdx-button weight="quiet" @click="handleFav()">
            <heart class="icon-small" />
            {{
              $t(
                rating.current.is_fave
                  ? 'montage-vote-remove-favorites'
                  : 'montage-vote-add-favorites'
              )
            }}
          </cdx-button>
        </div>
        <div>
          <cdx-button weight="quiet" @click="setRate()">
            <arrow-right class="icon-small" /> {{ $t('montage-vote-skip') }}
          </cdx-button>
          <cdx-button weight="quiet" @click="goPrevVoteEditing">
            <pencil class="icon-small" /> {{ $t('montage-edit-previous-vote') }}
          </cdx-button>
        </div>
      </div>

      <h3 class="vote-section-title">{{ $t('montage-vote-description') }}</h3>
      <div class="vote-details">
        <div class="vote-details-list">
          <div class="vote-details-list-item vote-details-2-line">
            <cloud-upload class="vote-details-icon" />
            <div class="vote-details-list-item-text">
              <h3>{{ formattedDateTime.date }}</h3>
              <p>{{ formattedDateTime.day }}, {{ formattedDateTime.time }}</p>
            </div>
          </div>
          <div class="vote-details-list-item vote-details-2-line">
            <div class="icon-container">
              <image-album class="vote-details-icon" />
            </div>
            <div class="vote-details-list-item-text">
              <h3>{{ rating.current.entry.resolution / 1000000 }} Mpix</h3>
              <p>
                {{ rating.current.entry.width + ' x ' + rating.current.entry.height }}
              </p>
            </div>
          </div>
          <div class="vote-details-list-item vote-details-2-line">
            <div class="icon-container">
              <history class="vote-details-icon" />
            </div>
            <div class="vote-details-list-item-text">
              <h3>
                {{ rating.current.history.length }}
                {{ $t('montage-vote-version')
                }}<span v-if="rating.current.history.length > 1">s</span>
              </h3>
              <p>
                {{
                  $t('montage-vote-last-version', [
                    formattedDate(rating.current.history[0].timestamp)
                  ])
                }}
              </p>
            </div>
            <cdx-button weight="quiet" @click="goPrevVoteEditing">
              <link-icon />
            </cdx-button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="voting-completed" v-if="round.status === 'active' && !images?.length">
    <div>
      <h3>{{ $t('montage-vote-all-done') }}</h3>
      <p class="greyed">
        {{ $t('montage-vote-no-images') }}
      </p>
      <cdx-button class="edit-voting-btn" @click="goPrevVoteEditing">
        <pencil class="icon-small" />
        {{ $t('montage-edit-previous-vote') }}
      </cdx-button>
    </div>
  </div>
  <div v-if="round.status !== 'active'">
    <h3>{{ $t('montage-vote-round-inactive') }}</h3>
    <p class="greyed">{{ $t('montage-vote-contact-organizer') }}</p>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import jurorService from '@/services/jurorService'
import { useRouter } from 'vue-router'
import alertService from '@/services/alertService'

import { CdxButton, CdxProgressBar } from '@wikimedia/codex'

import ImageIcon from 'vue-material-design-icons/Image.vue'
import LinkIcon from 'vue-material-design-icons/Link.vue'
import ArrowRight from 'vue-material-design-icons/ArrowRight.vue'
import Pencil from 'vue-material-design-icons/Pencil.vue'
import CloudUpload from 'vue-material-design-icons/CloudUpload.vue'
import ImageAlbum from 'vue-material-design-icons/ImageAlbum.vue'
import History from 'vue-material-design-icons/History.vue'
import ArrowRightThick from 'vue-material-design-icons/ArrowRightThick.vue'
import ArrowLeftThick from 'vue-material-design-icons/ArrowLeftThick.vue'
import Heart from 'vue-material-design-icons/Heart.vue'
import Star from 'vue-material-design-icons/Star.vue'

// Hooks
const { t: $t } = useI18n()
const router = useRouter()

// States variables
const counter = ref(0)
const skips = ref(0)
const imageLoading = ref(true)
const voteContainer = ref(null);
const showSidebar = ref(true)
const imageCache = new Map()

const props = defineProps({
  round: Object,
  tasks: Object
})

const roundLink = [props.round.id, props.round.canonical_url_name].join('-')

const images = ref(null)
const stats = ref(null)

const rating = ref({
  current: null,
  currentIndex: 0,
  next: null,
  rates: [1, 2, 3, 4, 5]
})

function toggleSidebar() {
  showSidebar.value = !showSidebar.value
}

function goPrevVoteEditing() {
  router.push({ name: 'vote-edit', params: { id: roundLink } })
}

function handleImageLoad() {
  imageLoading.value = false
}

const formattedDate = (timestamp) => {
  if (!timestamp) return ''

  const dateObj = new Date(timestamp)
  return new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(dateObj)
}

function getImageName(image) {
  if (!image) return null

  const entry = image.entry
  const url = [
    '//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/',
    encodeURIComponent(entry.name),
    '&width=1280'
  ].join('')

  return url
}

function getNextImage() {
  rating.value.currentIndex = (rating.value.currentIndex + 1) % images.value?.length
  rating.value.current = images.value[rating.value.currentIndex]
  rating.value.next = images.value[(rating.value.currentIndex + 1) % images.value?.length]
}

function getTasks() {
  return jurorService.getRoundTasks(props.round.id, skips.value).then((response) => {
    images.value = response.data.tasks
    rating.value.current = images.value?.[0]
    rating.value.currentIndex = 0
    rating.value.next = images.value?.[1] || null

    // Preload the next 10 images
    for (let i = 0; i < 10 && i < images.value.length; i++) {
      const img = new Image()
      img.src = getImageName(images.value[i])
      imageCache.set(images.value[i].entry.id, img)
    }
  })
}

function setRate(rate) {
  if (imageLoading.value) return

  if (rate) {
    const val = (rate - 1) / 4
    jurorService
      .setRating(props.round.id, { ratings: [{ task_id: rating.value.current.id, value: val }] })
      .then(() => {
        stats.value.total_open_tasks -= 1

        if (stats.value.total_open_tasks <= 10) {
          skips.value = 0
        }

        if (counter.value === 4 || !stats.value.total_open_tasks) {
          counter.value = 0
          getTasks()
        } else {
          counter.value += 1
          getNextImage()
        }
      })
  } else {
    skips.value += 1
    getNextImage()
  }
}

function handleFav() {
  if (rating.value.current.is_fave) {
    jurorService
      .unfaveImage(props.round.id, rating.value.current.entry.id)
      .then(() => {
        alertService.success($t('montage-vote-removed-favorites'), 500)

        rating.value.current.is_fave = false
      })
      .catch(alertService.error)
  } else {
    jurorService
      .faveImage(props.round.id, rating.value.current.entry.id)
      .then(() => {
        alertService.success($t('montage-vote-added-favorites'), 500)

        rating.value.current.is_fave = true
      })
      .catch(alertService.error)
  }
}

const handleKeyDown = (event) => {
  if (props.round.vote_method === 'rating') {
    const value = parseInt(event.key, 10)
    if (rating.value.rates.includes(value)) {
      setRate(value)
      alertService.success(`Voted ${value}/5`, 250)
    } else if (event.key === 'ArrowRight') {
      setRate()
    }
  }
}

const tooltipText = computed(() =>
  showSidebar.value ? $t('montage-vote-hide-panel') : $t('montage-vote-show-panel')
)

// Get the formatted date and time of current image
const formattedDateTime = computed(() => {
  const uploadDate = rating.value.current.entry.upload_date
  if (!uploadDate) return { date: '', day: '', time: '' }

  const dateObj = new Date(uploadDate)
  return {
    date: new Intl.DateTimeFormat('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    }).format(dateObj),
    day: new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(dateObj),
    time: new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: 'numeric' }).format(dateObj)
  }
})

// Changing value on states change
watch(
  () => rating.value.current,
  () => {
    imageLoading.value = true
  }
)

watch(
  () => props.tasks,
  (tasks) => {
    images.value = tasks.tasks
    stats.value = tasks.stats

    // Preload the images from tasks
    for (let i = 0; i < images.value.length; i++) {
      const index = (rating.value.currentIndex + i) % images.value.length
      const img = new Image()
      img.src = getImageName(images.value[index])
      imageCache.set(images.value[index].entry.id, img)
    }
  }
)

watch(images, (imgs) => {
  rating.value.current = imgs?.[0]
  rating.value.next = imgs?.[1] || null
})

onMounted(() => {
  if (voteContainer.value) {
    voteContainer.value.focus();
  }
});
</script>

<style scoped>
.vote-container {
  display: flex;
  justify-content: center;
  align-items: stretch;
  height: calc(100vh - 156.5px);
}

.vote-container:focus {
  outline: none;
}

.vote-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  background: #e6e6e6;
}

.vote-image-progress-bar {
  width: 100%;
  margin: 20px;
}

.vote-image-hide {
  display: none;
}

.with-sidebar {
  width: calc(100vw - 450px);
}

.vote-image-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.sidebar-hide-btn {
  position: absolute;
  top: 5px;
  right: 5px;
}

.vote-description-container {
  margin-left: 20px;
  width: 350px;
  overflow: auto;
}

.vote-file-name {
  display: flex;
  flex-direction: column;
  justify-content: start;
  align-items: stretch;
}

.vote-file-name h1 {
  margin: 0;
  height: 64px;
  overflow: hidden;
  font-size: 26px;
  display: block;
  margin-block-end: 0.67em;
  margin-inline-start: 0px;
  margin-inline-end: 0px;
  font-weight: bold;
}

.vote-file-links {
  display: flex;
  justify-content: start;
  align-items: center;
  margin-top: 20px;
}

.vote-commons-button {
  color: rgb(51, 102, 204);
}

.vote-section-title {
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.005em;
  display: block;
  margin-block-start: 1em;
  margin-block-end: 1em;
}

.vote-controls {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: stretch;
}

.vote-controls-button {
  display: flex;
  justify-content: center;
  align-items: center;
}

.vote-controls-instruction {
  margin-top: 16px;
}

.vote-actions {
  display: flex;
  flex-direction: column;
}

.vote-actions div {
  display: flex;
}

.vote-details-list {
  display: block;
  padding: 0;
  box-sizing: border-box;
}

.vote-details-list-item {
  display: flex;
  position: relative;
  padding: 0px 16px;
}

.vote-details-2-line {
  align-items: flex-start;
  min-height: 55px;
  height: 55px;
}

.vote-details-list-item-text {
  flex: 1 1 auto;
  margin: auto;
  text-overflow: ellipsis;
  overflow: hidden;
}

.vote-details-list-item-text h3 {
  color: rgba(0, 0, 0, 0.87);
  font-size: 16px;
  font-weight: 400;
  letter-spacing: 0.01em;
  margin: 0 0 0px 0;
  line-height: 1.2em;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.vote-details-list-item-text p {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.01em;
  margin: 0 0 0 0;
  line-height: 1.6em;
  color: rgba(0, 0, 0, 0.54);
}

.vote-details-icon {
  margin-right: 32px;
  width: 24px;
  margin-top: 16px;
  margin-bottom: 12px;
  box-sizing: content-box;
  cursor: default;
  font-size: 24px;
  height: 100%;
  display: inline-block;
  line-height: 1;
}

.voting-completed {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.edit-voting-btn {
  margin-top: 24px;
  width: 232px;
}
</style>
