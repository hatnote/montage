<template>
  <div class="commons-media-container" :style="{ width: containerWidth }">
    <!-- Video Handler -->
    <template v-if="isMediaVideo">
      <video
        ref="mediaElement"
        controls
        preload="metadata"
        :poster="mediaUrl"
        class="commons-media-content"
      >
        <source :src="fileUrl" :type="mimeType" />
        <source v-if="majorMime === 'video' && minorMime === 'webm'" :src="fileUrl" type="video/webm" />
        <source v-if="majorMime === 'video' && minorMime === 'mp4'" :src="fileUrl" type="video/mp4" />
        {{ $t('montage-media-video-not-supported', 'Your browser does not support the video tag.') }}
      </video>
    </template>

    <!-- Audio Handler -->
    <template v-else-if="isMediaAudio">
      <div class="audio-wrapper">
        <audio
          ref="mediaElement"
          controls
          class="commons-media-audio"
        >
          <source :src="fileUrl" :type="mimeType" />
          {{ $t('montage-media-audio-not-supported', 'Your browser does not support the audio element.') }}
        </audio>
        <div v-if="showAudioThumbnail" class="audio-thumbnail">
           <img :src="mediaUrl" :alt="filename" class="audio-preview-icon" />
        </div>
      </div>
    </template>

    <!-- Fallback Standard Image Handler -->
    <template v-else>
      <img
        :src="mediaUrl"
        :alt="filename"
        class="commons-media-content"
        :class="{ 'pixelated': !isHighRes }"
        @click="emitClick"
      />
    </template>

    <div v-if="showMetadata" class="media-metadata-overlay">
      <span class="media-badge">{{ majorMime.toUpperCase() }}</span>
      <span v-if="duration" class="media-duration">{{ formatDuration(duration) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mediaUrl: {
    type: String,
    required: true
  },
  fileUrl: {
    type: String,
    default: ''
  },
  filename: {
    type: String,
    default: 'Wikimedia Commons Media'
  },
  majorMime: {
    type: String,
    default: 'image'
  },
  minorMime: {
    type: String,
    default: 'jpeg'
  },
  duration: {
    type: Number,
    default: null
  },
  width: {
    type: [Number, String],
    default: '100%'
  },
  showMetadata: {
    type: Boolean,
    default: false
  },
  showAudioThumbnail: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['media-click'])

const isMediaVideo = computed(() => {
  return props.majorMime.toLowerCase() === 'video'
})

const isMediaAudio = computed(() => {
  return props.majorMime.toLowerCase() === 'audio'
})

const mimeType = computed(() => {
  return `${props.majorMime}/${props.minorMime}`
})

const containerWidth = computed(() => {
  return typeof props.width === 'number' ? `${props.width}px` : props.width
})

const isHighRes = computed(() => {
  // Check if it's a heavily scaled thumbnail
  return !props.mediaUrl.includes('120px-')
})

const formatDuration = (seconds) => {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const emitClick = () => {
  emit('media-click', { url: props.mediaUrl, type: props.majorMime })
}
</script>

<style scoped>
.commons-media-container {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.commons-media-content {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.pixelated {
  image-rendering: pixelated;
}

.audio-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 16px;
}

.commons-media-audio {
  width: 100%;
  margin-top: 8px;
}

.audio-preview-icon {
  max-height: 150px;
  opacity: 0.8;
}

.media-metadata-overlay {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  pointer-events: none;
}

.media-badge, .media-duration {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}
</style>
