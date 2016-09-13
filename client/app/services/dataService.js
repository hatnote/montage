const DataService = function($http, $q) {

  const service = {
    getCampaign: (id) => $http.get('/campaign/' + id),
    getRound: (id) => $http.get('/round/' + id),
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('dataService', DataService);
};
