<template>
    <div class="vote-image-review-dialog">
        <div class="vote-image-review-dialog-image-container">
            <CommonsImage :image="image" :width="800" image-class="vote-image-review-dialog-image" />
        </div>
        <div class="vote-image-review-dialog-review-section">
            <h3>{{ image.name.split('_').join(' ') }}</h3>
            <div class="vote-file-links">
                <a :href="getCommonsImageUrl(image, null)" target="_blank">
                    <cdx-button>
                        <image-icon class="icon-small" /> Show full-size
                    </cdx-button>
                </a>
                <a :href="'https://commons.wikimedia.org/wiki/File:' + image.entry.name" target="_blank"
                    style="margin-right: 16px;">
                    <cdx-button class="vote-commons-button">
                        <link-icon class="icon-small" /> Commons page
                    </cdx-button>
                </a>
            </div>
            <div class="vote-details">
                <div class="vote-details-list">
                    <div class="vote-details-list-item vote-details-2-line">
                        <cloud-upload class="vote-details-icon" />
                        <div class="vote-details-list-item-text">
                            <h4>{{ formattedDateTime.date }}</h4>
                            <p>{{ formattedDateTime.day }}, {{ formattedDateTime.time }}</p>
                        </div>
                    </div>
                    <div class="vote-details-list-item vote-details-2-line">
                        <div class="icon-container">
                            <image-album class="vote-details-icon" />
                        </div>
                        <div class="vote-details-list-item-text">
                            <h4>{{ image.entry.resolution / 1000000 }} Mpix</h4>
                            <p>
                                {{ image.entry.width + ' x ' + image.entry.height }}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="vote-image-review-dialog-review">
                <h4>Review:</h4>
                <cdx-text-area v-model="imageReview" />
                <p>
                    All your reviews will be saved after click on "Save Round" / "Save Changes" button.
                </p>
            </div>
        </div>
    </div>
</template>

<script setup>
import { defineProps, defineExpose, ref, computed } from 'vue';
// import { useI18n } from 'vue-i18n';
import { CdxTextArea, CdxButton } from '@wikimedia/codex';
import { getCommonsImageUrl } from '@/utils';
import CommonsImage from '@/components/CommonsImage.vue';

import ImageIcon from 'vue-material-design-icons/Image.vue'
import LinkIcon from 'vue-material-design-icons/Link.vue'
import CloudUpload from 'vue-material-design-icons/CloudUpload.vue'
import ImageAlbum from 'vue-material-design-icons/ImageAlbum.vue'

// const { t: $t } = useI18n()

const props = defineProps({
    image: Object,
    onSave: Function,
});

const imageReview = ref(props.image.review || '');

const saveImageData = () => {
    if (props.onSave) {
        props.onSave(imageReview.value);
    }
};

const formattedDateTime = computed(() => {
    const uploadDate = props.image.entry.upload_date
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

defineExpose({ saveImageData });
</script>

<style scoped>
.vote-image-review-dialog {
    display: flex;
    width: 100%;
}

.vote-image-review-dialog-image-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    max-width: 50%;
    max-height: 100%;
    overflow: hidden;
    background: #f5f5f5;
}

.vote-image-review-dialog-image {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.vote-image-review-dialog-review-section {
    flex: 1;
    padding: 0 1rem;
    display: flex;
    flex-direction: column;
}

.vote-image-review-dialog-review {
    margin-top: 16px;
}

.vote-image-review-dialog-review p {
    font-size: 12px;
    color: rgba(0, 0, 0, 0.54);
    margin-top: 8px;
}

.vote-file-links {
    display: flex;
    justify-content: space-around;
    align-items: center;
    margin-top: 20px;
}

.vote-commons-button {
    color: rgb(51, 102, 204);
}

.vote-details {
    margin-top: 16px;
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
</style>