import template from './round-edit.html';

const Component = {
  bindings: {
    last: '=',
    round: '=',
  },
  controller,
  template,
};

function controller(
  $filter,
  $state,
  adminService,
  alertService) {
  const vm = this;

  vm.loading = false;
  vm.roundBackup = null;

  vm.cancelEditRound = cancelEditRound;
  vm.saveRound = saveRound;

  // functions

  vm.$onInit = () => {
    vm.roundBackup = angular.extend({}, vm.round);
    vm.round.jurors = vm.round.jurors
      .filter(juror => juror.is_active)
      .map(juror => ({ name: juror.username }));
  };

  /**
   * 
   */
  function cancelEditRound() {
    angular.extend(vm.round, vm.roundBackup);
    vm.round.edit = false;
  }

  /**
   * 
   */
  function saveRound() {
    const round = {
      id: vm.round.id,
      name: vm.round.name,
      quorum: vm.round.quorum,
      directions: vm.round.directions,
      deadline_date: $filter('date')(vm.round.deadline_date, 'yyyy-MM-ddTHH:mm:ss'),
      new_jurors: vm.round.jurors.map(user => user.name),
    };

    vm.loading = true;
    adminService
      .editRound(vm.round.id, round)
      .then(() => {
        $state.reload();
      })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  }
}

export default Component;
