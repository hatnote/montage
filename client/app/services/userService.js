const UserService = function ($http, $q) {

  function getData(response) {
    let data = response.data;
    return (data.code && data.code !== '200') ? { error: data } : data;
  }

  const service = {
    getCampaign: (id) => $http.get('/admin/' + id).then(getData, getData),
    getCampaigns: () => $http.get('/admin').then(getData, getData),
    getRound: (id) => $http.get('/admin/round/' + id).then(getData, getData),
    logout: () => $http.get('/logout')
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('userService', UserService);
};
