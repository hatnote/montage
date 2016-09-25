const UserService = function ($http, $q) {

  function getData(response) {
    let data = response.data;
    return (data.code && data.code !== '200') ? { error: data } : data;
  }

  const admin = {
    // TODO: add an easy way to switch between paths for local dev & labs
    get: () => $http.get('/montage-dev/admin').then(getData, getData),
    getCampaign: (id) => $http.get('/montage-dev/admin/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get('/montage-dev/admin/round/' + id).then(getData, getData),

    addCampaign: (data) => $http.post('/montage-dev/admin/campaign', data).then(getData, getData),
    addRound: (id, data) => $http.post('/montage-dev/admin/campaign/' + id + '/new/round', data).then(getData, getData),

    editCampaign: (id, data) => $http.post('/montage-dev/admin/campaign/' + id, data).then(getData, getData),
    editRound: (id, data) => $http.post('/montage-dev/admin/round/' + id, data).then(getData, getData),
  };

  const juror = {
    get: () => $http.get('/montage-dev/juror').then(getData, getData),
    getCampaign: (id) => $http.get('/montage-dev/juror/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get('/montage-dev/juror/round/' + id).then(getData, getData),
    getRoundTasks: (id) => $http.get('/montage-dev/juror/round/' + id + '/tasks').then(getData, getData),
  };

  const service = {
    admin: admin,
    juror: juror,
    logout: () => $http.get('/montage-dev/logout')
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('userService', UserService);
};
