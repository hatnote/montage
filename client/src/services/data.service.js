const DataService = function ($http, $q) {

  const service = {
    getImageInfo: (images) => {
      const parts = Math.ceil(images.length / 50);
      let promises = [];
      for (let i = 0; i < parts; i++) {
        const part = images.slice(50 * i, 50 * i + 50);
        promises.push($http({
          method: 'JSONP',
          url: 'https://commons.wikimedia.org/w/api.php',
          params: {
            action: 'query',
            prop: 'imageinfo',
            titles: part.map((image) => 'File:' + image).join('|'),
            format: 'json',
            iiprop: 'timestamp|user|userid|size|dimensions|url',
            iilimit: '10'
          }
        }));
      }
      return $q.all(promises);
    },
    searchUser: (username) => $http({
      method: 'JSONP',
      url: 'https://commons.wikimedia.org/w/api.php',
      params: {
        action: 'query',
        list: 'globalallusers',
        format: 'json',
        rawcontinue: 'true',
        agufrom: username,
      }
    }),
    searchCategory: (category) => $http({
      method: 'JSONP',
      url: 'https://commons.wikimedia.org/w/api.php',
      params: {
        action: 'opensearch',
        format: 'json',
        namespace: '14',
        limit: '10',
        search: category,
      }
    }),
  };

  return service;
};

export default DataService;
