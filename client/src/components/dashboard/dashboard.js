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

  vm.campaignsAdmin = null;
  vm.campaignsJuror = null;

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
        vm.campaignsAdmin = data.data;
      })
      .catch(err => {
        vm.err = err;
      });
  }

  function getJurorData() {
    userService
      .getJuror()
      .then(data => {
        vm.user = data.user;
        if (!data.data.length) {
          return;
        }

        const roundsGroupedByCampaigns = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id',
        );
        const campaignsJuror = _.values(roundsGroupedByCampaigns);

        // order campaigns by open date (more recent at the top)
        campaignsJuror.sort((campaign1, campaign2) => {
          const getOpenDate = campaign =>
              campaign.length > 0 && campaign[0].campaign
                  ? campaign[0].campaign.open_date
                  : null;

          const campaign1OpenDate = getOpenDate(campaign1);
          const campaign2OpenDate = getOpenDate(campaign2);

          if (campaign1OpenDate === campaign2OpenDate) {
            return 0;
          } else if (campaign1OpenDate < campaign2OpenDate) {
            return 1;
          } else { // if (campaign1OpenDate > campaign2OpenDate)
            return -1;
          }
        });

        vm.campaignsJuror = campaignsJuror;
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
