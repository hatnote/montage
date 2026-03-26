<template>
  <div class="commons-media">
    <video
      v-if="mimeMajor === 'video'"
      :src="rawUrl"
      controls
      :class="imageClass"
      v-bind="$attrs"
    />
    <audio
      v-else-if="mimeMajor === 'audio'"
      :src="rawUrl"
      controls
      class="commons-media-audio"
      v-bind="$attrs"
    />
    <img
      v-else
      :src="currentSrc"
      :alt="alt"
      :class="imageClass"
      @load="handleLoad"
      @error="handleError"
      v-bind="$attrs"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  image: {
    type: [Object, String],
    required: true
  },
  width: {
    type: Number,
    default: 1280
    // Use Commons standard thumbnail sizes for best performance (pre-cached):
    // 320, 640, 800, 1024, 1280, 2560
    // These sizes are already generated and cached by Wikimedia Commons
  },
  alt: {
    type: String,
    default: ''
  },
  imageClass: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['load', 'error'])

const attemptIndex = ref(0)
const hasLoaded = ref(false)

const imageName = computed(() => {
  return props.image?.entry?.name || props.image?.name || props.image
})

const encodedName = computed(() => {
  return encodeURIComponent(imageName.value)
})

// Use Special:Redirect for maximum compatibility
// This works for all file types including TIFF, handles redirects, and performs format conversion
const urlStrategies = computed(() => {
  const name = encodedName.value
  const width = props.width

  return [
    // Strategy 1: Special:Redirect/file with width (works universally, handles TIFF → JPG conversion)
    `//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${name}&width=${width}`,

    // Strategy 2: Special:Redirect/file without width (full size fallback)
    `//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${name}`
  ]
})

const currentSrc = computed(() => {
  return urlStrategies.value[attemptIndex.value]
})

const mimeMajor = computed(() => {
  return props.image?.entry?.mime_major || props.image?.mime_major || 'image'
})

const rawUrl = computed(() => {
  return `//commons.wikimedia.org/wiki/Special:FilePath/${encodedName.value}`
})

const handleLoad = () => {
  hasLoaded.value = true
  emit('load')
}

const handleError = () => {
  // Try next strategy if available
  if (attemptIndex.value < urlStrategies.value.length - 1) {
    attemptIndex.value++
  } else {
    // All strategies failed
    emit('error')
  }
}

// Reset attempt index when image changes
watch(imageName, () => {
  attemptIndex.value = 0
  hasLoaded.value = false
})
</script>

<style scoped>
.commons-media {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.commons-media img,
.commons-media video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.commons-media-audio {
  width: 100%;
  padding: 10px;
}
</style>
