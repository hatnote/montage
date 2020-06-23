import './campaign.scss';
import template from './campaign.html';

const Component = {
  controller,
  template,
};

function controller($filter, $q, $state, $stateParams, adminService, alertService) {
  const vm = this;

  vm.campaign = null;
  vm.edit = false;
  vm.loading = false;
  vm.newRound = false;

  vm.closeCampaign = closeCampaign;
  vm.reopenCampaign = reopenCampaign;
  vm.editCampaign = editCampaign;
  vm.saveEditCampaign = saveEditCampaign;

  // functions

  vm.$onInit = () => {
    const id = $stateParams.id.split('-')[0];

    vm.loading = true;
    adminService
      .getCampaign(id)
      .then((data) => {
        vm.campaign = data.data;
        vm.campaign.rounds = vm.campaign.rounds.filter(round => round.status !== 'cancelled');
        vm.error = data.errors;

        if (!vm.campaign.rounds.length) {
          vm.campaign.rounds.push({});
        }

        vm.isCampaignClosed = vm.campaign.status === 'finalized';
      })
      .catch((err) => {
        vm.err = err;
      })
      .finally(() => {
        vm.loading = false;
      });
  };

  /**
   *
   * @param {Boolean} value
   */
  function editCampaign(value) {
    if (value) {
      vm.campaignBackup = angular.extend({}, vm.campaign);
      angular.extend(vm.campaign, {
        open_date: new Date(vm.campaign.open_date),
        close_date: new Date(vm.campaign.close_date),
        coordinators: vm.campaign.coordinators.map(user => ({ id: user.id, name: user.username })),
      });
    } else {
      angular.extend(vm.campaign, vm.campaignBackup);
    }
    vm.edit = value;
  }

  /**
   *
   */
  function closeCampaign() {
    vm.loading = true;
    adminService
      .finalizeCampaign(vm.campaign.id)
      .then(() => $state.reload())
      .catch(alertService.error)
      .finally(() => {
        vm.loading = false;
      });
  }

  function reopenCampaign() {
    vm.loading = true;
    adminService
      .reopenCampaign(vm.campaign.id)
      .then(() => $state.reload())
      .catch(alertService.error)
      .finally(() => {
        vm.loading = false;
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
      .catch(alertService.error);
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
      .catch(alertService.error);
  }

  function saveEditCampaign() {
    vm.loading = true;

    const campaign = angular.extend({}, vm.campaign, {
      open_date: $filter('date')(vm.campaign.open_date, 'yyyy-MM-ddTHH:mm:ss'),
      close_date: $filter('date')(vm.campaign.close_date, 'yyyy-MM-ddTHH:mm:ss'),
    });

    const oldCoordinators = vm.campaignBackup.coordinators.map(user => user.username);
    const newCoordinators = vm.campaign.coordinators.map(user => user.name);

    const added = newCoordinators
      .filter(x => oldCoordinators.indexOf(x) < 0)
      .map(name => [adminService.addCoordinator, name]);
    const removed = oldCoordinators
      .filter(x => newCoordinators.indexOf(x) < 0)
      .map(name => [adminService.removeCoordinator, name]);

    adminService
      .editCampaign(campaign.id, campaign)
      .then(() => $q.all([...added, ...removed].map(item => item[0](vm.campaign.id, item[1]))))
      .then(() => $state.reload())
      .catch(alertService.error)
      .finally(() => {
        vm.loading = false;
      });
  }
}

export default Component;
