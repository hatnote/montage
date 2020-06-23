const Service = ($http, $q, $window) => {
  const base = [$window.__env.baseUrl, 'v1', 'admin'].join('/');

  const admin = {
    get: () => $http.get(base),
    getCampaign: id => $http.get([base, 'campaign', id].join('/')),
    getRound: id => $http.get([base, 'round', id].join('/')),

    addOrganizer: data => $http.post(`${base}/add_organizer`, data),
    addCampaign: data => $http.post(`${base}/add_campaign`, data),
    addRound: (id, data) => $http.post(`${base}/campaign/${id}/add_round`, data),
    finalizeCampaign: id => $http.post(`${base}/campaign/${id}/finalize`, { post: true }),
    reopenCampaign: id => $http.post(`${base}/campaign/${id}/reopen`, { post: true }),
    addCoordinator: (id, username) =>
      $http.post(`${base}/campaign/${id}/add_coordinator`, { username }),
    removeCoordinator: (id, username) =>
      $http.post(`${base}/campaign/${id}/remove_coordinator`, { username }),

    activateRound: id => $http.post(`${base}/round/${id}/activate`, { post: true }),
    pauseRound: id => $http.post(`${base}/round/${id}/pause`, { post: true }),

    populateRound: (id, data) => $http.post(`${base}/round/${id}/import`, data),
    editCampaign: (id, data) => $http.post(`${base}/campaign/${id}/edit`, data),
    editRound: (id, data) => $http.post(`${base}/round/${id}/edit`, data),
    cancelRound: id => $http.post(`${base}/round/${id}/cancel`),
    getRoundFlags: id => $http.get(`${base}/round/${id}/flags`),
    getRoundReviews: id => $http.get(`${base}/round/${id}/reviews`),
    getRoundVotes: id => $http.get(`${base}/round/${id}/votes`),

    previewRound: id => $http.get(`${base}/round/${id}/preview_results`),
    advanceRound: (id, data) => $http.post(`${base}/round/${id}/advance`, data),

    downloadRound: id => `${base}/round/${id}/results/download`,
    downloadEntries: id => `${base}/round/${id}/entries/download`
  };

  return admin;
};

export default Service;
