const DataService = function($http, $q) {

  const service = {
    getCampaign: (id) => $http.get('/campaign/' + id),
    getRound: (id) => $http.get('/round/' + id),

    getTempImages: () => $http.get('/static/images_50.json'),  // temporary!
    getTempImage: () => $http.get('/static/images_50.json').then(data => {
      let index = Math.floor((Math.random() * 45) + 1);
      return data.data.images[index];
    })
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('dataService', DataService);
};
