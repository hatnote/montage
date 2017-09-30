import _ from 'lodash';

import './campaign.scss';
import templateAdmin from './campaign-admin.tpl.html';
import templateJury from './campaign-jury.tpl.html';
import templateNewRound from './new-round.tpl.html';
import templateEditCampaign from './edit-campaign.tpl.html';
import templateEditRound from './edit-round.tpl.html';

const Component = {
  bindings: {
    campaign: '<',
    user: '<',
    type: '<',
  },
  controller,
  template: templateJury,
};

function controller(
  $filter,
  $mdDialog,
  $mdToast,
  $q,
  $state,
  $templateCache,
  $timeout,
  adminService,
  alertService,
  dataService,
  dialogService) {
  const vm = this;

  vm.activateRound = activateRound;
  vm.addRound = addRound;
  vm.cancelCampaignName = cancelCampaignName;
  vm.dict = {};
  vm.editCampaign = editCampaign;
  vm.editCampaignName = editCampaignName;
  vm.editRound = editRound;
  vm.editVotes = editVotes;
  vm.getActiveJurors = (round) => round.jurors.filter((juror) => juror.is_active);
  vm.getInactiveJurors = (round) => round.jurors.filter((juror) => !juror.is_active);
  vm.isNameEdited = false;
  vm.isRoundActive = isRoundActive;
  vm.loading = false;
  vm.loadRoundDetails = loadRoundDetails;
  vm.nameEdit = '';
  vm.openRound = openRound;
  vm.pauseRound = pauseRound;
  vm.cancelRound = cancelRound;
  vm.downloadRound = downloadRound;
  vm.roundDetails = {};
  vm.roundPreview = {};
  vm.saveCampaignName = saveCampaignName;
  vm.showRoundMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

  if (isAdmin()) {
    vm.campaign.rounds = vm.campaign.rounds.filter((round) => round.status !== 'cancelled');
  }

  const voteMethods = {
    'yesno': {
      label: 'Yes/No',
      value: 'yesno',
      icon: 'thumbs_up_down'
    },
    'rating': {
      label: 'Rating',
      value: 'rating',
      icon: 'star_border'
    },
    'ranking': {
      label: 'Ranking',
      value: 'ranking',
      icon: 'sort'
    }
  };

  vm.dict.settings = {
    allowed_filetypes: 'Allowed filetypes',
    dq_by_filetype: 'Disqualify by filetype',
    dq_by_resolution: 'Disqualify by resolution',
    dq_by_upload_date: 'Disqualify by upload date',
    dq_by_uploader: 'Disqualify by uploader',
    dq_coords: 'Disqualify by coordinates',
    dq_maintainers: 'Disqualify maintainers',
    dq_organizers: 'Disqualify maintainers',
    final_threshold: 'Final threshold',
    min_resolution: 'Min. resolution',
    show_filename: 'Show filename',
    show_link: 'Show link',
    show_resolution: 'Show resolution'
  };

  $templateCache.put('campaign-template', isAdmin() ? templateAdmin : templateJury);

  // functions

  function activateRound(round) {
    round.loading = true;
    adminService.activateRound(round.id).then((response) => {
      round.loading = false;
      response.error ?
        alertService.error(response.error) :
        $state.reload();
    });
  }

  function cancelRound(round, event) {

    let confirm = $mdDialog.confirm()
      .title('Cancelling Round')
      .textContent('Are you sure you want to cancel this round?')
      .ariaLabel('Cancelling Round')
      .targetEvent(event)
      .ok('Yes, Cancel Round')
      .cancel('No, Keep Round');

    $mdDialog.show(confirm).then(() => {
      round.loading = true;
      adminService.cancelRound(round.id).then((response) => {
        round.loading = false;
        response.error ?
          alertService.error(response.error) :
          $state.reload();
      });
    }, () => {
      // round kept
    });
  }

  function downloadRound(round) {
    let dl_url = adminService.downloadRound(round.id);
    window.open(dl_url);
  }

  function createRound(round, loading, prevRoundId) {
    let round_ = angular.copy(round);
    round_ = angular.extend(round_, {
      jurors: round.jurors.map((element) => element.name),
      deadline_date: $filter('date')(round.deadline_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC')
    });

    if (round_.imports && !round_.imports.category.length) {
      round_.imports.import_method = 'gistcsv';
    }

    if (!round_.name) {
      alertService.error({
        message: 'Error',
        detail: 'Name cannot be empty'
      });
      return;
    }
    if (!round_.deadline_date) {
      alertService.error({
        message: 'Error',
        detail: 'Deadline date cannot be empty'
      });
      return;
    }
    if (!round_.jurors.length) {
      alertService.error({
        message: 'Error',
        detail: 'Jurors must be added'
      });
      return;
    }
    if (!round_.quorum) {
      alertService.error({
        message: 'Error',
        detail: 'Quorum value is empty on invalid'
      });
      return;
    }
    if (!round_.imports && !round.threshold) {
      alertService.error({
        message: 'Error',
        detail: 'Threshold value is empty on invalid'
      });
      return;
    }
    loading.window = true;
    round_.imports ?
      addFirstRound(vm.campaign.id, round_, loading) :
      addNextRound(prevRoundId, round_, loading);
  }

  function addFirstRound(id, round, loading) {
    adminService.addRound(id, round).then((response) => {
      if (response.error) {
        loading.window = false;
        alertService.error(response.error);
        return;
      }

      const id = response.id;
      adminService.populateRound(id, round.imports).then((response) => {
        if (response.error) {
          loading.window = false;
          alertService.error({
            message: 'Error',
            detail: 'Something is wrong with file list URL or Commons importing'
          });
          return;
        }

        alertService.success('New round added');
        $mdDialog.hide(true);
        $state.reload();
      });
    });
  }

  function addNextRound(id, round, loading) {
    const data = {
      next_round: round,
      threshold: round.threshold
    };

    adminService.advanceRound(id, data).then((response) => {
      if (response.error) {
        loading.window = false;
        alertService.error(response.error);
        return;
      }

      alertService.success('New round added');
      $mdDialog.hide(true);
      $state.reload();
    });
  }

  function addRound(event) {
    let scope = {
      round: {
        name: 'Round ' + (vm.campaign.rounds.length + 1),
        vote_method: 'rating',
        quorum: 2,
        jurors: [],
        config: { show_link: true },
        imports: {
          import_method: 'category',
          category: '',
        },
      },
      preview: vm.campaign.rounds.length ? vm.roundPreview[_.last(vm.campaign.rounds).id] : false,
      createRound,
      searchCategory: name => dataService
        .searchCategory(name)
        .then(response => response[1].map(element => element.substring(9))),
      voteMethods,
      today: new Date(),
    };

    if (scope.preview) {
      scope.round.jurors = scope.preview.round.jurors.map((user) => ({
        id: user.id + '',
        name: user.username
      }));
      scope.round.imports = undefined;
      scope.prevRound = _.last(vm.campaign.rounds);
    }

    dialogService.show({
      template: templateNewRound,
      scope: scope
    }, event);
  }

  function cancelCampaignName() {
    vm.isNameEdited = false;
    vm.nameEdit = '';
  }

  function editCampaign(event) {
    let campaign = angular.extend(angular.copy(vm.campaign), {
      open_date: new Date(vm.campaign.open_date),
      close_date: new Date(vm.campaign.close_date),
      coordinators: vm.campaign.coordinators.map((user) => ({ name: user.username }))
    });

    dialogService.show({
      template: templateEditCampaign,
      scope: {
        campaign: campaign,
        saveEditCampaign: saveEditCampaign,
      }
    }, event);
  }

  function editCampaignName($event) {
    vm.nameEdit = vm.campaign.name;
    vm.isNameEdited = true;
    $timeout(() => {
      let input = angular.element($event.target).parent().parent().find('input')[0];
      input.focus();
    });
  }

  function editRound(round, event) {
    let round_ = angular.extend(angular.copy(round), {
      deadline_date: new Date(round.deadline_date),
      jurors: vm.getActiveJurors(round).map((user) => ({ name: user.username }))
    });

    dialogService.show({
      template: templateEditRound,
      scope: {
        round: round_,
        voteMethods: voteMethods,
        saveEditRound: saveEditRound,
      }
    }, event);
  }

  function editVotes(round) {
    $state.go('main.juror.vote-edit', { id: round.id });
  }

  function isAdmin() {
    return vm.type === 'admin';
  }

  function isRoundActive(round) {
    return round.status === 'active' && round.total_tasks;
  }

  function loadRoundDetails(round) {
    const id = round.id;
    vm.roundDetails[id] = 'loading';

    $q.all({
      round: adminService.getRound(id),
      preview: adminService.previewRound(round.id)
    }).then((response) => {
      vm.roundDetails[id] = response.round.data;
      vm.roundPreview[id] = response.preview.data;
    });
  }

  function openRound(round) {
    if (!isRoundActive(round)) {
      return;
    }
    vm.loading = true;
    console.log(round.id);
    $state.go('main.vote', { id: round.id });
  }

  function pauseRound(round) {
    round.loading = true;
    adminService.pauseRound(round.id).then((response) => {
      round.loading = false;
      response.error ?
        alertService.error(response.error) :
        $state.reload();
    });
  }

  function saveEditCampaign(campaign, loading) {
    loading.window = true;

    let campaign_ = angular.extend(angular.copy(campaign), {
      coordinators: campaign.coordinators.map((element) => element.name),
      open_date: $filter('date')(campaign.open_date, 'yyyy-MM-ddTHH:mm:ss'),
      close_date: $filter('date')(campaign.close_date, 'yyyy-MM-ddTHH:mm:ss')
    });

    adminService.editCampaign(campaign_.id, campaign_).then((response) => {
      if (response.error) {
        loading.window = false;
        alertService.error(response.error);
        return;
      }

      alertService.success('Campaign settings saved');
      $mdDialog.hide(true);
      $state.reload();
    });
  }

  function saveEditRound(round, loading) {
    loading.window = true;
    round.new_jurors = round.jurors.map((user) => user.name);

    const round_ = angular.extend({}, round, {
      deadline_date: $filter('date')(round.deadline_date, 'yyyy-MM-ddTHH:mm:ss')
    })

    $q.all({
      round: adminService.editRound(round_.id, round_)
    }).then((response) => {
      if (response.round.error) {
        loading.window = false;
        alertService.error(response.round.error);
        return;
      }

      alertService.success('Round settings saved');
      $mdDialog.hide(true);
      $state.reload();
    });
  }

  function saveCampaignName() {
    vm.campaign.name = vm.nameEdit;
    vm.isNameEdited = false;

    adminService.editCampaign(vm.campaign.id, {
      name: vm.campaign.name
    }).then((response) => {
      response.error ?
        alertService.error(response.error) :
        alertService.success('Campaign name changed');
    });
  }
}

/*
export default () => {
  angular
    .module('montage')
    .component('montCampaign', CampaignComponent)
    .filter('fromNow', () => (input) => moment.utc(input).fromNow());
};
*/

export default Component;
