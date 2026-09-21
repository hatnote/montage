<template>
  <div class="zoomable-image-wrapper">
    <div class="zoom-normal-view">
      <CommonsImage
        :image="props.image"
        :width="baseWidth"
        :image-class="imageClass"
        @load="$emit('load', $event)"
        @error="$emit('error', $event)"
      />
      <cdx-button
        class="zoom-trigger-btn"
        weight="quiet"
        :aria-label="$t('montage-zoom-open')"
        @click="openZoom"
      >
        <magnify class="icon-small" />
        {{ $t('montage-zoom-open') }}
      </cdx-button>
    </div>

    <div
      v-if="zoomOpen"
      ref="overlayRef"
      class="zoom-overlay"
      role="dialog"
      :aria-label="$t('montage-zoom-dialog-label')"
      @wheel.prevent="handleWheel"
      @dblclick="toggleFitToActual"
      @mousedown="startDrag"
      @touchstart="handleTouchStart"
      @touchmove.prevent="handleTouchMove"
      @touchend="handleTouchEnd"
      @contextmenu.prevent
    >
      <img
        v-if="zoomImageUrl"
        :key="zoomImageUrl"
        :src="zoomImageUrl"
        :alt="image?.entry?.name || ''"
        class="zoom-image"
        :class="{ 'zoom-image--animating': isAnimating }"
        :style="imageTransform"
        draggable="false"
        @load="onZoomImageLoad"
      />

      <div v-if="isZoomLoading" class="zoom-loading">
        <cdx-progress-bar />
      </div>

      <div class="zoom-level-indicator" aria-live="polite">
        {{ $t('montage-zoom-level', [Math.round(scale * 100)]) }}
      </div>

      <div class="zoom-controls">
        <cdx-button
          weight="quiet"
          class="zoom-ctrl-btn"
          :aria-label="$t('montage-zoom-in')"
          @click.stop="zoomIn"
        >
          <plus />
        </cdx-button>
        <cdx-button
          weight="quiet"
          class="zoom-ctrl-btn"
          :aria-label="$t('montage-zoom-out')"
          @click.stop="zoomOut"
        >
          <minus />
        </cdx-button>
        <cdx-button
          weight="quiet"
          class="zoom-ctrl-btn"
          :aria-label="$t('montage-zoom-reset')"
          @click.stop="resetToActual"
        >
          <fullscreen />
        </cdx-button>
      </div>

      <cdx-button
        class="zoom-close-btn"
        weight="quiet"
        :aria-label="$t('montage-zoom-close', [escHint])"
        @click="closeZoom"
      >
        <close />
      </cdx-button>

      <transition name="zoom-hint-fade">
        <div v-if="showHint" class="zoom-hint">
          {{ $t('montage-zoom-hint') }}
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { CdxButton, CdxProgressBar } from '@wikimedia/codex'
import { useI18n } from 'vue-i18n'
import { getCommonsImageUrl } from '@/utils'
import CommonsImage from '@/components/CommonsImage.vue'

import Magnify from 'vue-material-design-icons/Magnify.vue'
import Plus from 'vue-material-design-icons/Plus.vue'
import Minus from 'vue-material-design-icons/Minus.vue'
import Close from 'vue-material-design-icons/Close.vue'
import Fullscreen from 'vue-material-design-icons/Fullscreen.vue'

const { t: $t } = useI18n()
const COMMONS_THUMB_WIDTHS = [320, 640, 800, 1024, 1280, 1600, 2000, 2500, 3000, 4000]

const MIN_SCALE = 0.1
const MAX_SCALE = 10
const ZOOM_STEP_FACTOR = 1.25

const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  baseWidth: {
    type: Number,
    default: 1280
  },
  imageClass: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['load', 'error', 'zoom-state-change'])

const overlayRef = ref(null)

const zoomOpen = ref(false)
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isAnimating = ref(false)
const isZoomLoading = ref(false)
const showHint = ref(false)
let hintTimeout = null

let dragging = false
let dragStartX = 0
let dragStartY = 0
let dragStartTranslateX = 0
let dragStartTranslateY = 0

let lastPinchDistance = 0
let touchDragStartX = 0
let touchDragStartY = 0
let touchDragStartTranslateX = 0
let touchDragStartTranslateY = 0
let singleTouchActive = false


const escHint = computed(() => {
  if (typeof navigator === 'undefined') return 'Esc'
  return /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⎋ Esc' : 'Esc'
})

const fitScale = computed(() => {
  if (!overlayRef.value || !props.image?.entry?.width) return 1

  const containerW = overlayRef.value.clientWidth * 0.92
  const containerH = overlayRef.value.clientHeight * 0.92
  const imgW = props.image.entry.width
  const imgH = props.image.entry.height

  if (!imgW || !imgH) return 1
  return Math.min(containerW / imgW, containerH / imgH, 1)
})

