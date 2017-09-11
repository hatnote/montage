import './campaign.scss';
import template from './campaign.html';

const Component = {
  controller,
  template,
};

function controller($stateParams, adminService) {
  const vm = this;

  vm.campaign = null;

  vm.activateRound = activateRound;
  vm.pauseRound = pauseRound;
  vm.populateRound = populateRound;
  // vm.cancelRound = cancelRound;

  // functions

  vm.$onInit = () => {
    const id = $stateParams.id.split('-')[0];
    adminService
      .getCampaign(id)
      .then((data) => {
        vm.campaign = data.data;
        vm.campaign.rounds.forEach((round) => {
          getRoundDetails(round);
          getRoundResults(round);
        });
      })
      .catch((err) => { vm.error = err.data; });
  };

  function activateRound(round) {
    adminService
      .activateRound(round.id)
      .then(() => {
        getRoundDetails(round);
      });
  }

  function pauseRound(round) {
    adminService
      .pauseRound(round.id)
      .then(() => {
        getRoundDetails(round);
      });
  }

  /**
   * Getting details of round including jurors ratings
   * @param {Object} round
   */
  function getRoundDetails(round) {
    adminService
      .getRound(round.id)
      .then((data) => {
        angular.extend(round, data.data);
      })
      .catch((err) => { vm.error = err.data; });
  }

  /**
   * Getting current results of round
   * @param {Object} round
   */
  function getRoundResults(round) {
    adminService
      .previewRound(round.id)
      .then((data) => {
        angular.extend(round, {
          details: data.data,
        });
      })
      .catch((err) => { vm.error = err.data; });
  }

  function populateRound(round) {
    adminService
      .populateRound(round.id, {
        import_method: 'gistcsv',
        gist_url: 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv',
      })
      .then((data) => {

      })
      .catch((err) => { vm.error = err.data; });
  }
}

export default Component;
