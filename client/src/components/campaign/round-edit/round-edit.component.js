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
  $mdDialog,
  $state,
  adminService,
  alertService) {
  const vm = this;

  vm.loading = false;
  vm.roundBackup = null;

  vm.cancelEditRound = cancelEditRound;
  vm.deleteRound = deleteRound;
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
   * @param {Object} event 
   */
  function deleteRound(event) {
    const dialog = $mdDialog.confirm()
      .title('Delete Round')
      .textContent('Are you sure you want to delete this round?')
      .ariaLabel('Delete Round')
      .targetEvent(event)
      .ok('Delete Round')
      .cancel('Cancel');

    $mdDialog.show(dialog).then(() => {
      vm.loading = true;
      adminService
        .cancelRound(vm.round.id)
        .then(() => {
          $state.reload();
        })
        .catch(alertService.error)
        .finally(() => { vm.loading = false; });
    });
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
