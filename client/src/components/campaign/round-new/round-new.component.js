import template from './round-new.html';

const Component = {
  bindings: {
    campaign: '=',
    index: '=',
    showForm: '=',
  },
  controller,
  template,
};

function controller(
  $filter,
  $state,
  adminService,
  alertService,
  dataService) {
  const vm = this;

  vm.category = null;
  vm.loading = 0;
  vm.prevRound = null;
  vm.round = {};

  vm.addRound = addRound;
  vm.advanceRound = advanceRound;
  vm.cancelAddRound = cancelAddRound;
  vm.searchCategory = searchCategory;

  // functions

  vm.$onInit = () => {
    const methods = [null, 'yesno', 'rating', 'ranking'];

    vm.round = {
      name: `Round ${vm.index}`,
      vote_method: methods[vm.index] || 'rating',
      quorum: 2,
      jurors: [],
      config: {
        dq_by_resolution: true,
        min_resolution: 2000000,

        dq_by_upload_date: true,
        dq_by_uploader: true,
        dq_coords: true,
        dq_maintainers: true,
        dq_organizers: true,
        show_filename: true,
        show_link: true,
        show_resolution: true,
      },
      imports: {
        import_method: 'gistcsv', // category
        // category: '',
        gist_url: 'https://gist.githubusercontent.com/yarl/bc4b89847f9ced089f7169bbfec79841/raw/c8bd23d3b354ce9d20de578245e4dc7c9f095fb0/wlm2015_fr_5.csv',
      },
    };

    if (vm.index > 1) {
      vm.prevRound = vm.campaign.rounds[vm.index - 2];
      vm.round.jurors = vm.prevRound.jurors
        .filter(juror => juror.is_active)
        .map(juror => ({ id: juror.id, name: juror.username }));
    }
  };

  /**
   * 
   */
  function addRound() {
    const round = angular.extend({}, vm.round, {
      deadline_date: $filter('date')(vm.round.deadline_date, 'yyyy-MM-ddTHH:mm:ss'),
      jurors: vm.round.jurors.map(user => user.name),
    });

    vm.loading += 1;
    adminService
      .addRound(vm.campaign.id, round)
      .then((data) => {
        importCategory(data.data.id, vm.category || vm.categorySearchText);
      })
      .catch(alertService.error)
      .finally(() => { vm.loading -= 1; });
  }

  /**
   * 
   */
  function advanceRound() {
    const round = {
      next_round: {
        name: vm.round.name,
        vote_method: vm.round.vote_method,
        quorum: vm.round.quorum,
        deadline_date: $filter('date')(vm.round.deadline_date, 'yyyy-MM-ddTHH:mm:ss'),
        jurors: vm.round.jurors.map(user => user.name),
      },
      threshold: vm.round.threshold,
    };

    vm.loading += 1;
    adminService
      .advanceRound(vm.prevRound.id, round)
      .then(() => { $state.reload(); })
      .catch(alertService.error)
      .finally(() => { vm.loading -= 1; });
  }

  /**
   * 
   */
  function cancelAddRound() {
    vm.campaign.rounds.pop();
  }

  /**
   * 
   * @param {int} id 
   * @param {String} name 
   */
  function importCategory(id, name) {
    vm.loading += 1;
    adminService
      .populateRound(id, {
        import_method: 'category',
        category: name,
      })
      .then(() => { $state.reload(); })
      .catch(alertService.error)
      .finally(() => { vm.loading -= 1; });
  }

  /**
   * 
   * @param {String} name 
   */
  function searchCategory(name) {
    return dataService
      .searchCategory(name)
      .then(response => response[1].map(element => element.substring(9)));
  }
}

export default Component;
