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

        const hists = _.values(responses[0].query.pages)
        hists.forEach((element) => {
          if (element && element.imageinfo) {
            const image = _.find(tasks, {
              entry: { url: element.imageinfo[0].url }
            })
            if (image) {
              image.history = element.imageinfo
            }
          }
        })
        return data
      })
    })
  }
}

export default jurorService
