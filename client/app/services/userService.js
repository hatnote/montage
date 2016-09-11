const UserService = function($http, $q) {

  const service = {
      getCampaign: (id) => $http.get('/admin/' + id),
      getCampaigns: () => $http.get('/admin'),
      getRound: (id) => $http.get('/admin/round' + id)
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('userService', UserService);
};
