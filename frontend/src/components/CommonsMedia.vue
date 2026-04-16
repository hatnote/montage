<template>
  <div class="commons-media-container" :style="{ width: width + 'px', maxWidth: '100%' }">
    <video
      v-if="mediaType === 'video'"
      :src="mediaUrl"
      controls
      :class="imageClass"
      :style="{ width: '100%', maxHeight: '80vh' }"
      @loadeddata="handleLoad"
      @error="handleError"
    >
      Your browser does not support the video tag.
    </video>
    
    <audio
      v-else-if="mediaType === 'audio'"
      :src="mediaUrl"
      controls
      :class="imageClass"
      :style="{ width: '100%' }"
      @loadeddata="handleLoad"
      @error="handleError"
    >
      Your browser does not support the audio tag.
    </audio>

    <CommonsImage
      v-else
      :image="image"
      :width="width"
      :alt="alt"
      :image-class="imageClass"
      @load="handleLoad"
      @error="handleError"
      v-bind="$attrs"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CommonsImage from './CommonsImage.vue'

const props = defineProps({
  image: {
    type: [Object, String],
    required: true
  },
  width: {
    type: Number,
    default: 1280
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

const imageName = computed(() => {
  return props.image?.entry?.name || props.image?.name || props.image
})

const encodedName = computed(() => {
  return encodeURIComponent(imageName.value)
})

const mediaType = computed(() => {
  if (!imageName.value) return 'image'
  const name = imageName.value.toLowerCase()
  if (name.endsWith('.mp4') || name.endsWith('.webm') || name.endsWith('.ogv')) {
    return 'video'
  }
  if (name.endsWith('.mp3') || name.endsWith('.ogg') || name.endsWith('.wav') || name.endsWith('.flac') || name.endsWith('.oga')) {
    return 'audio'
  }
  return 'image'
})

const mediaUrl = computed(() => {
  return `//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${encodedName.value}`
})

const handleLoad = () => {
  emit('load')
}

const handleError = () => {
  emit('error')
}
</script>

<style scoped>
.commons-media-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 auto;
}
</style>
