import _ from 'lodash';

import './dashboard.scss';
import template from './dashboard.tpl.html';
import templateNewOrganizer from './new-organizer.tpl.html';
import {CAMPAIGN_STATUS_ACTIVE, CAMPAIGN_STATUS_FINALIZED} from "../../constants";

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
        const isActiveCampaign = campaign =>
            (campaign.active_round || !campaign.rounds.length) && !(campaign.status === CAMPAIGN_STATUS_FINALIZED);
        vm.campaignsAdmin = data.data.filter(
          campaign => isActiveCampaign(campaign),
        );
        vm.campaignsAdminInactive = data.data.filter(
          campaign => !isActiveCampaign(campaign),
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

        const roundsGroupedByCampaigns = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id',
        );
        let campaignsJuror = _.values(roundsGroupedByCampaigns);

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
