<template>
  <cdx-message type="warning">
    <p>This screen is under development.</p>
  </cdx-message>
  <div class="ranking-screen">
    <div class="round-header">
      <div>
        <h2>{{ round.name }}</h2>
        <p style="color: gray">Part of {{ round.campaign.name }}</p>
      </div>
      <div class="order-by">
        <p style="font-size: 16px; color: gray">Order by:</p>
        <cdx-select v-model:selected="sortOrder.order_by" :menu-items="menuItems" />
        <cdx-select
          v-model:selected="sortOrder.sort"
          :menu-items="menuItemsSort"
          style="width: 100px !important"
        />
      </div>
      <div class="grid-size-controls" style="margin-left: 60px">
        <p style="font-size: 16px; color: gray; margin-left: 11px">Gallary size</p>
        <cdx-button
          :action="gridSize === 3 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(3)"
        >
          <image-size-select-actual style="font-size: 6px" />
        </cdx-button>
        <cdx-button
          :action="gridSize === 2 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(2)"
        >
          <image-size-select-large style="font-size: 6px" />
        </cdx-button>
        <cdx-button
          :action="gridSize === 1 ? 'progressive' : ''"
          weight="quiet"
          @click="setGridSize(1)"
        >
          <image-size-select-small style="font-size: 6px" />
        </cdx-button>
      </div>

      <cdx-button weight="quiet" action="progressive">
        <content-save-outline style="font-size: 6px" /> Save Round
      </cdx-button>
    </div>

    <div class="image-grid" :class="'grid-size-' + gridSize">
      <div
        v-for="vote in votes"
        :key="vote.id"
        class="gallery__image link"
        :class="getImageSizeClass()"
      >
        <div class="gallery__image-container">
          <img :src="vote.url" />
        </div>
        <div style="font-size: 14px; color: gray">
          <p>voted in a day</p>
          <p>5 Sep 2023 at 8:11 UTC</p>
        </div>
        <div style="margin-bottom: 40px; display: flex; justify-content: center; margin-top: 8px">
          <cdx-button :action="vote.value === true ? 'progressive' : ''" weight="quiet">
            <thumb-up style="font-size: 6px" /> Accept
          </cdx-button>
          <cdx-button :action="vote.value === false ? 'progressive' : ''" weight="quiet">
            <thumb-down style="font-size: 6px" /> Decline
          </cdx-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

// Components
import { CdxButton, CdxSelect, CdxMessage } from '@wikimedia/codex'

// Icons
import ContentSaveOutline from 'vue-material-design-icons/ContentSaveOutline.vue'
import ImageSizeSelectActual from 'vue-material-design-icons/ImageSizeSelectActual.vue'
import ImageSizeSelectLarge from 'vue-material-design-icons/ImageSizeSelectLarge.vue'
import ImageSizeSelectSmall from 'vue-material-design-icons/ImageSizeSelectSmall.vue'
import ThumbUp from 'vue-material-design-icons/ThumbUp.vue'
import ThumbDown from 'vue-material-design-icons/ThumbDown.vue'

const round = reactive({
  name: 'Round 1',
  campaign: { name: "Mahmoud and Jay's new Campaign" },
  status: 'active',
  config: {
    show_filename: true
  }
})

const votes = ref([
  {
    id: 1,
    value: true,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Salzburg_Michaelskirche_Deckenfresko-4118.jpg/512px-Salzburg_Michaelskirche_Deckenfresko-4118.jpg'
  },
  {
    id: 2,
    value: false,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Ninove_Omloop_Het_Nieuwsblad_2024_02.jpg/640px-Ninove_Omloop_Het_Nieuwsblad_2024_02.jpg'
  },
  {
    id: 3,
    value: true,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/Gesergiyo_sand_pinnacles%2C_Konso_%2825%29_%2829127485796%29.jpg/640px-Gesergiyo_sand_pinnacles%2C_Konso_%2825%29_%2829127485796%29.jpg'
  },
  {
    id: 4,
    value: true,
    url: 'https://upload.wikimedia.org/wikipedia/commons/5/50/Stavby_kyrka_-_KMB_-_16000200132457.jpg'
  },
  {
    id: 5,
    value: false,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Noord-Hollands_Archief%2C_Beeldcollectie_van_de_gemeente_Haarlem%2C_Inventarisnummer_NL-HlmNHA_1100_KNA006009247.JPG/637px-Noord-Hollands_Archief%2C_Beeldcollectie_van_de_gemeente_Haarlem%2C_Inventarisnummer_NL-HlmNHA_1100_KNA006009247.JPG'
  },
  {
    id: 6,
    value: false,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/2021-10-31_12-53-27_sf-connexion-Colmar.jpg/776px-2021-10-31_12-53-27_sf-connexion-Colmar.jpg'
  },
  {
    id: 7,
    value: true,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Aimard_-_Le_Grand_Chef_des_Aucas%2C_1889%2C_illust_30.png/632px-Aimard_-_Le_Grand_Chef_des_Aucas%2C_1889%2C_illust_30.png'
  },
  {
    id: 8,
    value: true,
    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/PanfilovkaPer_8.jpg/640px-PanfilovkaPer_8.jpg'
  },
  {
    id: 9,
    value: false,
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
  return `gallery__image--size-${gridSize.value}`
}

const sortOrder = reactive({
  order_by: 'votedate',
  sort: 'desc'
})

const menuItems = [
  { label: 'Vote Date', value: 'votedate' },
  { label: 'Sort by Filename', value: 'filename' }
]

const menuItemsSort = [
  { label: 'accending', value: 'asc' },
  { label: 'descending', value: 'desc' }
]
</script>

<style scoped>
.ranking-screen {
  padding: 20px;
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

.gallery__image {
  display: inline-block;
  position: relative;
  background: #ccc;
  width: calc((100% - 100px) / 5);
  height: 15vw;
  margin: 10px 10px 100px;
  vertical-align: top;
}

.gallery__image--size-2 {
  width: calc((100% - 100px) / 3);
  height: 28vw;
}

.gallery__image--size-3 {
  width: calc((100% - 100px) / 2);
  height: 43vw;
}

.gallery__image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
  /* Ensures no overflow */
}

.gallery__image-container img {
  width: 100%;
  height: auto;
  object-fit: cover;
}

.gallery__drag-icon {
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

.gallery__drag-icon > span[role='img'] {
  display: flex;
}

.gallery__footer {
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

.gallery__footer-name {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gallery__footer:hover {
  height: 50%;
  background: #e0e0e0;
}

.gallery__footer-name:hover {
  white-space: normal;
  font-size: 16px;
}
</style>
