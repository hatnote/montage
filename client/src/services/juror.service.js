import _ from 'lodash';

const UserService = ($http, $q, $window, dataService) => {
  const base = [$window.__env.baseUrl, 'v1'].join('/');

  const juror = {
    get: () => $http.get(base + '/juror'),
    getCampaign: id => $http.get(base + '/juror/campaign/' + id),
    allCampaigns: () => $http.get(base + '/juror/campaigns/all'),
    getPastVotes: (id, offset, orderBy, sort) => $http.get([
      base, 'juror/round', id,
      `votes?offset=${offset || 0}&order_by=${orderBy || 'date'}&sort=${sort || 'desc'}`,
    ].join('/')),
    getPastRanking: (id, offset) => $http.get(base + '/juror/round/' + id + '/rankings'),
    getFaves: () => $http.get(base + '/juror/faves'),

    getRound: id => $http.get(base + '/juror/round/' + id),
    getRoundTasks,
    getRoundVotesStats: id => $http.get(base + '/juror/round/' + id + '/votes-stats'),

    faveImage: (roundId, entryId) => $http.post(base + '/juror/round/' + roundId + '/' + entryId + '/fave', {}),
    unfaveImage: (roundId, entryId) => $http.post(base + '/juror/round/' + roundId + '/' + entryId + '/unfave', {}),
    flagImage: (roundId, entryId, reason) => $http.post(base + '/juror/round/' + roundId + '/' + entryId + '/flag', { reason }),

    setRating: (id, data) => $http.post(base + '/juror/round/' + id + '/tasks/submit', data),
  };

  function getRoundTasks(id, offset, orderBy, sort) {
    return $http.get(base + '/juror/round/' + id + '/tasks?count=5&offset=' + (offset || 0))
      .then((data) => {
        const tasks = data.data.tasks;
        const files = tasks.map(task => task.entry.name);

        return dataService.getImageInfo(files).then((responses) => {
          if (!responses.length) { return data; }

          const hists = _.values(responses[0].query.pages);
          hists.forEach((element) => {
            if (element && element.imageinfo) {
              const image = _.find(tasks, {
                entry: { url: element.imageinfo[0].url },
              });
              if (image) {
                image.history = element.imageinfo;
              }
            }
          });
          return data;
        });
      });
  }

  return juror;
};

export default UserService;
