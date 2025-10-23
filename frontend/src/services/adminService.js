import { apiBackend } from './api'

const adminService = {
  get: () => apiBackend.get('admin'),

  getUser: () => apiBackend.get('admin/user'),

  allCampaigns: () => apiBackend.get('admin/campaigns/all'),

  getCampaign: (id) => apiBackend.get(`admin/campaign/${id}`),

  getRound: (id) => apiBackend.get(`admin/round/${id}`),

  getReviews: (id) => apiBackend.get(`admin/round/${id}/reviews`),

  addOrganizer: (data) => apiBackend.post('admin/add_organizer', data),

  addCampaign: (data) => apiBackend.post('admin/add_campaign', data),

  addRound: (id, data) => apiBackend.post(`admin/campaign/${id}/add_round`, data),

  finalizeCampaign: (id) => apiBackend.post(`admin/campaign/${id}/finalize`, { post: true }),

  addCoordinator: (id, username) =>
    apiBackend.post(`admin/campaign/${id}/add_coordinator`, { username }),

  removeCoordinator: (id, username) =>
    apiBackend.post(`admin/campaign/${id}/remove_coordinator`, { username }),

  activateRound: (id) => apiBackend.post(`admin/round/${id}/activate`, { post: true }),

  pauseRound: (id) => apiBackend.post(`admin/round/${id}/pause`, { post: true }),

  populateRound: (id, data) => apiBackend.post(`admin/round/${id}/import`, data),

  editCampaign: (id, data) => apiBackend.post(`admin/campaign/${id}/edit`, data),

  editRound: (id, data) => apiBackend.post(`admin/round/${id}/edit`, data),

  cancelRound: (id) => apiBackend.post(`admin/round/${id}/cancel`),

  getRoundFlags: (id) => apiBackend.get(`admin/round/${id}/flags`),

  getRoundReviews: (id) => apiBackend.get(`admin/round/${id}/reviews`),

  getRoundVotes: (id) => apiBackend.get(`admin/round/${id}/votes`),

  previewRound: (id) => apiBackend.get(`admin/round/${id}/preview_results`),

  advanceRound: (id, data) => apiBackend.post(`admin/round/${id}/advance`, data),

  searchRoundEntries: (roundId, params) => {
    const queryParams = new URLSearchParams()
    if (params.search) queryParams.append('search', params.search)
    if (params.limit) queryParams.append('limit', params.limit)
    if (params.offset) queryParams.append('offset', params.offset)

    return apiBackend.get(
      `admin/maintainer/round/${roundId}/entries/search?${queryParams.toString()}`
    )
  },

  removeEntry: (roundId, entryId, data) => {
    return apiBackend.post(
      `admin/maintainer/round/${roundId}/entry/${entryId}/remove`,
      data
    )
  },

  // Direct download URLs (manual baseURL needed)
  downloadRound: (id) => `${apiBackend.defaults.baseURL}admin/round/${id}/results/download`,
  downloadEntries: (id) => `${apiBackend.defaults.baseURL}admin/round/${id}/entries/download`,
  downloadReviews: (id) => `${apiBackend.defaults.baseURL}admin/round/${id}/reviews`
}

export default adminService
