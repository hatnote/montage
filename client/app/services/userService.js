const UserService = function ($http, $q) {

  function getData(response) {
    let data = response.data;
    return (data.code && data.code !== '200') ? { error: data } : data;
  }

  const admin = {
    get: () => $http.get('/admin').then(getData, getData),
    getCampaign: (id) => $http.get('/admin/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get('/admin/round/' + id).then(getData, getData),

    addCampaign: (data) => $http.post('/admin/campaign', data).then(getData, getData),
    addRound: (data) => $http.post('/admin/round', data).then(getData, getData),

    editCampaign: (id, data) => $http.post('/admin/campaign/' + id, data).then(getData, getData),
    editRound: (id, data) => $http.post('/admin/round/' + id, data).then(getData, getData),
  };

  const juror = {
    get: () => $http.get('/juror').then(getData, getData),
    getCampaign: (id) => $http.get('/juror/campaign/' + id).then(getData, getData),
    getRound: (id) => $http.get('/juror/round/' + id).then(getData, getData),
  };

  const service = {
    admin: admin,
    juror: juror,
    logout: () => $http.get('/logout')
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('userService', UserService);
};
