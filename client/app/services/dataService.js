const DataService = function ($http, $q) {

  const service = {
    getImageInfo: (images) => $http({
      method: 'JSONP',
      url: '//commons.wikimedia.org/w/api.php',
      params: {
        action: 'query',
        prop: 'imageinfo',
        titles: images.map((image) => 'File:' + image).join('|'),
        format: 'json',
        iiprop: 'timestamp|user|userid|size|dimensions|url',
        iilimit: '10',
        callback: 'JSON_CALLBACK'
      }
    }),
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
    }),
    searchCategory: (category) => $http({
      method: 'JSONP',
      url: '//commons.wikimedia.org/w/api.php',
      params: {
        action: 'opensearch',
        format: 'json',
        namespace: '14',
        limit: '10',
        search: category,
        callback: 'JSON_CALLBACK'
      }
    }),
  };

  return service;
};

export default () => {
  angular
    .module('montage')
    .factory('dataService', DataService);
};
