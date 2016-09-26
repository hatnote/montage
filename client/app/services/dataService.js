const DataService = function ($http, $q) {

  const service = {
    searchUser: (username) => $http({
      method: 'JSONP',
      url: '//commons.wikimedia.org/w/api.php',
      params: {
        action: 'query',
        list: 'globalallusers',
        format: 'json',
        rawcontinue: 'true',
        agufrom: username,
        callback: 'JSON_CALLBACK'
      }
    })
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('dataService', DataService);
};
