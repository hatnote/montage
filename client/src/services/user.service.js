import _ from 'lodash';

const UserService = function ($http, $q, $window, dataService) {

  function getData(response) {
    let data = response.data;
    return (response.status !== 200) ? { error: data } : data;
  }

  const base = $window.__env.baseUrl;

  const admin = {
    get: () => $http.get(base + 'admin').then(getData, getData),
    getCampaign: (id) => $http.get(base + 'admin/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get(base + 'admin/round/' + id).then(getData, getData),

    addOrganizer: (data) => $http.post(base + 'admin/add_organizer', data).then(getData, getData),
    addCampaign: (data) => $http.post(base + 'admin/add_campaign', data).then(getData, getData),
    addRound: (id, data) => $http.post(base + 'admin/campaign/' + id + '/add_round', data).then(getData, getData),

    activateRound: (id) => $http.post(base + 'admin/round/' + id + '/activate', { 'post': true }).then(getData, getData),
    pauseRound: (id) => $http.post(base + 'admin/round/' + id + '/pause', { 'post': true }).then(getData, getData),

    populateRound: (id, data) => $http.post(base + 'admin/round/' + id + '/import', data).then(getData, getData),
    editCampaign: (id, data) => $http.post(base + 'admin/campaign/' + id + '/edit', data).then(getData, getData),
    editRound: (id, data) => $http.post(base + 'admin/round/' + id + '/edit', data).then(getData, getData),
    cancelRound: (id) => $http.post(base + 'admin/round/' + id + '/cancel').then(getData, getData),

    previewRound: (id) => $http.get(base + 'admin/round/' + id + '/preview_results').then(getData, getData),
    advanceRound: (id, data) => $http.post(base + 'admin/round/' + id + '/advance', data).then(getData, getData),

    downloadRound: (id) => base + 'admin/round/' + id + '/download',

    importCSV: (id) => $http.post(base + 'admin/round/' + id + '/import', {
      import_method: 'gistcsv',
      gist_url: 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'
    }).then(getData, getData)
  };

  const juror = {
    get: () => $http.get(base + 'juror').then(getData, getData),
    getCampaign: (id) => $http.get(base + 'juror/campaign/' + id).then(getData, getData),
    getPastVotes: (id, offset) => $http.get(base + 'juror/round/' + id + '/ratings?offset=' + (offset || 0)).then(getData, getData),
    getPastRanking: (id, offset) => $http.get(base + 'juror/round/' + id + '/rankings').then(getData, getData),

    getRound: (id) => $http.get(base + 'juror/round/' + id).then(getData, getData),
    getRoundTasks: getRoundTasks,

    setRating: (id, data) => $http.post(base + 'juror/round/' + id + '/tasks/submit', data).then(getData, getData)
  };

  function getRoundTasks(id, offset) {
    return $http.get(base + 'juror/round/' + id + '/tasks?count=5&offset=' + (offset || 0))
      .then((response) => {
        let data = getData(response);
        if (data.error) {
          return data;
        }

        const tasks = data.data.tasks;
        const files = tasks.map((task) => task.entry.name);
        return dataService.getImageInfo(files).then((responses) => {
          const hists = [];
          responses.forEach(response => {
            const array = Object.keys(response.data.query.pages).map(key => response.data.query.pages[key]);
            Array.prototype.push.apply(hists, array);
          });

          hists.forEach(element => {
            let image = _.find(tasks, {
              entry: { url: element.imageinfo[0].url }
            });
            if(image) {
              image.history = element.imageinfo;
            }
          });
          return data;
        });
      }, getData);
  }

  const service = {
    admin: admin,
    juror: juror,
    logout: () => $http.get(base + 'logout')
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('userService', UserService);
};
