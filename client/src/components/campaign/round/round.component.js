import template from './round.html';

const Component = {
  bindings: {
    last: '=',
    round: '=',
  },
  controller,
  template,
};

function controller(adminService) {
  const vm = this;

  vm.activateRound = activateRound;
  vm.pauseRound = pauseRound;
  vm.populateRound = populateRound;
  vm.editRound = () => { vm.round.edit = true; };

  // functions

  vm.$onInit = () => {
  };

  function activateRound() {
    adminService
      .activateRound(vm.round.id)
      .then(() => {
        getRoundDetails(vm.round);
      });
  }

  function pauseRound() {
    adminService
      .pauseRound(vm.round.id)
      .then(() => {
        getRoundDetails(vm.round);
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

  function populateRound() {
    adminService
      .populateRound(vm.round.id, {
        import_method: 'gistcsv',
        gist_url: 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv',
      })
      .then((data) => {

      })
      .catch((err) => { vm.error = err.data; });
  }
}

export default Component;
