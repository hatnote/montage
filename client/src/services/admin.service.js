import _ from 'lodash';

const Service = ($http, $q, $window, dataService) => {

  const base = $window.__env.baseUrl + 'v1/';

  const admin = {
    get: () => $http.get(base + 'admin'),
    getCampaign: (id) => $http.get(base + 'admin/campaign/' + id),
    getRound: (id) => $http.get(base + 'admin/round/' + id),

    addOrganizer: (data) => $http.post(base + 'admin/add_organizer', data),
    addCampaign: (data) => $http.post(base + 'admin/add_campaign', data),
    addRound: (id, data) => $http.post(base + 'admin/campaign/' + id + '/add_round', data),

    activateRound: (id) => $http.post(base + 'admin/round/' + id + '/activate', { 'post': true }),
    pauseRound: (id) => $http.post(base + 'admin/round/' + id + '/pause', { 'post': true }),

    populateRound: (id, data) => $http.post(base + 'admin/round/' + id + '/import', data),
    editCampaign: (id, data) => $http.post(base + 'admin/campaign/' + id + '/edit', data),
    editRound: (id, data) => $http.post(base + 'admin/round/' + id + '/edit', data),
    cancelRound: (id) => $http.post(base + 'admin/round/' + id + '/cancel'),

    previewRound: (id) => $http.get(base + 'admin/round/' + id + '/preview_results'),
    advanceRound: (id, data) => $http.post(base + 'admin/round/' + id + '/advance', data),

    downloadRound: (id) => base + 'admin/round/' + id + '/download',

    importCSV: (id) => $http.post(base + 'admin/round/' + id + '/import', {
      import_method: 'gistcsv',
      gist_url: 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
    })
  };

  return admin;
};

export default Service;
