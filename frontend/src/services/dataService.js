import { apiCommons } from './api'

const dataService = {
  async getImageInfo(images) {
    const parts = Math.ceil(images.length / 50)
    let promises = []

    for (let i = 0; i < parts; i++) {
      const part = images.slice(50 * i, 50 * i + 50)
      promises.push(
        apiCommons({
          method: 'GET',
          params: {
            action: 'query',
            prop: 'imageinfo',
            titles: part.map((image) => 'File:' + image).join('|'),
            format: 'json',
            iiprop: 'timestamp|user|userid|size|dimensions|url',
            iilimit: '10',
            origin: '*'
          }
        })
      )
    }

    try {
      const results = await Promise.all(promises)
      return results.map((response) => response.data)
    } catch (error) {
      console.error('Error fetching image info:', error)
      throw error
    }
  },

  async searchUser(username) {
    try {
      const response = await apiCommons({
        method: 'GET',
        params: {
          action: 'query',
          list: 'globalallusers',
          format: 'json',
          rawcontinue: 'true',
          agufrom: username,
          origin: '*'
        }
      })
      return response
    } catch (error) {
      console.error('Error searching for user:', error)
      throw error
    }
  },

  async searchCategory(category) {
    try {
      const response = await apiCommons({
        method: 'GET',
        params: {
          action: 'opensearch',
          format: 'json',
          namespace: '14',
          limit: '10',
          search: category,
          origin: '*'
        }
      })
      return response
    } catch (error) {
      console.error('Error searching for category:', error)
      throw error
    }
  }
}

export default dataService
