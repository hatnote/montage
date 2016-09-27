const UserService = function ($http, $q, $window) {

  function getData(response) {
    let data = response.data;
    return (data.code && data.code !== '200') ? { error: data } : data;
  }

  const base = $window.__env.baseUrl;

  const admin = {
    get: () => $http.get(base + 'admin').then(getData, getData),
    getCampaign: (id) => $http.get(base + 'admin/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get(base + 'admin/round/' + id).then(getData, getData),

    addCampaign: (data) => $http.post(base + 'admin/new/campaign', data).then(getData, getData),
    addRound: (id, data) => $http.post(base + 'admin/campaign/' + id + '/new/round', data).then(getData, getData),

    editCampaign: (id, data) => $http.post(base + 'admin/campaign/' + id, data).then(getData, getData),
    editRound: (id, data) => $http.post(base + 'admin/round/' + id, data).then(getData, getData),
  };

  const juror = {
    get: () => $http.get(base + 'juror').then(getData, getData),
    getCampaign: (id) => $http.get(base + 'juror/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get(base + 'juror/round/' + id).then(getData, getData),
    getRoundTasks: (id) => $http.get(base + 'juror/round/' + id + '/tasks').then(getData, getData),

    setRating: (data) => $http.post(base + 'juror/submit/rating', data).then(getData, getData)
  };

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
