import './campaign.scss';
import template from './campaign.html';

const Component = {
  controller,
  template,
};

function controller($stateParams, adminService) {
  const vm = this;

  vm.campaign = null;

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
}

export default Component;
