<template>
  <div class="disqualify-panel">
    <div class="diqualify-panel-controls">
      <div class="disqualify-grid-size-controls">
        <cdx-button
          :action="gridSize === 3 ? 'progressive' : ''"
          weight="quite"
          @click="setGridSize(3)"
        >
          <image-size-select-actual class="icon-small" />
          {{ $t('montage-vote-grid-size-large') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 2 ? 'progressive' : ''"
          weight="quite"
          @click="setGridSize(2)"
        >
          <image-size-select-large class="icon-small" />
          {{ $t('montage-vote-grid-size-medium') }}
        </cdx-button>
        <cdx-button
          :action="gridSize === 1 ? 'progressive' : ''"
          weight="quite"
          @click="setGridSize(1)"
        >
          <image-size-select-small class="icon-small" />
          {{ $t('montage-vote-grid-size-small') }}
        </cdx-button>
      </div>
    </div>

    <div class="disqualify-grid" :class="'grid-size-' + gridSize">
      <div
        v-for="entry in entries"
        :key="entry.id"
        class="disqualify-entry"
        :class="{ 'disqualify-entry--disqualified': entry.dq_user_id }"
      >
        <div class="disqualify-entry-image">
          <CommonsImage :image="entry" :width="640" image-class="disqualify-entry-thumbnail" />
          <div v-if="entry.dq_user_id" class="disqualify-entry-overlay">
            <span>DQ</span>
          </div>
        </div>

        <div class="disqualify-entry-info">
          <p class="disqualify-entry-name" :title="entry.name">
            {{ entry.name.split('_').join(' ') }}
          </p>

          <p v-if="entry.dq_reason" class="disqualify-entry-reason">
            {{ $t('montage-disqualify-reason-label', [entry.dq_reason]) }}
          </p>

          <div class="disqualify-entry-actions">
            <a
              :href="'https://commons.wikimedia.org/wiki/File:' + encodeURIComponent(entry.name)"
              target="_blank"
              rel="noopener"
            >
              <cdx-button size="medium">
                <link-icon class="icon-small" />
                {{ $t('montage-view-on-commons') }}
              </cdx-button>
            </a>
            <cdx-button
              v-if="canModify && !entry.dq_user_id"
              action="destructive"
              @click="$emit('disqualify', entry)"
            >
              <cancel-icon class="icon-small" />
              {{ $t('montage-disqualify-action') }}
            </cdx-button>
            <cdx-button
              v-if="canModify && entry.dq_user_id"
              action="progressive"
              @click="$emit('requalify', entry)"
            >
              <undo-icon class="icon-small" />
              {{ $t('montage-requalify-action') }}
            </cdx-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxButton } from '@wikimedia/codex'
import CommonsImage from '@/components/CommonsImage.vue'

import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import LinkIcon from 'vue-material-design-icons/Link.vue'
import CancelIcon from 'vue-material-design-icons/Cancel.vue'
import UndoIcon from 'vue-material-design-icons/Undo.vue'

const { t: $t } = useI18n()
defineProps({
  entries: {
    type: Array,
    required: true
  },
  canModify: {
    type: Boolean,
    default: true
  }
})

defineEmits(['disqualify', 'requalify'])
const gridSize = ref(2)
const setGridSize = (size) => {
  gridSize.value = size
}
</script>

<style scoped>
.disqualify-panel {
  padding: 16px 0;
}
.disqualify-panel-controls {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
.disqualify-grid-size-controls {
  display: flex;
  gap: 8px;
}
.disqualify-grid {
  display: grid;
  gap: 16px;
}
.disqualify-grid.grid-size-1 {
  grid-template-columns: repeat(5, 1fr);
}
.disqualify-grid.grid-size-2 {
  grid-template-columns: repeat(3, 1fr);
}
.disqualify-grid.grid-size-3 {
  grid-template-columns: repeat(2, 1fr);
}
.disqualify-entry {
  border: 1px solid #c8ccd1;
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
}
.disqualify-entry--disqualified {
  opacity: 0.7;
  border-color: #d33;
}
.disqualify-entry-image {
  position: relative;
  width: 100%;
  height: 200px;
  background: #eaecf0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.disqualify-grid.grid-size-2 .disqualify-entry-image {
  height: 250px;
}
.disqualify-grid.grid-size-3 .disqualify-entry-image {
  height: 350px;
}
.disqualify-entry-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.disqualify-entry-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(211, 51, 51, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}
.disqualify-entry-overlay span {
  background: #d33;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 18px;
}
.disqualify-entry-info {
  padding: 12px;
}
.disqualify-entry-name {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.disqualify-entry-reason {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #d33;
  font-style: italic;
}
.disqualify-entry-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.disqualify-empty {
  text-align: center;
  padding: 48px;
  color: #72777d;
}
.icon-small {
  font-size: 6px;
}
</style>
