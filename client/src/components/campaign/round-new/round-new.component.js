import template from './round-new.html';

const Component = {
  bindings: {
    campaign: '=',
    index: '=',
  },
  controller,
  template,
};

function controller(
  $filter,
  adminService) {
  const vm = this;

  vm.round = {};

  vm.addRound = addRound;

  // functions

  vm.$onInit = () => {
    vm.round = {
      name: `Round ${vm.index + 1}`,
      vote_method: 'yesno',
      quorum: 2,
      jurors: [],
      config: { show_link: true },
      imports: {
        import_method: 'gistcsv', // category
        // category: '',
        gist_url: 'https://gist.githubusercontent.com/yarl/bc4b89847f9ced089f7169bbfec79841/raw/c8bd23d3b354ce9d20de578245e4dc7c9f095fb0/wlm2015_fr_5.csv',
      },
    };
  };

  function addRound() {
    const round = angular.extend({}, vm.round, {
      deadline_date: $filter('date')(vm.round.deadline_date, 'yyyy-MM-ddTHH:mm:ss'),
      jurors: vm.round.jurors.map(user => user.name),
    });

    vm.loading = true;
    adminService
      .addRound(vm.campaign.id, round)
      .then(() => { })
      .catch((err) => { vm.error = err.data; })
      .finally(() => { vm.loading = false; });
  }
}

export default Component;
