import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CommonsMedia from '../CommonsMedia.vue'
import CommonsImage from '../CommonsImage.vue'

describe('CommonsMedia Component', () => {
  it('renders video tag for .mp4 files', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        image: { name: 'Test_video.mp4' },
        width: 800
      }
    })
    
    // Check dynamic elements
    const video = wrapper.find('video')
    expect(video.exists()).toBe(true)
    expect(wrapper.find('audio').exists()).toBe(false)
    
    // Video should be mounted with correct properties
    expect(video.attributes('src')).toContain('Test_video.mp4')
  })

  it('renders audio tag for .mp3 files', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        image: { name: 'Soundtrack.mp3' },
        width: 800
      }
    })
    
    const audio = wrapper.find('audio')
    expect(audio.exists()).toBe(true)
    expect(wrapper.find('video').exists()).toBe(false)
    expect(audio.attributes('src')).toContain('Soundtrack.mp3')
  })

  it('falls back to CommonsImage for other files (.jpg)', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        image: { name: 'Photo.jpg' },
        width: 800
      }
    })
    
    // Video and Audio should not exist
    expect(wrapper.find('video').exists()).toBe(false)
    expect(wrapper.find('audio').exists()).toBe(false)
    
    // The fallback component CommonsImage should be rendered
    const commonsImage = wrapper.findComponent(CommonsImage)
    expect(commonsImage.exists()).toBe(true)
  })

  it('renders metadata overlay when showMetadata is true', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        image: { name: 'Audio.ogg' },
        showMetadata: true,
        duration: 125,
        width: 800
      }
    })
    
    // Should render the timestamp and mime badge
    const overlay = wrapper.find('.media-metadata-overlay')
    expect(overlay.exists()).toBe(true)
    expect(wrapper.text()).toContain('2:05') // 125s calculated format
  })
  
  it('gracefully handles missing image props', () => {
    const wrapper = mount(CommonsMedia, {
      props: {
        image: null,
        width: 800
      }
    })
    
    // Should fall back to generic CommonsImage or render empty block without crashing
    expect(wrapper.find('.commons-media-container').exists()).toBe(true)
  })
})
