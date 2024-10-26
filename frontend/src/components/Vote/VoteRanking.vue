<template>
  <cdx-message type="warning">
    <p>This screen is under development.</p>
  </cdx-message>
  <div class="vote-ranking-screen">
    <div class="vote-round-header">
      <div>
        <h2>{{ round.name }}</h2>
        <p class="vote-campaign-part">Part of {{ round.campaign.name }}</p>
      </div>

      <div class="vote-grid-size-controls">
        <cdx-button
          :action="gridSize === 3 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(3)"
        >
          <image-size-select-actual class="icon-small" /> Large
        </cdx-button>
        <cdx-button
          :action="gridSize === 2 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(2)"
        >
          <image-size-select-large class="icon-small" /> Medium
        </cdx-button>
        <cdx-button
          :action="gridSize === 1 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(1)"
        >
          <image-size-select-small class="icon-small" /> Small
        </cdx-button>
      </div>

      <cdx-button weight="quiet" action="progressive">
        <content-save-outline class="icon-small" /> Save Round
      </cdx-button>
    </div>

    <div class="vote-image-grid" :class="'grid-size-' + gridSize">
      <draggable class="vote-gallery" v-model="images">
        <div
          v-for="(image, index) in images"
          :key="image.id"
          class="vote-gallery-image link"
          :class="getImageSizeClass()"
        >
          <div class="vote-gallery-drag-icon">
            <drag-horizontal-variant />
          </div>
          <div class="vote-gallery-image-container">
            <img :src="image.url" />
          </div>
          <div class="vote-gallery-footer">
            <h3 class="vote-gallery-footer-name">
              <div class="vote-footer-content">
                <strong>{{ getOrdinal(index + 1) }} place</strong>
                <v-icon v-if="image.review">mdi-rate-review</v-icon>
              </div>
              <span v-if="!round.config.show_filename"> Image #{{ image.id }} </span>
              <span v-else>
                {{ image.name.split('_').join(' ') }}
              </span>
            </h3>
          </div>
        </div>
      </draggable>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

// Components
import { VueDraggableNext as draggable } from 'vue-draggable-next'
import { CdxButton, CdxMessage } from '@wikimedia/codex'

// Icon
import DragHorizontalVariant from 'vue-material-design-icons/DragHorizontalVariant.vue'
import ContentSaveOutline from 'vue-material-design-icons/ContentSaveOutline.vue'
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'

const round = reactive({
  name: 'Round 1',
  campaign: { name: "Mahmoud and Jay's new Campaign" },
  status: 'active',
  config: {
    show_filename: true
  }
})

const images = ref([
  {
    id: 1,
    name: 'Image1.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Salzburg_Michaelskirche_Deckenfresko-4118.jpg/512px-Salzburg_Michaelskirche_Deckenfresko-4118.jpg'
  },
  {
    id: 2,
    name: 'Image2.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Ninove_Omloop_Het_Nieuwsblad_2024_02.jpg/640px-Ninove_Omloop_Het_Nieuwsblad_2024_02.jpg'
  },
  {
    id: 3,
    name: 'Image1.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/Gesergiyo_sand_pinnacles%2C_Konso_%2825%29_%2829127485796%29.jpg/640px-Gesergiyo_sand_pinnacles%2C_Konso_%2825%29_%2829127485796%29.jpg'
  },
  {
    id: 4,
    name: 'Image2.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/5/50/Stavby_kyrka_-_KMB_-_16000200132457.jpg'
  },
  {
    id: 5,
    name: 'Image1.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Noord-Hollands_Archief%2C_Beeldcollectie_van_de_gemeente_Haarlem%2C_Inventarisnummer_NL-HlmNHA_1100_KNA006009247.JPG/637px-Noord-Hollands_Archief%2C_Beeldcollectie_van_de_gemeente_Haarlem%2C_Inventarisnummer_NL-HlmNHA_1100_KNA006009247.JPG'
  },
  {
    id: 6,
    name: 'Image2.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/2021-10-31_12-53-27_sf-connexion-Colmar.jpg/776px-2021-10-31_12-53-27_sf-connexion-Colmar.jpg'
  },
  {
    id: 7,
    name: 'Image1.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Aimard_-_Le_Grand_Chef_des_Aucas%2C_1889%2C_illust_30.png/632px-Aimard_-_Le_Grand_Chef_des_Aucas%2C_1889%2C_illust_30.png'
  },
  {
    id: 8,
    name: 'Image2.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/PanfilovkaPer_8.jpg/640px-PanfilovkaPer_8.jpg'
  },
  {
    id: 9,
    name: 'Image1.jpg',
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Lamb_of_God_Full_Force_2019_19.jpg/640px-Lamb_of_God_Full_Force_2019_19.jpg'
  }
])

const gridSize = ref(1)
const error = ref(null)

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

.vote-gallery-drag-icon {
  cursor: move;
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
</style>