const imageTransform = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  transformOrigin: '0 0',
  willChange: 'transform'
}))

const requestedWidth = computed(() => {
  if (!zoomOpen.value || !props.image?.entry?.width) {
    return props.baseWidth
  }

  const displayedWidth = props.image.entry.width * scale.value

  for (const width of COMMONS_THUMB_WIDTHS) {
    if (width >= displayedWidth) return width
  }

  if (scale.value >= MAX_SCALE * 0.7) {
    return null // null signals "original" to getCommonsImageUrl
  }

  return COMMONS_THUMB_WIDTHS[COMMONS_THUMB_WIDTHS.length - 1]
})

const zoomImageUrl = computed(() => {
  if (!props.image) return ''
  return getCommonsImageUrl(props.image, requestedWidth.value)
})

function openZoom() {
  if (zoomOpen.value) return

  zoomOpen.value = true
  isZoomLoading.value = true

  scale.value = fitScale.value
  translateX.value = 0
  translateY.value = 0

  requestAnimationFrame(() => {
    centerImage()
  })

  showHint.value = true
  if (hintTimeout) clearTimeout(hintTimeout)
  hintTimeout = setTimeout(() => {
    showHint.value = false
  }, 2500)

  emit('zoom-state-change', true)
}

function closeZoom() {
  if (!zoomOpen.value) return

  zoomOpen.value = false
  isZoomLoading.value = false
  showHint.value = false
  if (hintTimeout) clearTimeout(hintTimeout)

  emit('zoom-state-change', false)
}

function toggleFitToActual() {
  if (!zoomOpen.value) return

  if (Math.abs(scale.value - 1) < 0.01) {
    // Currently at 100%, go to fit
    animateToScale(fitScale.value)
  } else {
    animateToScale(1)
  }
}

function resetToActual() {
  if (!zoomOpen.value) return
  animateToScale(1)
}

function zoomIn() {
  if (!zoomOpen.value) {
    openZoom()
    return
  }
  animateToScale(scale.value * ZOOM_STEP_FACTOR)
}

function zoomOut() {
  if (!zoomOpen.value) return
  const newScale = scale.value / ZOOM_STEP_FACTOR
  if (newScale < fitScale.value) {
    closeZoom()
  } else {
    animateToScale(newScale)
  }
}

function animateToScale(targetScale) {
  targetScale = clampScale(targetScale)
  isAnimating.value = true

  const startScale = scale.value
  const startTime = performance.now()
  const duration = 200 // ms

  const animate = (currentTime) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)

    scale.value = startScale + (targetScale - startScale) * eased
    clampTranslation()

    if (progress < 1) {
      requestAnimationFrame(animate)
    } else {
      scale.value = targetScale
      clampTranslation()
      isAnimating.value = false
    }
  }

  requestAnimationFrame(animate)
}

function onZoomImageLoad() {
  isZoomLoading.value = false
}

function handleWheel(e) {
  if (!zoomOpen.value || isAnimating.value) return

  const rect = overlayRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  const zoomFactor = e.deltaY < 0 ? 1.1 : 1 / 1.1
  const newScale = clampScale(scale.value * zoomFactor)
  const scaleRatio = newScale / scale.value
  translateX.value = mouseX - (mouseX - translateX.value) * scaleRatio
  translateY.value = mouseY - (mouseY - translateY.value) * scaleRatio

  scale.value = newScale
  clampTranslation()
}

