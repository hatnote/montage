import _ from 'lodash';

import './dashboard.scss';
import template from './dashboard.tpl.html';
import templateNewOrganizer from './new-organizer.tpl.html';

const Component = {
  controller,
  template,
};

function controller(
  $filter,
  $state,
  $mdDialog,
  adminService,
  alertService,
  dialogService,
  userService,
) {
  const vm = this;

  vm.isAdmin = false;
  vm.isJuror = false;
  vm.campaigns = [];
  vm.campaignsAdmin = null;
  vm.campaignsAdminInactive = null;

  vm.showInactiveCampaigns = false;
  vm.collapseClosedCampaigns = () => {
    vm.showInactiveCampaigns = !vm.showInactiveCampaigns;
  };

  vm.addOrganizer = addOrganizer;

  // functions

  vm.$onInit = () => {
    getAdminData();
    getJurorData();
  };

  function getAdminData() {
    userService
      .getAdmin()
      .then(data => {
        vm.isAdmin = data.data.length;
        vm.campaignsAdmin = data.data.filter(
          campaign => campaign.active_round || !campaign.rounds.length,
        );
        vm.campaignsAdminInactive = data.data.filter(
          campaign => !campaign.active_round && campaign.rounds.length,
        );
      })
      .catch(err => {
        vm.err = err;
      });
  }

  function getJurorData() {
    userService
      .getJuror()
      .then(data => {
        vm.isJuror = data.data.length;
        vm.user = data.user;
        if (!data.data.length) {
          return;
        }

        const grupped = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id',
        );
        vm.campaignsJuror = _.values(grupped);
      })
      .catch(err => {
        vm.err = err;
      });
  }

  function addOrganizer() {
    dialogService.show({
      template: templateNewOrganizer,
      scope: {
        organizers: [],
        add: (data, loading) => {
          if (!data[0]) {
            alertService.error({
              message: 'Error',
              detail: 'Provide organizer name',
            });
            return;
          }

          loading.window = true;
          const username = data[0].name;
          adminService.addOrganizer({ username }).then(response => {
            if (response.error) {
              loading.window = false;
              alertService.error(response.error);
              return;
            }

            alertService.success(`${username} added as an organizer`);
            $mdDialog.hide(true);
            $state.reload();
          });
        },
      },
    });
  }
}

export default Component;
