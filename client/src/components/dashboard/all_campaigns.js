import _ from 'lodash';

import './dashboard.scss';
import template from './all_campaigns.tpl.html';

const Component = {
  controller,
  template,
};

function controller(
  $filter,
  $state,
  $mdDialog,
  adminService,
  jurorService,
) {
  const vm = this;

  vm.campaignsAdmin = false;
  vm.campaignsJuror = false;

  // functions

  vm.$onInit = () => {
    getAdminData();
    getJurorData();
  };

  function getAdminData() {
    adminService
       .allCampaigns()
      .then(data => {
        vm.campaignsAdmin = data.data || [];
      })
      .catch(err => {
        vm.err = err;
      });
  }

  function getJurorData() {
    jurorService
      .allCampaigns()
      .then(data => {
        if (!data.data.length) {
          vm.campaignsJuror = [];
          return;
        }

        const roundsGroupedByCampaigns = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id',
        );
        vm.campaignsJuror = _.values(roundsGroupedByCampaigns);
      })
      .catch(err => {
        vm.err = err;
      });
  }
}

export default Component;