function startDrag(e) {
  if (!zoomOpen.value || e.button !== 0) return
  if (e.target.closest('.zoom-controls, .zoom-close-btn')) return

  e.preventDefault()
  dragging = true
  dragStartX = e.clientX
  dragStartY = e.clientY
  dragStartTranslateX = translateX.value
  dragStartTranslateY = translateY.value

  const onMove = (e) => {
    if (!dragging) return
    translateX.value = dragStartTranslateX + (e.clientX - dragStartX)
    translateY.value = dragStartTranslateY + (e.clientY - dragStartY)
    clampTranslation()
  }

  const onUp = () => {
    dragging = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function handleTouchStart(e) {
  if (!zoomOpen.value) return
  if (e.target.closest('.zoom-controls, .zoom-close-btn')) return

  const touches = e.touches

  if (touches.length === 2) {
    // Pinch zoom
    singleTouchActive = false
    lastPinchDistance = getPinchDistance(touches)
  } else if (touches.length === 1) {
    // Single touch drag
    singleTouchActive = true
    touchDragStartX = touches[0].clientX
    touchDragStartY = touches[0].clientY
    touchDragStartTranslateX = translateX.value
    touchDragStartTranslateY = translateY.value
  }
}

function handleTouchMove(e) {
  if (!zoomOpen.value || isAnimating.value) return

  const touches = e.touches

  if (touches.length === 2 && lastPinchDistance > 0) {
    const newDistance = getPinchDistance(touches)
    const scaleRatio = newDistance / lastPinchDistance

    const rect = overlayRef.value.getBoundingClientRect()
    const centerX = (touches[0].clientX + touches[1].clientX) / 2 - rect.left
    const centerY = (touches[0].clientY + touches[1].clientY) / 2 - rect.top

    const newScale = clampScale(scale.value * scaleRatio)
    const actualRatio = newScale / scale.value

    translateX.value = centerX - (centerX - translateX.value) * actualRatio
    translateY.value = centerY - (centerY - translateY.value) * actualRatio
    scale.value = newScale
    lastPinchDistance = newDistance
    clampTranslation()
  } else if (touches.length === 1 && singleTouchActive) {
    translateX.value = touchDragStartTranslateX + (touches[0].clientX - touchDragStartX)
    translateY.value = touchDragStartTranslateY + (touches[0].clientY - touchDragStartY)
    clampTranslation()
  }
}

function handleTouchEnd(e) {
  singleTouchActive = false
  if (e.touches.length < 2) {
    lastPinchDistance = 0
  }
}

function getPinchDistance(touches) {
  const dx = touches[0].clientX - touches[1].clientX
  const dy = touches[0].clientY - touches[1].clientY
  return Math.sqrt(dx * dx + dy * dy)
}


function clampScale(s) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s))
}

function centerImage() {
  if (!overlayRef.value || !props.image?.entry) return

  const containerW = overlayRef.value.clientWidth
  const containerH = overlayRef.value.clientHeight
  const imgW = props.image.entry.width * scale.value
  const imgH = props.image.entry.height * scale.value

  translateX.value = (containerW - imgW) / 2
  translateY.value = (containerH - imgH) / 2
}

function clampTranslation() {
  if (!overlayRef.value || !props.image?.entry?.width) return

  const containerW = overlayRef.value.clientWidth
  const containerH = overlayRef.value.clientHeight
  const imgW = props.image.entry.width * scale.value
  const imgH = props.image.entry.height * scale.value

  if (imgW <= containerW) {
    translateX.value = (containerW - imgW) / 2
  } else {
    translateX.value = Math.min(0, Math.max(containerW - imgW, translateX.value))
  }

  if (imgH <= containerH) {
    translateY.value = (containerH - imgH) / 2
  } else {
    translateY.value = Math.min(0, Math.max(containerH - imgH, translateY.value))
  }
}

const onKeyDown = (e) => {
  if (!zoomOpen.value) return

  if (e.key === 'Escape') {
    e.preventDefault()
    e.stopPropagation()
    closeZoom()
    return
  }
  e.stopPropagation()
}

watch(
  () => props.image,
  (newImage) => {
    if (!newImage?.entry?.name && zoomOpen.value) {
      closeZoom()
    }
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  document.addEventListener('keydown', onKeyDown, { capture: true })
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeyDown, { capture: true })
  if (hintTimeout) clearTimeout(hintTimeout)
})
</script>

<style scoped>
.zoomable-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.zoom-normal-view {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.zoom-normal-view :deep(img) {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}

.zoom-trigger-btn {
  position: absolute;
  bottom: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.7);
  color: #000;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 13px;
  z-index: 5;
  opacity: 0.85;
  transition: opacity 0.15s ease, background 0.15s ease;
}

.zoom-trigger-btn:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.85);
}

.zoom-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
}

.zoom-overlay:active {
  cursor: grabbing;
}

.zoom-image {
  user-select: none;
  -webkit-user-drag: none;
  max-width: none;
  max-height: none;
  pointer-events: none;
}

.zoom-image--animating {
  transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.zoom-loading {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  z-index: 10;
}

.zoom-level-indicator {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-family: ' monospace', monospace;
  z-index: 10;
  pointer-events: none;
}

.zoom-controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 6px;
  padding: 4px;
  z-index: 10;
}

.zoom-ctrl-btn {
  background: transparent;
  color: #fff;
  width: 40px;
  height: 40px;
  min-height: 40px;
  border-radius: 4px;
}

.zoom-ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.zoom-close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.6); 
  color: #fff;
  border: 2px solid #fff !important;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  min-height: 44px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
  transition: background 0.15s ease, border-color 0.15s ease;
}

.zoom-close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: #fff;
}

.zoom-hint {
  position: absolute;
  bottom: 70px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: rgba(255, 255, 255, 0.9);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  white-space: nowrap;
  z-index: 10;
  pointer-events: none;
}

.zoom-hint-fade-enter-active,
.zoom-hint-fade-leave-active {
  transition: opacity 0.4s ease;
}

.zoom-hint-fade-enter-from,
.zoom-hint-fade-leave-to {
  opacity: 0;
}
</style>