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
        gist_url: 'https://gist.githubusercontent.com/yarl/bc4b89847f9ced089f7169bbfec79841/raw/c8bd23d3b354ce9d20de578245e4dc7c9f095fb0/wlm2015_fr_5.csv',
      })
      .then((data) => {

      })
      .catch((err) => { vm.error = err.data; });
  }
}

export default Component;
