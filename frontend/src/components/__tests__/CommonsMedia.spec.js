import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CommonsMedia from '@/components/Media/CommonsMedia.vue'

describe('CommonsMedia.vue (GSoC Unified Media POC)', () => {
  it('renders a standard image tag for image/jpeg combinations', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        mediaUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/test.jpg',
        fileUrl: 'https://upload.wikimedia.org/wikipedia/commons/test.jpg',
        majorMime: 'image',
        minorMime: 'jpeg'
      },
      global: {
        mocks: { $t: (msg) => msg }
      }
    })

    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    const video = wrapper.find('video')
    expect(video.exists()).toBe(false)
  })

  it('drops into HTML5 video bindings when confronting video/webm sources natively', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        mediaUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/poster.jpg',
        fileUrl: 'https://upload.wikimedia.org/wikipedia/commons/test.webm',
        majorMime: 'video',
        minorMime: 'webm'
      },
      global: {
        mocks: { $t: (msg) => msg }
      }
    })

    const video = wrapper.find('video')
    expect(video.exists()).toBe(true)
    const source = wrapper.find('source')
    expect(source.exists()).toBe(true)
    expect(source.attributes('type')).toBe('video/webm')
    expect(video.attributes('poster')).toBe('https://upload.wikimedia.org/wikipedia/commons/thumb/poster.jpg')
  })

  it('synthesizes audio environments for audio/ogg contexts securely', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        mediaUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/preview.jpg',
        fileUrl: 'https://upload.wikimedia.org/wikipedia/commons/sound.ogg',
        majorMime: 'audio',
        minorMime: 'ogg',
        showAudioThumbnail: true
      },
      global: {
        mocks: { $t: (msg) => msg }
      }
    })

    const audio = wrapper.find('audio')
    expect(audio.exists()).toBe(true)
    const source = wrapper.find('source')
    expect(source.attributes('type')).toBe('audio/ogg')
  })
})
