import { apiBackend } from './api'
import _ from 'lodash'
import dataService from './dataService'

const jurorService = {
  get: () => apiBackend.get('juror'),

  getCampaign: (id) => apiBackend.get(`juror/campaign/${id}`),

  allCampaigns: () => apiBackend.get('juror/campaigns/all'),

  getPastVotes: (id, offset = 0, orderBy = 'date', sort = 'desc') =>
    apiBackend.get(`juror/round/${id}/votes?offset=${offset}&order_by=${orderBy}&sort=${sort}`),

  getPastRanking: (id) => apiBackend.get(`juror/round/${id}/rankings`),

  getFaves: () => apiBackend.get('juror/faves'),

  getRound: (id) => apiBackend.get(`juror/round/${id}`),

  getRoundVotesStats: (id) => apiBackend.get(`juror/round/${id}/votes-stats`),

  faveImage: (roundId, entryId) => apiBackend.post(`juror/round/${roundId}/${entryId}/fave`, {}),

  unfaveImage: (roundId, entryId) =>
    apiBackend.post(`juror/round/${roundId}/${entryId}/unfave`, {}),

  flagImage: (roundId, entryId, reason) =>
    apiBackend.post(`juror/round/${roundId}/${entryId}/flag`, { reason }),

  setRating: (id, data) => apiBackend.post(`juror/round/${id}/tasks/submit`, data),

  getRoundTasks: (id, offset = 0) => {
    return apiBackend.get(`juror/round/${id}/tasks?count=10&offset=${offset}`).then((data) => {
      const tasks = data.data.tasks
      const files = tasks.map((task) => task.entry.name)

      return dataService.getImageInfo(files).then((responses) => {
        if (!responses.length) return data

        responses.forEach((response) => {
          // Build redirect map (old name -> new name) if present
          const redirectMap = {}
          if (response.query.redirects) {
            response.query.redirects.forEach((redirect) => {
              const fromName = redirect.from.replace(/^File:/i, '')
              const toName = redirect.to.replace(/^File:/i, '')
              redirectMap[fromName] = toName
            })
          }

          const pages = _.values(response.query.pages)
          pages.forEach((page) => {
            if (page && page.imageinfo) {
              // Match by filename (could be the actual name or after redirect)
              const pageTitle = page.title.replace(/^File:/i, '')
              
              // Try to find by actual page title first, then check if any task redirects to this
              let image = _.find(tasks, (task) => task.entry.name === pageTitle)
              
              // If not found, check if this page is the target of a redirect
              if (!image) {
                const originalName = _.findKey(redirectMap, (target) => target === pageTitle)
                if (originalName) {
                  image = _.find(tasks, (task) => task.entry.name === originalName)
                }
              }
              
              if (image) {
                image.history = page.imageinfo
              }
            }
          })
        })
        return data
      })
    })
  }
}

export default jurorService
