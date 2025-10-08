<template>
  <div class="vote-ranking-screen" v-if="round.status === 'active' && images?.length > 0">
    <div class="vote-round-header">
      <div>
        <h2>{{ round.name }}</h2>
        <p class="vote-campaign-part">
          {{ $t('montage-vote-round-part-of-campaign', [round.campaign.name]) }}
        </p>
      </div>

      <div class="vote-grid-size-controls">
        <cdx-button :action="gridSize === 3 ? 'progressive' : ''" weight="quiet" @click="setGridSize(3)">
          <image-size-select-actual class="icon-small" />
          {{ $t('montage-vote-grid-size-large') }}
        </cdx-button>
        <cdx-button :action="gridSize === 2 ? 'progressive' : ''" weight="quiet" @click="setGridSize(2)">
          <image-size-select-large class="icon-small" />
          {{ $t('montage-vote-grid-size-medium') }}
        </cdx-button>
        <cdx-button :action="gridSize === 1 ? 'progressive' : ''" weight="quiet" @click="setGridSize(1)">
          <image-size-select-small class="icon-small" />
          {{ $t('montage-vote-grid-size-small') }}
        </cdx-button>
      </div>

      <cdx-button weight="quiet" action="progressive" @click="saveRanking">
        <content-save-outline class="icon-small" />
        {{ $t('montage-round-save') }}
      </cdx-button>
    </div>

    <div class="vote-image-grid" :class="'grid-size-' + gridSize">
      <draggable class="vote-gallery" v-model="images">
        <div v-for="(image, index) in images" :key="image.entry.id" class="vote-gallery-image link"
          :class="getImageSizeClass()">
          <div class="vote-gallery-expand-icon" @click="openImage(image)">
            <arrow-expand-all />
          </div>
          <div class="vote-gallery-image-container">
            <img :src="image.entry.url" />
          </div>
          <div class="vote-gallery-footer">
            <h3 class="vote-gallery-footer-name">
              <div>
                <strong>
                  {{ $t('montage-vote-ordinal-place', [getOrdinal(index + 1)]) }}
                </strong>
              </div>
              <span v-if="!round.config.show_filename">
                {{ $t('montage-vote-image') }} #{{ image.entry.id }}
              </span>
              <span v-else>
                {{ image.entry.name.split('_').join(' ') }}
              </span>
            </h3>
          </div>
        </div>
      </draggable>
    </div>
  </div>

  <div class="voting-completed" v-if="round.status === 'active' && !images?.length">
    <div>
      <h3>{{ $t('montage-vote-all-done') }}</h3>
      <p class="greyed">{{ $t('montage-vote-no-images') }}</p>
      <p class="greyed">{{ $t('montage-vote-no-images-warning') }}</p>
      <cdx-button class="edit-voting-btn" @click="editPreviousVotes">
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
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService'
import dialogService from '@/services/dialogService'

// Components
import { VueDraggableNext as draggable } from 'vue-draggable-next'
import { CdxButton } from '@wikimedia/codex'

// Icon
import ContentSaveOutline from 'vue-material-design-icons/ContentSaveOutline.vue'
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import ArrowExpandAll from 'vue-material-design-icons/ArrowExpandAll.vue'
import ImageReviewDialog from './ImageReviewDialog.vue'

const { t: $t } = useI18n()
const router = useRouter()

const props = defineProps({
  round: Object,
  tasks: Object
})

const roundLink = [props.round.id, props.round.canonical_url_name].join('-')

// State variables
const images = ref(null)
const stats = ref(null)
const gridSize = ref(1)

const setGridSize = (size) => {
  gridSize.value = size
}

const getOrdinal = (n) => {
  const ordinals = ['th', 'st', 'nd', 'rd']
  const value = n % 100
  return `${n}${ordinals[(value - 20) % 10] || ordinals[value] || ordinals[0]}`
}

const getImageSizeClass = () => {
  return `vote-gallery-image--size-${gridSize.value}`
}

const openImage = (image) => {
  dialogService().show({
    title: $t('montage-vote-image-review', [image.entry.id]),
    props: {
      image: image,
      onSave: (newValue) => image.review = newValue,
    },
    content: ImageReviewDialog,
    primaryAction: {
      label: 'Save',
      actionType: 'progressive'
    },
    defaultAction: {
      label: 'Cancel',
    },
    onDefault: () => console.log('Canceled'),
    maxWidth: "56rem"
  })
}

const saveRanking = () => {
  const ratings = images.value.map((image, index) => ({
    task_id: image.id,
    value: index,
    review: image.review || null
  }))

  jurorService
    .setRating(props.round.id, { ratings })
    .then(() => {
      router.go(0)
    })
    .catch(alertService.error)
}

const editPreviousVotes = () => {
  router.push({ name: 'vote-edit', params: { id: roundLink } })
}

watch(
  () => props.tasks,
  (tasks) => {
    console.log(tasks)
    images.value = tasks.tasks
    stats.value = tasks.stats
  }
)

watch(images, (img) => {
  console.log(img)
}
)
</script>

<style scoped>
.vote-ranking-screen {
  padding: 20px;
}

.vote-round-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vote-campaign-part {
  color: gray;
}

.vote-grid-size-controls {
  display: flex;
  gap: 10px;
}

.vote-image-grid {
  margin-top: 8px;
}

.vote-gallery {
  display: flex;
  flex-wrap: wrap;
}

.vote-gallery-image {
  display: inline-block;
  position: relative;
  background: #ccc;
  width: calc((100% - 100px) / 5);
  height: 15vw;
  margin: 10px 10px 60px;
  vertical-align: top;
  cursor: grab;
}

.vote-gallery-image--size-2 {
  width: calc((100% - 100px) / 3);
  height: 28vw;
}

.vote-gallery-image--size-3 {
  width: calc((100% - 100px) / 2);
  height: 43vw;
}

.vote-gallery-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.vote-gallery-image-container img {
  width: 100%;
  height: auto;
  object-fit: cover;
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

.vote-gallery-footer {
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

.vote-gallery-footer-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vote-gallery-footer:hover {
  height: 50%;
  background: #e0e0e0;
}

.vote-gallery-footer-name:hover {
  white-space: normal;
  font-size: 16px;
}

.icon-small {
  font-size: 6px;
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
