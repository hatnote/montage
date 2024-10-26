<template>
  <cdx-message type="warning">
    <p>This screen is under development.</p>
  </cdx-message>
  <div class="vote-rating-screen">
    <div class="vote-image-container">
      <img :src="imageSrc" class="vote-image" />
    </div>
    <div class="vote-description-container">
      <div class="vote-header">
        <h2>{{ imageName }}</h2>
        <p class="vote-remaining-images">{{ remainingImages }} images remaining</p>
        <div class="vote-button-group">
          <cdx-button :href="imageLink" weight="quiet">
            <image-icon class="icon-small" /> Show full-size
          </cdx-button>
          <cdx-button :href="commonsPage" weight="quiet" class="commons-button">
            <link-icon class="icon-small" /> Commons page
          </cdx-button>
        </div>
      </div>
      <div class="vote-controls">
        <h3>Vote</h3>
        <div class="vote-stars">
          <span v-for="rate in [1, 2, 3, 4, 5]" :key="rate">
            <star />
          </span>
        </div>
        <span class="vote-keyboard-instructions">
          You can also use keyboard to vote.<br />
          <span class="key">1</span>-<span class="key">5</span> – One to Five Stars<br />
          <span class="key">→</span> – Skip (vote later)
        </span>
      </div>
      <div class="vote-actions">
        <h3>Actions</h3>
        <div class="vote-button-group">
          <cdx-button weight="quiet">
            <arrow-right class="icon-small" /> Skip (vote later)
          </cdx-button>
          <cdx-button weight="quiet">
            <pencil class="icon-small" /> Edit previous votes
          </cdx-button>
        </div>
      </div>

      <div class="vote-description-section">
        <h3>Description</h3>
        <div class="vote-description-details">
          <cloud-upload class="icon-small" />
          <div class="vote-date-time">
            <p>{{ date }}</p>
            <p>{{ time }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CdxButton, CdxMessage } from '@wikimedia/codex'

import ImageIcon from 'vue-material-design-icons/Image.vue'
import LinkIcon from 'vue-material-design-icons/Link.vue'
import ArrowRight from 'vue-material-design-icons/ArrowRight.vue'
import Pencil from 'vue-material-design-icons/Pencil.vue'
import CloudUpload from 'vue-material-design-icons/CloudUpload.vue'
import Star from 'vue-material-design-icons/Star.vue'

const imageName = ref('โง่ๆๆๆ.jpg')
const remainingImages = ref(2463)
const imageSrc = ref(
  'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Montreal_Zombie_Walk_2015_-_Doge_%2822033091143%29.jpg/640px-Montreal_Zombie_Walk_2015_-_Doge_%2822033091143%29.jpg'
)
const imageLink = ref(
  'https://upload.wikimedia.org/wikipedia/commons/1/1f/Montreal_Zombie_Walk_2015_-_Doge_%2822033091143%29.jpg'
)
const commonsPage = ref(
  'https://commons.wikimedia.org/wiki/File:Montreal_Zombie_Walk_2015_-_Doge_(22033091143).jpg'
)
const date = ref('18 Mar 2022')
const time = ref('Friday, 6:15')
</script>

<style scoped>
.vote-rating-screen {
  display: flex;
  padding: 24px;
  height: calc(100vh - 116.5px);
}

.vote-image-container {
  flex: 7;
  background-color: #e6e6e5;
  display: flex;
  justify-content: center;
  align-items: center;
}

.vote-image {
  max-width: 100%;
  height: auto;
  object-fit: contain;
}

.vote-description-container {
  flex: 3;
  padding-left: 16px;
  overflow-x: scroll;
}

.vote-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.vote-remaining-images {
  margin-top: 16px;
  color: gray;
}

.vote-button-group {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  width: 100%;
}

.vote-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.vote-stars {
  display: flex;
  justify-content: space-around;
  width: 100%;
}

.vote-keyboard-instructions {
  color: gray;
  margin-top: 16px;
}

.key {
  display: inline-block;
  margin: 0 0.1em;
  width: 18px;
  line-height: 18px;
  height: 18px;
  text-align: center;
  color: darkgray;
  background: white;
  font-size: 11px;
  border-radius: 3px;
  text-shadow: 0 1px 0 white;
  white-space: nowrap;
  border: 1px solid gray;
  box-shadow:
    0 1px 0px rgba(0, 0, 0, 0.2),
    0 0 0 2px #fff inset;
}

.vote-actions {
  margin-top: 24px;
}

.vote-description-section {
  margin-top: 24px;
}

.vote-description-details {
  display: flex;
  align-items: center;
  margin-left: 16px;
}

.vote-date-time {
  margin-left: 40px;
  color: gray;
}
</style>
