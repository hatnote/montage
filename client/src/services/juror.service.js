import _ from 'lodash';

const UserService = ($http, $q, $window, dataService) => {

  const base = $window.__env.baseUrl + 'v1/';

  const juror = {
    get: () => $http.get(base + 'juror'),
    getCampaign: (id) => $http.get(base + 'juror/campaign/' + id),
    getPastVotes: (id, offset) => $http.get(base + 'juror/round/' + id + '/ratings?offset=' + (offset || 0)),
    getPastRanking: (id, offset) => $http.get(base + 'juror/round/' + id + '/rankings'),

    getRound: (id) => $http.get(base + 'juror/round/' + id),
    getRoundTasks: getRoundTasks,

    setRating: (id, data) => $http.post(base + 'juror/round/' + id + '/tasks/submit', data),
  };

  function getRoundTasks(id, offset) {
    return $http.get(base + 'juror/round/' + id + '/tasks?count=5&offset=' + (offset || 0))
      .then((data) => {
        const tasks = data.data.tasks;
        const files = tasks.map(task => task.entry.name);

        return dataService.getImageInfo(files).then((responses) => {
          const hists = _.values(responses[0].query.pages);

/*
          responses[0].forEach((response) => {
            const array = Object.keys(response.data.query.pages)
              .map(key => response.data.query.pages[key]);
            Array.prototype.push.apply(hists, array);
          });
*/
          hists.forEach((element) => {
            let image = _.find(tasks, {
              entry: { url: element.imageinfo[0].url },
            });
            if (image) {
              image.history = element.imageinfo;
            }
          });
          return data;
        });
      });
  }

  return juror;
};

export default UserService;
